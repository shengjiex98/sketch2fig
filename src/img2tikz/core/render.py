"""
TikZ rendering and image comparison utilities.

Handles:
- Converting TikZ code to PDF via pdflatex
- Converting PDF to PNG via Ghostscript
- Computing similarity between images
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim


class TikzCompilationError(RuntimeError):
    """
    Raised when pdflatex cannot compile the generated TikZ document.

    Attributes:
        log_excerpt: Relevant snippet from the LaTeX log (if available)
    """

    def __init__(self, message: str, log_excerpt: str | None = None):
        super().__init__(message)
        self.log_excerpt = log_excerpt


def _build_latex_document(tikz: str) -> str:
    """Wrap TikZ content in a minimal standalone document."""
    return (
        r"""
\documentclass[tikz,border=2mm]{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes,arrows,positioning,calc,patterns,decorations.pathreplacing}

\begin{document}
\begin{tikzpicture}
"""
        + tikz
        + r"""
\end{tikzpicture}
\end{document}
"""
    )


def _extract_log_excerpt(log_path: Path, max_lines: int = 20) -> str | None:
    """
    Extract a concise error summary from a LaTeX .log file.

    Looks for lines starting with "!" (LaTeX errors) and includes a few lines of
    context. Falls back to the last few lines if no explicit error markers are
    found.
    """
    if not log_path.exists():
        return None

    try:
        lines = log_path.read_text(errors="ignore").splitlines()
    except Exception:
        return None

    excerpt: list[str] = []
    for idx, line in enumerate(lines):
        if line.startswith("!"):
            excerpt.extend(lines[idx : min(len(lines), idx + 3)])

    if not excerpt:
        excerpt = lines[-max_lines:]

    trimmed = [line.rstrip() for line in excerpt[-max_lines:]]
    text = "\n".join(line for line in trimmed if line.strip())
    return text or None


def compile_tikz(tikz: str, out_dir: Path) -> tuple[bool, str | None]:
    """
    Compile TikZ code to PDF using pdflatex and capture LaTeX errors.

    Args:
        tikz: TikZ code that will be wrapped in a standalone document.
        out_dir: Directory where temporary LaTeX artifacts are written.

    Returns:
        Tuple of (success flag, latex_log_excerpt).
        On success, returns (True, None).
        On failure, returns (False, error_snippet_from_log).

    Raises:
        FileNotFoundError: If pdflatex is not installed.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("pdflatex"):
        raise FileNotFoundError(
            "pdflatex not found. Please install a LaTeX distribution "
            "(e.g., TeX Live, MacTeX)"
        )

    tex_file = out_dir / "diagram.tex"
    tex_file.write_text(_build_latex_document(tikz))

    try:
        completed = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "diagram.tex",
            ],
            cwd=out_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.CalledProcessError as exc:
        returncode = exc.returncode
        stdout = getattr(exc, "stdout", "") or ""
        stderr = getattr(exc, "stderr", "") or ""

    pdf_file = out_dir / "diagram.pdf"
    log_path = out_dir / "diagram.log"
    log_excerpt = _extract_log_excerpt(log_path)

    if returncode != 0 or not pdf_file.exists():
        if not log_excerpt:
            stderr = stderr.strip()
            stdout = stdout.strip()
            combined = "\n".join(line for line in [stderr, stdout] if line)
            log_excerpt = combined or "pdflatex failed without log output."
        return False, log_excerpt

    return True, None


def render_tikz(tikz: str, out_dir: Path) -> Path:
    """
    Render TikZ code to a PNG image.

    Process:
    1. Create a minimal standalone LaTeX document with the TikZ code
    2. Compile to PDF using pdflatex (via compile_tikz)
    3. Convert PDF to PNG using Ghostscript

    Args:
        tikz: TikZ code (content for tikzpicture environment)
        out_dir: Directory to write output files

    Returns:
        Path to the generated PNG file

    Raises:
        TikzCompilationError: If pdflatex fails to compile the document
        RuntimeError: If Ghostscript conversion fails
        FileNotFoundError: If required tools are not installed
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir)
        success, log_excerpt = compile_tikz(tikz, build_dir)
        if not success:
            raise TikzCompilationError(
                "pdflatex compilation failed. See latex_error.txt for details.",
                log_excerpt=log_excerpt,
            )

        pdf_file = build_dir / "diagram.pdf"
        if not pdf_file.exists():
            raise TikzCompilationError(
                "pdflatex reported success but did not produce diagram.pdf."
            )

        png_file = out_dir / "rendered.png"

        # Ensure Ghostscript is available right before conversion
        if not shutil.which("gs"):
            raise FileNotFoundError(
                "gs (Ghostscript) not found. Install via: brew install ghostscript"
            )

        try:
            subprocess.run(
                [
                    "gs",
                    "-dSAFER",
                    "-dBATCH",
                    "-dNOPAUSE",
                    "-sDEVICE=png16m",
                    "-r300",  # 300 DPI
                    "-dTextAlphaBits=4",
                    "-dGraphicsAlphaBits=4",
                    f"-sOutputFile={png_file}",
                    str(pdf_file),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Ghostscript conversion failed:\n{e.stderr}\n{e.stdout}"
            ) from e

        if not png_file.exists():
            raise RuntimeError("Ghostscript did not produce PNG output")

        return png_file


def calc_similarity(target_img: Path, rendered_img: Path) -> float:
    """
    Calculate similarity between two images using SSIM (Structural Similarity Index).

    Both images are converted to grayscale and resized to a fixed size before
    comparison.
    SSIM returns a value in [-1, 1] but typically in [0, 1] for real images, where
    1.0 means identical.

    Args:
        target_img: Path to the target (original) image
        rendered_img: Path to the rendered (comparison) image

    Returns:
        Similarity score in [0, 1], where 1.0 is identical

    Raises:
        FileNotFoundError: If either image does not exist
        ValueError: If images cannot be loaded
    """
    if not target_img.exists():
        raise FileNotFoundError(f"Target image not found: {target_img}")
    if not rendered_img.exists():
        raise FileNotFoundError(f"Rendered image not found: {rendered_img}")

    # Load images
    try:
        img1 = Image.open(target_img).convert("L")  # Convert to grayscale
        img2 = Image.open(rendered_img).convert("L")
    except Exception as e:
        raise ValueError(f"Failed to load images: {e}") from e

    # Resize to a fixed size for comparison
    # TODO: Consider making the comparison size configurable
    fixed_size = (512, 512)
    img1 = img1.resize(fixed_size, Image.Resampling.LANCZOS)
    img2 = img2.resize(fixed_size, Image.Resampling.LANCZOS)

    # Convert to numpy arrays
    arr1 = np.array(img1)
    arr2 = np.array(img2)

    # Calculate SSIM
    # data_range is the value range (0-255 for uint8)
    similarity = ssim(arr1, arr2, data_range=255)

    # Ensure result is in [0, 1]
    return max(0.0, min(1.0, float(similarity)))

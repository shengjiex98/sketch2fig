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


def render_tikz(tikz: str, out_dir: Path) -> Path:
    """
    Render TikZ code to a PNG image.

    Process:
    1. Create a minimal standalone LaTeX document with the TikZ code
    2. Compile to PDF using pdflatex
    3. Convert PDF to PNG using Ghostscript

    Args:
        tikz: TikZ code (content for tikzpicture environment)
        out_dir: Directory to write output files

    Returns:
        Path to the generated PNG file

    Raises:
        RuntimeError: If pdflatex or gs (Ghostscript) fail
        FileNotFoundError: If required tools are not installed
    """
    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check for required tools
    if not shutil.which("pdflatex"):
        raise FileNotFoundError(
            "pdflatex not found. Please install a LaTeX distribution (e.g., TeX Live, MacTeX)"
        )
    if not shutil.which("gs"):
        raise FileNotFoundError(
            "gs (Ghostscript) not found. Install via: brew install ghostscript"
        )

    # Create a temporary directory for LaTeX compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Build the standalone LaTeX document
        # Standalone class auto-crops to content
        # TODO: Make preamble configurable to support additional TikZ libraries
        latex_doc = r"""
\documentclass[tikz,border=2mm]{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes,arrows,positioning,calc,patterns,decorations.pathreplacing}

\begin{document}
\begin{tikzpicture}
""" + tikz + r"""
\end{tikzpicture}
\end{document}
"""

        # Write LaTeX source
        tex_file = tmppath / "diagram.tex"
        tex_file.write_text(latex_doc)

        # Compile with pdflatex
        # Run twice to resolve references if any
        try:
            subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "diagram.tex",
                ],
                cwd=tmppath,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"pdflatex compilation failed:\n{e.stderr}\n{e.stdout}"
            ) from e

        pdf_file = tmppath / "diagram.pdf"
        if not pdf_file.exists():
            raise RuntimeError("pdflatex did not produce diagram.pdf")

        # Convert PDF to PNG using Ghostscript
        # Use high resolution for better comparison
        png_file = out_dir / "rendered.png"
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

    Both images are converted to grayscale and resized to a fixed size before comparison.
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

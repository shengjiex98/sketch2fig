"""TikZ compilation pipeline: TikZ code → PDF → PNG."""

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

_DEFAULT_PREAMBLE = (
    Path(__file__).parent.parent.parent / "templates" / "preamble_default.tex"
)

_DOCUMENT_TEMPLATE = r"""\documentclass[border=5pt]{{standalone}}
\usepackage{{tikz}}
\usetikzlibrary{{calc,positioning,arrows.meta,shapes,backgrounds,fit,math}}
\usepackage{{amsmath,amssymb}}
{preamble}
\begin{{document}}
{tikz_code}
\end{{document}}
"""


@dataclass
class LatexError:
    message: str
    line: int | None
    context: str


def wrap_in_document(tikz_code: str, preamble: str = "") -> str:
    """Wrap a tikzpicture block in a standalone LaTeX document.

    The base template already includes tikz and common libraries.
    Pass an explicit preamble (or load DEFAULT_PREAMBLE yourself) to add more.
    """
    return _DOCUMENT_TEMPLATE.format(preamble=preamble, tikz_code=tikz_code)


DEFAULT_PREAMBLE: str = (
    _DEFAULT_PREAMBLE.read_text() if _DEFAULT_PREAMBLE.exists() else ""
)


def compile_tikz(
    tikz_code: str,
    preamble: str = "",
    output_dir: Path | None = None,
) -> tuple[Path | None, str]:
    """Compile TikZ code to PDF.

    Returns (pdf_path, log_output). pdf_path is None on failure.
    If output_dir is provided, the PDF is written there; otherwise a temp dir is used
    and the caller is responsible for consuming the file before gc.
    """
    document = wrap_in_document(tikz_code, preamble)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_path = tmp / "figure.tex"
        tex_path.write_text(document, encoding="utf-8")

        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_path),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        log = result.stdout + result.stderr

        pdf_src = tmp / "figure.pdf"
        if not pdf_src.exists():
            logger.debug("pdflatex failed; log:\n%s", log)
            return None, log

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            dest = output_dir / "figure.pdf"
            shutil.copy2(pdf_src, dest)
            return dest, log

        # Caller wants a persistent path — copy next to a system tempfile
        dest_dir = Path(tempfile.mkdtemp(prefix="s2f_"))
        dest = dest_dir / "figure.pdf"
        shutil.copy2(pdf_src, dest)
        return dest, log


def render_to_image(pdf_path: Path, dpi: int = 300) -> Image.Image:
    """Render first page of a PDF to a PIL Image at the given DPI."""
    stem = pdf_path.stem
    out_prefix = pdf_path.parent / stem

    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(out_prefix)],
        check=True,
        capture_output=True,
        timeout=30,
    )

    # pdftoppm names the first page <prefix>-1.png
    candidates = sorted(pdf_path.parent.glob(f"{stem}-*.png"))
    if not candidates:
        raise FileNotFoundError(f"pdftoppm produced no PNG from {pdf_path}")
    return Image.open(candidates[0])


def parse_errors(log: str) -> list[LatexError]:
    """Extract the first LaTeX error from a pdflatex log string."""
    lines = log.splitlines()
    errors: list[LatexError] = []

    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("!"):
            message = lines[i].lstrip().lstrip("!").strip()
            line_no: int | None = None

            # Search forward for l.<number> line reference
            for j in range(i + 1, min(i + 10, len(lines))):
                m = re.match(r"l\.(\d+)\s", lines[j])
                if m:
                    line_no = int(m.group(1))
                    break

            context_start = max(0, i - 1)
            context_end = min(len(lines), i + 5)
            context = "\n".join(lines[context_start:context_end])

            errors.append(LatexError(message=message, line=line_no, context=context))
            # Only extract the first error per the spec
            break
        i += 1

    return errors

# TikZ Compilation Pipeline

Reference this doc when working on `compiler.py`.

## Pipeline

```
TikZ code (str) → wrap in document → pdflatex → PDF → pdftoppm → PNG
```

## Key Implementation Details

### Wrapping TikZ in a Document

The user/agent produces a `\begin{tikzpicture}...\end{tikzpicture}` block. The compiler wraps it:

```latex
\documentclass[border=5pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{calc,positioning,arrows.meta,shapes,backgrounds,fit}
\usepackage{amsmath,amssymb}
% ... preamble from template ...

\begin{document}
% ... user's tikzpicture code ...
\end{document}
```

Use the `standalone` document class with `border=5pt` — this auto-crops to the figure bounds.

### Compilation

```python
import subprocess
import tempfile
from pathlib import Path

def compile_tikz(tikz_code: str, preamble: str = "") -> tuple[Path | None, str]:
    """Compile TikZ code. Returns (pdf_path, log_output). pdf_path is None on failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "figure.tex"
        tex_path.write_text(wrap_in_document(tikz_code, preamble))

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(tex_path)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        pdf_path = Path(tmpdir) / "figure.pdf"
        if pdf_path.exists():
            # Copy to a stable location before tmpdir cleanup
            ...
        return (pdf_path_or_none, result.stdout + result.stderr)
```

### Rendering PDF to PNG

```bash
pdftoppm -png -r 300 figure.pdf figure_render
# Produces figure_render-1.png
```

Use 300 DPI for evaluation. The VLM needs enough resolution to judge alignment and text, but higher DPI wastes tokens.

### Error Parsing

LaTeX errors follow a predictable pattern. Extract the useful part:

```
! Undefined control sequence.
l.42 \badcommand
                {foo}
```

Parse strategy:
1. Find lines starting with `!` — these are error messages
2. Find lines starting with `l.` — these are line numbers
3. Return the error message + surrounding context (±3 lines of the TikZ source)

Don't try to parse every possible LaTeX error. Extract the first error and the line number — that's enough for the LLM to fix it.

### Common Compilation Failures

| Error | Likely Cause | Fix Hint for LLM |
|-------|-------------|-------------------|
| `Undefined control sequence` | Missing package or typo | Check package imports, fix command name |
| `Missing $ inserted` | Math mode issue | Wrap math in `$...$` |
| `Package tikz Error: Cannot parse coordinate` | Bad coordinate syntax | Check `(x,y)` format |
| `Dimension too large` | Coordinates out of range | Scale down coordinates |
| `File ended while scanning` | Unclosed brace/environment | Check brace matching |

### Output Directory Convention

Store compilation artifacts in a structured output directory:

```
output/
├── plan.json           # Structured plan from planner
├── iteration_0/
│   ├── figure.tex      # Full LaTeX document
│   ├── figure.pdf      # Compiled PDF (if successful)
│   ├── figure.png      # Rendered PNG
│   └── eval.json       # Evaluation results
├── iteration_1/
│   └── ...
└── final.tex           # Best result (tikzpicture only, no document wrapper)
```

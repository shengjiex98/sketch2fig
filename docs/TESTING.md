# Testing Guide

Reference this doc when writing tests or debugging test failures.

## The Core Problem

This project's output is visual — "does the figure look right?" can't be fully unit-tested. We handle this with a tiered strategy.

## Tier 1: Fast, Free, Always Run

These tests use NO LLM calls and NO image rendering. They run in <5 seconds.

### What to Test

**compiler.py:**
- `wrap_in_document()` produces valid LaTeX structure (string checks)
- `parse_errors()` extracts error messages from sample log output
- Known-good TikZ code compiles successfully (requires LaTeX installed)
- Known-bad TikZ code fails with parseable error

**prompts.py:**
- Prompt templates produce valid strings with expected structure
- All template variables are properly substituted

**planner.py / generator.py / evaluator.py:**
- JSON schema validation on mock outputs
- Edge cases: empty input, malformed JSON recovery

### Example Test

```python
# tests/test_compiler.py
from sketch2fig.compiler import wrap_in_document, parse_errors

def test_wrap_in_document_has_standalone():
    result = wrap_in_document(r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}")
    assert r"\documentclass" in result
    assert "standalone" in result
    assert r"\begin{tikzpicture}" in result

def test_parse_errors_extracts_line_number():
    log = """
    ! Undefined control sequence.
    l.42 \\badcommand
                    {foo}
    """
    errors = parse_errors(log)
    assert len(errors) >= 1
    assert errors[0].line == 42
    assert "Undefined control sequence" in errors[0].message
```

## Tier 2: Slow, Free, Run Before Committing

These tests compile TikZ and render images. They take 10-30 seconds but cost nothing.

### Golden Reference Tests

Store known-good input/output pairs in `tests/fixtures/`:

```
tests/fixtures/
├── simple_boxes/
│   ├── input.png          # Screenshot of the figure
│   ├── reference.tex      # Known-good TikZ code
│   └── reference.png      # Rendered from reference.tex
├── pipeline_diagram/
│   ├── input.png
│   ├── reference.tex
│   └── reference.png
└── ...
```

Test that the compiler pipeline works end-to-end:

```python
# tests/test_golden.py
import pytest
from pathlib import Path
from sketch2fig.compiler import compile_tikz, render_to_image

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.mark.slow
@pytest.mark.parametrize("fixture", ["simple_boxes", "pipeline_diagram"])
def test_reference_compiles(fixture):
    """Reference TikZ code should always compile."""
    tex = (FIXTURES / fixture / "reference.tex").read_text()
    pdf_path, log = compile_tikz(tex)
    assert pdf_path is not None, f"Compilation failed:\n{log}"

@pytest.mark.slow
@pytest.mark.parametrize("fixture", ["simple_boxes", "pipeline_diagram"])
def test_reference_renders_similar(fixture):
    """Rendered output should match stored reference image."""
    tex = (FIXTURES / fixture / "reference.tex").read_text()
    pdf_path, _ = compile_tikz(tex)
    rendered = render_to_image(pdf_path)
    reference = Image.open(FIXTURES / fixture / "reference.png")
    similarity = compute_ssim(rendered, reference)
    assert similarity > 0.95  # Should be nearly identical
```

### Image Similarity Utility

```python
# src/sketch2fig/similarity.py
from PIL import Image
import numpy as np

def compute_ssim(img1: Image.Image, img2: Image.Image) -> float:
    """Compute structural similarity. Returns 0-1 (1 = identical)."""
    # Resize to same dimensions
    size = (min(img1.width, img2.width), min(img1.height, img2.height))
    img1 = img1.resize(size).convert("L")
    img2 = img2.resize(size).convert("L")

    arr1 = np.array(img1, dtype=float)
    arr2 = np.array(img2, dtype=float)

    # Simple SSIM approximation (good enough for our purposes)
    mu1, mu2 = arr1.mean(), arr2.mean()
    sigma1_sq = arr1.var()
    sigma2_sq = arr2.var()
    sigma12 = ((arr1 - mu1) * (arr2 - mu2)).mean()

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / \
           ((mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2))
    return float(ssim)
```

Keep this implementation simple — don't pull in scikit-image just for SSIM.

## Tier 3: Integration Tests (Costs Money)

These call real LLM APIs. Mark them clearly and never run automatically.

```python
# tests/test_integration.py
import pytest

@pytest.mark.integration
def test_full_pipeline_simple_boxes():
    """Full agent loop on a simple test case."""
    from sketch2fig.orchestrator import convert
    result = convert("tests/fixtures/simple_boxes/input.png")
    assert result.compiled  # At minimum it should compile
    assert result.iterations <= 5  # Should converge
    # Optionally check SSIM against reference
```

Run manually with: `uv run pytest -m integration -v`

## Creating New Test Fixtures

When you have a working conversion, save it as a fixture:

1. Put the input screenshot in `tests/fixtures/<name>/input.png`
2. Put the best TikZ output in `tests/fixtures/<name>/reference.tex`
3. Compile and render: save as `tests/fixtures/<name>/reference.png`

Start with 2-3 simple fixtures. Add more as you encounter interesting edge cases.

## Fixture Ideas (Start Simple)

1. **simple_boxes** — 3 boxes connected by arrows, with text labels
2. **pipeline_diagram** — The 4-step deviation bound figure from the project plan
3. **two_column** — Side-by-side comparison (left vs right)

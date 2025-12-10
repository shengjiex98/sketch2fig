# Development Guide

## Setup

```bash
# Install with dev dependencies
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

## Code Quality Tools

### Pre-commit Hooks

Set up pre-commit hooks to automatically check code quality:

```bash
uv run pre-commit install
```

This will run code formatters and linters on every commit.

### Manual Formatting

```bash
# Format code with Black
uv run black .

# Lint with Ruff
uv run ruff check --fix .

# Type checking with mypy
uv run mypy src/
```

## Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=optikz --cov-report=html

# Run specific test file
uv run pytest tests/test_pipeline_smoke.py

# Run with verbose output
uv run pytest tests/ -v
```

**Note:** Integration tests that make actual API calls are skipped by default. They require:
- Valid `OPENAI_API_KEY`
- Network connectivity
- Will incur API costs

## Project Structure

```
optikz/
├── src/optikz/              # Source code (src-layout)
│   ├── __init__.py
│   ├── core/                # Core pipeline modules
│   │   ├── __init__.py
│   │   ├── llm.py          # LLM integration (OpenAI)
│   │   ├── render.py       # TikZ rendering and image comparison
│   │   ├── pipeline.py     # Main iteration loop
│   │   └── report.py       # HTML report generation
│   └── cli/                 # Command-line interface
│       ├── __init__.py
│       └── main.py         # CLI entry point
├── tests/                   # Test suite
│   ├── __init__.py
│   └── test_pipeline_smoke.py
├── docs/                    # Documentation
├── examples/                # Example diagrams
├── pyproject.toml           # Project metadata and dependencies
├── .pre-commit-config.yaml  # Pre-commit hooks
└── README.md
```

## Architecture

### Core Modules

**llm.py** - LLM Integration
- `initial_tikz_from_llm()`: Generate initial TikZ from image
- `refine_tikz_via_llm()`: Refine TikZ based on visual comparison

**render.py** - Rendering and Comparison
- `render_tikz()`: Convert TikZ to PNG via pdflatex + Ghostscript
- `calc_similarity()`: Compute SSIM between images

**pipeline.py** - Main Pipeline
- `convert_with_iterations()`: Main iteration loop
- `IterationResult`: Dataclass for iteration metadata
- `RunResult`: Dataclass for complete run results

**report.py** - Report Generation
- `write_html_report()`: Generate visual comparison HTML report

### Design Principles

1. **Separation of concerns**: LLM, rendering, and pipeline logic are separate
2. **Testability**: Core functions are pure and mockable
3. **Extensibility**: Easy to swap LLM providers or rendering backends
4. **Clean interfaces**: Dataclasses for structured data flow

## Adding Features

### Example: Add New Similarity Metric

1. Add metric function to `render.py`:
```python
def calc_perceptual_hash_similarity(img1: Path, img2: Path) -> float:
    # Implementation
    return similarity_score
```

2. Update `pipeline.py` to use it:
```python
similarity = calc_perceptual_hash_similarity(img_path, rendered_path)
```

3. Add tests in `tests/test_render.py`

### Example: Add CLI Option

1. Update `cli/main.py` argument parser:
```python
parser.add_argument(
    "--metric",
    choices=["ssim", "phash"],
    default="ssim",
    help="Similarity metric to use",
)
```

2. Pass to pipeline:
```python
result = convert_with_iterations(
    image_path=args.image,
    metric=args.metric,
)
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes** with tests
4. **Run code quality checks**: `uv run pre-commit run --all-files`
5. **Run tests**: `uv run pytest tests/`
6. **Commit your changes**: Follow conventional commit format
7. **Push and create a pull request**

## Known Limitations & TODOs

- **LaTeX error handling**: Malformed TikZ causes `pdflatex` to fail; could add retry logic
- **Prompt tuning**: Basic prompts can be improved for better initial generation
- **Library detection**: Doesn't auto-detect required TikZ libraries
- **Cost control**: No token/cost tracking or limits on LLM calls
- **Async processing**: All operations are synchronous; async LLM calls would improve performance
- **Image preprocessing**: Could benefit from normalization/enhancement before sending to LLM

## Debugging Tips

### Enable verbose logging

Add logging to pipeline:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect intermediate files

All intermediate files are saved in `runs/run_*/`:
- Check `iteration_*.tex` for generated TikZ
- Check `iter_*/rendered.png` for rendered outputs
- Look at `iter_*/diagram.log` for pdflatex errors

### Test individual components

```python
from optikz.core import initial_tikz_from_llm, render_tikz
from pathlib import Path

# Test just LLM generation
tikz = initial_tikz_from_llm(Path("test.png"))
print(tikz)

# Test just rendering
rendered = render_tikz(tikz, Path("./test_output"))
```

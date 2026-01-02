# img2tikz

Convert diagram images to TikZ code using vision LLMs with iterative refinement.

## Overview

**img2tikz** uses vision-capable LLMs (GPT-4 Vision/GPT-4o) to convert diagram images (PNG/JPEG) into TikZ LaTeX graphics code. The system iteratively refines the generated TikZ by comparing the rendered output with the original image until a similarity threshold is met.

## Quick Start

### Prerequisites

- **Python 3.11+**
- **LaTeX distribution** with `pdflatex` (TeX Live, MacTeX)
- **Ghostscript** for PDF → PNG conversion
- **OpenAI API key**

**macOS:**
```bash
brew install --cask mactex
brew install ghostscript
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-pictures ghostscript
```

### Installation

```bash
# Clone the repository
cd img2tikz

# Install with uv (recommended)
uv sync

# Or with pip
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-api-key-here"
```

### Usage

```bash
# Basic usage
img2tikz examples/your_diagram.png

# With custom parameters
img2tikz diagram.png --iters 5 --threshold 0.95 --open-report
```

**Options:**
- `--iters N`: Maximum refinement iterations (default: 3)
- `--threshold T`: Similarity threshold for early stopping (default: 0.9)
- `--work-root DIR`: Output directory (default: `./runs`)
- `--open-report`: Open HTML report in browser
- `--no-report`: Skip HTML report generation

### As a Library

```python
from pathlib import Path
from img2tikz.core import convert_with_iterations, write_html_report

result = convert_with_iterations(
    image_path=Path("diagram.png"),
    max_iters=3,
    similarity_threshold=0.9,
)

print(f"Final TikZ: {result.final_tikz}")
print(f"Similarity: {result.iterations[-1].similarity:.4f}")

# Generate visual report
report_path = write_html_report(result)
```

## Output Structure

Each run creates a timestamped directory:

```
runs/run_20250101_123456/
├── original.png              # Input image
├── final_tikz.tex            # Generated TikZ code
├── final_standalone.tex      # Compilable standalone document
├── report.html               # Visual comparison report
└── iter_*/                   # Rendered images for each iteration
    └── rendered.png
```

## Documentation

- [Configuration Guide](docs/configuration.md) - Customize LLM models, prompts, and TikZ libraries
- [Development Guide](docs/development.md) - Contributing, testing, and code quality tools
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Features

- Vision LLM integration for diagram understanding
- Iterative refinement with automatic quality assessment
- Image similarity metrics (SSIM)
- HTML reports with visual comparisons
- Clean, extensible architecture

## Project Structure

```
img2tikz/
├── src/img2tikz/            # Main package
│   ├── core/                # Core pipeline modules
│   │   ├── llm.py          # LLM integration
│   │   ├── render.py       # TikZ rendering & comparison
│   │   ├── pipeline.py     # Iteration loop
│   │   └── report.py       # HTML report generation
│   └── cli/                 # Command-line interface
│       └── main.py
├── tests/                   # Test suite
├── examples/                # Example diagrams
└── docs/                    # Documentation
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

Built with OpenAI's GPT-4 Vision API, scikit-image for SSIM computation, and TikZ rendering via pdflatex and Ghostscript.

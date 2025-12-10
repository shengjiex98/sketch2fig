# optikz-backend

Convert diagram images to TikZ code using vision LLMs with iterative refinement.

## Overview

**optikz-backend** uses OpenAI's vision-capable models (GPT-4 Vision/GPT-4o) to convert diagram images (PNG/JPEG) into TikZ LaTeX graphics code. The system iteratively refines the generated TikZ by:

1. Generating initial TikZ from the input image
2. Rendering the TikZ to PNG
3. Comparing the rendered output with the original
4. Refining the TikZ based on visual differences
5. Repeating until a similarity threshold is met or max iterations reached

The core library is UI-agnostic and can be used from a CLI or integrated into other applications.

## Features

- **Vision LLM integration**: Uses OpenAI's GPT-4 Vision/GPT-4o for diagram understanding
- **Iterative refinement**: Automatically improves TikZ code through multiple iterations
- **Image similarity metrics**: Uses SSIM (Structural Similarity Index) for comparison
- **HTML reports**: Generates visual reports showing the refinement process
- **Clean architecture**: Reusable core library with minimal dependencies

## Prerequisites

### Required

- **Python 3.11+**
- **LaTeX distribution** with `pdflatex` (e.g., TeX Live, MacTeX)
- **Ghostscript** for PDF → PNG conversion
- **OpenAI API key** (set as environment variable)

### Installing LaTeX and Ghostscript

**macOS:**
```bash
# Install MacTeX (full LaTeX distribution)
brew install --cask mactex

# Install Ghostscript
brew install ghostscript
```

**Linux (Ubuntu/Debian):**
```bash
# Install TeX Live
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-pictures

# Install Ghostscript
sudo apt-get install ghostscript
```

## Installation

### Using uv (recommended)

```bash
# Clone or navigate to the project directory
cd optikz-backend

# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install the package with dependencies
uv pip install -e .

# Install with development tools (optional)
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install the package with dependencies
pip install -e .

# Install with development tools (optional)
pip install -e ".[dev]"
```

### Set OpenAI API Key

Copy the example environment file and add your API key:

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

Or export it directly:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Add this to your `~/.bashrc`, `~/.zshrc`, or equivalent to make it permanent.

## Usage

### Command Line

```bash
# Basic usage (3 iterations, 0.9 threshold)
optikz-backend examples/your_diagram.png

# Or using python -m
python -m optikz_backend.cli.main examples/your_diagram.png

# Custom parameters
optikz-backend examples/your_diagram.png --iters 5 --threshold 0.95

# Specify output directory and open report
optikz-backend examples/your_diagram.png --work-root my_runs/ --open-report

# Skip HTML report generation
optikz-backend examples/your_diagram.png --no-report
```

**CLI Options:**
- `--iters N`: Maximum refinement iterations (default: 3)
- `--threshold T`: Similarity threshold for early stopping (default: 0.9)
- `--work-root DIR`: Output directory (default: `./runs`)
- `--open-report`: Open HTML report in browser after completion
- `--no-report`: Skip HTML report generation

### As a Library

```python
from pathlib import Path
from optikz_backend.core import convert_with_iterations, write_html_report

# Run the conversion pipeline
result = convert_with_iterations(
    image_path=Path("diagram.png"),
    max_iters=3,
    similarity_threshold=0.9,
    work_root=Path("./runs"),
)

# Access results
print(f"Final TikZ: {result.final_tikz}")
print(f"Iterations: {len(result.iterations)}")
for iteration in result.iterations:
    print(f"Step {iteration.step}: similarity = {iteration.similarity:.4f}")

# Generate HTML report
report_path = write_html_report(result)
print(f"Report: {report_path}")
```

## Project Structure

```
optikz-backend/
├── pyproject.toml              # Project metadata and dependencies
├── LICENSE                     # MIT License
├── .python-version             # Python version for pyenv/asdf
├── .env.example                # Example environment variables
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
├── README.md                   # This file
├── src/                        # Source code (src-layout)
│   └── optikz_backend/        # Core library package
│       ├── __init__.py
│       ├── core/              # Core pipeline modules
│       │   ├── __init__.py
│       │   ├── llm.py         # LLM integration (OpenAI)
│       │   ├── render.py      # TikZ rendering and image comparison
│       │   ├── pipeline.py    # Main iteration loop
│       │   └── report.py      # HTML report generation
│       └── cli/               # Command-line interface
│           ├── __init__.py
│           └── main.py        # CLI entry point
├── examples/                   # Example diagrams
│   └── README.md
└── tests/                      # Tests
    ├── __init__.py
    └── test_pipeline_smoke.py
```

## Output Structure

Each run creates a timestamped directory under `work_root` (default: `./runs`):

```
runs/
└── run_20250101_123456/
    ├── original.png              # Copy of input image
    ├── iteration_0.tex           # Initial TikZ code
    ├── iteration_1.tex           # Refined TikZ code
    ├── final_tikz.tex            # Final TikZ code (bare)
    ├── final_standalone.tex      # Compilable standalone document
    ├── report.html               # Visual report
    ├── iter_0/
    │   └── rendered.png          # Rendered iteration 0
    ├── iter_1/
    │   └── rendered.png          # Rendered iteration 1
    └── ...
```

## Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=optikz_backend
```

**Note:** Most integration tests are skipped by default as they require API keys and make real API calls.

## Swapping LLM Providers

The LLM integration is encapsulated in [src/optikz_backend/core/llm.py](src/optikz_backend/core/llm.py). To use a different provider:

1. **Modify the client initialization** in `initial_tikz_from_llm()` and `refine_tikz_via_llm()`
2. **Adjust the API call format** for your provider (e.g., Anthropic Claude, Azure OpenAI, local models)
3. **Update environment variable handling** for API keys/endpoints

**Example: Using Anthropic Claude**

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2000,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64_image,
                    },
                },
            ],
        }
    ],
)
```

The rest of the pipeline remains unchanged.

## Configuration

### LLM Model

The default model is `gpt-4o`. To change it, edit `DEFAULT_MODEL` in [src/optikz_backend/core/llm.py:15](src/optikz_backend/core/llm.py#L15):

```python
DEFAULT_MODEL = "gpt-4-turbo"  # or your preferred model
```

### TikZ Libraries

The LaTeX preamble includes common TikZ libraries. To add more, edit the `latex_doc` template in [src/optikz_backend/core/render.py](src/optikz_backend/core/render.py):

```latex
\usetikzlibrary{shapes,arrows,positioning,calc,patterns,decorations.pathreplacing,graphs}
```

### Similarity Comparison

The comparison resizes images to 512×512 before computing SSIM. To change this, edit [src/optikz_backend/core/render.py](src/optikz_backend/core/render.py):

```python
fixed_size = (1024, 1024)  # Higher resolution
```

## Limitations and TODOs

- **LaTeX errors**: If TikZ code is malformed, `pdflatex` will fail. Error handling could be improved to retry with corrections.
- **Prompt tuning**: The prompts in [llm.py](src/optikz_backend/core/llm.py) are basic and can be refined for better results.
- **Library detection**: The system doesn't automatically detect which TikZ libraries are needed.
- **Cost control**: No token/cost tracking or limits on LLM calls.
- **Async processing**: All operations are synchronous; could benefit from async LLM calls.

## Contributing

This is an initial architecture designed for clarity and extensibility. Contributions are welcome!

### Development Setup

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Set up pre-commit hooks (recommended)
pre-commit install

# Run code formatters manually
black .
ruff check --fix .

# Run type checker
mypy src/

# Run tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built with OpenAI's GPT-4 Vision API
- Uses scikit-image for SSIM computation
- TikZ rendering via pdflatex and Ghostscript

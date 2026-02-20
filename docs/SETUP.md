# Setup Guide

Read this once when first setting up the project. After setup is complete, you don't need to reference this again.

## Initialize Project

```bash
# Create project
uv init sketch2fig
cd sketch2fig

# Set up src layout
mkdir -p src/sketch2fig
touch src/sketch2fig/__init__.py

# Add dependencies
uv add anthropic typer pillow pydantic-settings
uv add --dev pytest pytest-asyncio

# System dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y texlive-base texlive-pictures texlive-latex-extra poppler-utils
```

## Verify LaTeX Works

```bash
# Quick smoke test
echo '\documentclass[border=1pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
\draw (0,0) rectangle (2,1);
\node at (1,0.5) {Hello};
\end{tikzpicture}
\end{document}' > /tmp/test.tex

pdflatex -output-directory=/tmp /tmp/test.tex
pdftoppm -png -r 300 /tmp/test.pdf /tmp/test_render

# Should produce /tmp/test_render-1.png
ls /tmp/test_render-1.png
```

## Environment Variables

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
SKETCH2FIG_MAX_ITERATIONS=5
SKETCH2FIG_MODEL=claude-sonnet-4-6
```

## pyproject.toml Additions

Ensure these sections exist:

```toml
[project.scripts]
sketch2fig = "sketch2fig.cli:app"

[tool.pytest.ini_options]
markers = [
    "slow: marks tests that render images (deselect with '-m \"not slow\"')",
    "integration: marks tests that call LLM APIs (deselect with '-m \"not integration\"')",
]
```

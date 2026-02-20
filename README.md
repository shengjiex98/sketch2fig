# sketch2fig

Agentic AI tool that converts screenshots and sketches into publication-quality TikZ figures.

## How It Works

```
Input sketch → [Plan] → [Generate TikZ] → [Compile] → [Evaluate] → [Refine] → Output
                                              ↑                         │
                                              └─────── loop ────────────┘
```

1. **Plan:** VLM analyzes the input image, producing a structured description of elements, layout, and aesthetic intent
2. **Generate:** LLM produces TikZ code from the plan
3. **Compile:** `pdflatex` compiles to PDF, rendered to PNG for evaluation
4. **Evaluate:** VLM compares input vs output, scoring completeness, structure, text accuracy, and aesthetics
5. **Refine:** If issues are found, the LLM makes targeted edits and re-compiles (up to 5 iterations)

## Quick Start

```bash
# Install
uv sync

# Convert a figure
uv run sketch2fig convert screenshot.png

# Convert with aesthetic cleanup
uv run sketch2fig convert messy_sketch.png --clean

# Refine an existing output
uv run sketch2fig refine output.tex "make the arrows thicker"
```

## Requirements

- Python 3.12+
- TeX Live (`texlive-base texlive-pictures texlive-latex-extra`)
- poppler-utils (`pdftoppm`)
- Anthropic API key

## Examples

_Coming soon: before/after comparisons_

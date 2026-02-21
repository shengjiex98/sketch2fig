# sketch2fig

Convert figure screenshots and sketches into publication-quality TikZ code using Claude.

```
Input PNG → Plan → Generate TikZ → Compile → Evaluate → Refine → Output .tex + .png
                                        ↑                     │
                                        └──── targeted edits ─┘
```

## Demo

**Schedule diagram — passes on the first try**

| Input | Output |
|-------|--------|
| ![](docs/eval_images/4_schedule_input.png) | ![](docs/eval_images/4_schedule_output.png) |

**Pipeline with curves and shading — 5 refinement iterations**

| Input | Iteration 1 | Final |
|-------|------------|-------|
| ![](docs/eval_images/3_deviation_input.png) | ![](docs/eval_images/3_deviation_iter1.png) | ![](docs/eval_images/3_deviation_output.png) |

## Getting Started

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/), TeX Live with `pdflatex`, poppler, Anthropic API key.

```bash
# macOS
brew install --cask basictex && brew install poppler

# Ubuntu/Debian
apt-get install texlive-pictures texlive-latex-extra poppler-utils
```

```bash
git clone https://github.com/yourname/sketch2fig
cd sketch2fig
uv sync
echo "ANTHROPIC_API_KEY=sk-..." > .env
uv run sketch2fig convert your_figure.png
```

Output lands in `output/<name>/final.tex` and `final.png`.

Try it on a bundled example:

```bash
uv run sketch2fig convert tests/fixtures/real_examples/4_schedule.png --verbose
```

### Options

| Flag | Description |
|------|-------------|
| `--clean` | Aesthetic cleanup — improve alignment even if input is rough |
| `--max-iters N` | Max refinement iterations (default: 5) |
| `--output-dir PATH` | Custom output directory |
| `--verbose` | Show plan summary, per-iteration scores, and evaluator critique |

## How It Works

1. **Plan** — Claude analyzes the figure: element types, layout, connections, color semantics
2. **Generate** — Claude writes a `tikzpicture` from the plan, using the original image for detail
3. **Compile** — `pdflatex` compiles the code; on failure Claude auto-fixes errors (up to 3 retries)
4. **Evaluate** — The rendered PNG is scored against the input on completeness, structure, text, and aesthetics
5. **Refine** — Below threshold, Claude makes targeted edits and re-compiles (up to 5 iterations)

All figure understanding and code generation use Claude's vision capabilities via the Anthropic API.

# SketchToFigure: Agentic Sketch-to-Publication-Quality Figure Generator

## Project Summary

**Goal:** Build an agentic AI tool that converts screenshots, sketches, or rough diagrams into publication-quality vector graphics (primarily TikZ, with SVG as secondary output), featuring self-correction, aesthetic reasoning, and iterative refinement.

**Portfolio positioning:** Demonstrates agentic AI system design (planning, tool use, self-evaluation, error recovery) for Research Scientist / MLE roles focused on AI agents.

**Timeline:** 2–3 week MVP

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Interface                        │
│   sketch2fig convert input.png [--style distill]         │
│   sketch2fig refine output.tex "make arrows thicker"     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Agent Orchestrator                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Planning  │→ │ Generate │→ │ Evaluate │──┐            │
│  │  Agent    │  │  Agent   │  │  Agent   │  │            │
│  └──────────┘  └──────────┘  └──────────┘  │            │
│       ↑                                     │            │
│       └─────────── Refine ◄─────────────────┘            │
│                                                          │
│  Max iterations: 5 (configurable)                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Tool Layer                             │
│                                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐       │
│  │ LaTeX/TikZ  │ │   Image     │ │  Similarity  │       │
│  │ Compiler    │ │ Renderer    │ │  Scorer      │       │
│  └─────────────┘ └─────────────┘ └──────────────┘       │
│  ┌─────────────┐ ┌─────────────┐                        │
│  │ SVG Export  │ │  Style      │                        │
│  │ (optional)  │ │  Templates  │                        │
│  └─────────────┘ └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 LLM Provider Layer                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐       │
│  │ Anthropic │  │ OpenAI   │  │ Local/Ollama     │       │
│  │ (Claude)  │  │ (GPT-4o) │  │ (Llama, etc.)   │       │
│  └──────────┘  └──────────┘  └──────────────────┘       │
│                                                          │
│  Common interface: generate(prompt, image) → str         │
└─────────────────────────────────────────────────────────┘
```

---

## The Agentic Loop (Core Innovation)

This is the heart of the project — what makes it more than "call GPT-4 and hope for the best."

### Phase 1: Analysis & Planning
The agent examines the input image and produces a structured plan:
- **Element identification:** What shapes, arrows, text labels, groupings exist?
- **Layout analysis:** Grid structure? Linear flow? Hierarchical?
- **Aesthetic assessment:** Are items intended to be aligned but slightly off? Are spacings meant to be uniform? Is there a color scheme?
- **Intent inference:** Is this a pipeline diagram? A state machine? A neural network architecture? A comparison figure?
- **Fidelity decision:** Ask user — faithful reproduction, or "clean up" the aesthetics?

### Phase 2: Code Generation
Generate TikZ (or SVG) code based on the plan:
- Use style templates for consistent, publication-quality aesthetics
- Apply a preamble with well-defined styles (colors, line widths, fonts)
- Structure the code with scopes and relative positioning for maintainability

### Phase 3: Compile & Render
- Compile TikZ → PDF → PNG using `pdflatex` + `convert`/`pdftoppm`
- Capture and parse compilation errors
- If compilation fails, feed errors back to the generation agent

### Phase 4: Visual Evaluation
- Send BOTH the original input image AND the rendered output to the VLM
- Ask it to evaluate:
  - **Structural fidelity:** Are all elements present? Correct connectivity?
  - **Aesthetic quality:** Alignment, spacing, visual balance?
  - **Text accuracy:** Are all labels correct?
- Produce a structured score + specific critique

### Phase 5: Iterative Refinement
- If evaluation score < threshold OR specific issues identified:
  - Feed the critique + current code back to the generation agent
  - Agent produces a *targeted edit* (not full regeneration)
  - Re-compile, re-evaluate
- Loop up to N times (default: 5)
- Track improvement across iterations to detect plateaus

```
Input ──→ [Plan] ──→ [Generate] ──→ [Compile] ──→ [Evaluate] ──→ Output
  ↑                                     │              │
  │                              fail?──┘       score < threshold?
  │                                │                   │
  │                         [Parse Error]        [Critique]
  │                                │                   │
  └────────────────────────────────┴───────────────────┘
                               (max 5 iterations)
```

---

## Project Structure

```
sketch2fig/
├── pyproject.toml              # uv project config
├── README.md
├── src/
│   └── sketch2fig/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (click or typer)
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── orchestrator.py # Main agentic loop
│       │   ├── planner.py      # Phase 1: Analysis & planning
│       │   ├── generator.py    # Phase 2: Code generation
│       │   └── evaluator.py    # Phase 4: Visual evaluation
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract LLM interface
│       │   ├── anthropic.py    # Claude implementation
│       │   ├── openai.py       # GPT-4o implementation
│       │   └── ollama.py       # Local model implementation
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── compiler.py     # TikZ → PDF → PNG pipeline
│       │   ├── renderer.py     # Image comparison utilities
│       │   └── templates.py    # Style templates & preambles
│       ├── prompts/
│       │   ├── plan.py         # Planning prompt templates
│       │   ├── generate.py     # Generation prompt templates
│       │   ├── evaluate.py     # Evaluation prompt templates
│       │   └── refine.py       # Refinement prompt templates
│       └── config.py           # Configuration & defaults
├── templates/
│   ├── preamble_default.tex    # Standard TikZ preamble
│   ├── preamble_distill.tex    # Distill-inspired style
│   └── preamble_minimal.tex    # Minimal clean style
├── examples/
│   ├── pipeline_diagram/       # Example input → output pairs
│   ├── neural_network/
│   └── state_machine/
└── tests/
    ├── test_compiler.py
    ├── test_agent.py
    └── fixtures/               # Test images
```

---

## 2-Week Sprint Plan

### Week 1: Core Pipeline (Working End-to-End)

**Days 1–2: Foundation**
- [ ] Set up project with `uv`, install dependencies
- [ ] Implement LLM provider abstraction (`base.py`, `anthropic.py`)
- [ ] Implement TikZ compiler tool (`compiler.py`):
  - `compile_tikz(code: str) -> CompileResult` (PDF path or error)
  - `render_to_image(pdf_path: str) -> PIL.Image`
- [ ] Test: compile the example TikZ code from your paper

**Days 3–4: Single-Shot Generation**
- [ ] Write planning prompt — structured output (JSON) describing figure elements
- [ ] Write generation prompt — produces TikZ code from plan + image
- [ ] Implement `planner.py` and `generator.py`
- [ ] Test: feed your example figure screenshot → get TikZ code → compile
- [ ] Create default TikZ preamble with clean styles

**Days 5–7: The Agentic Loop**
- [ ] Implement `evaluator.py` — sends input + output images to VLM for comparison
- [ ] Implement `orchestrator.py` — the full plan → generate → compile → evaluate → refine loop
- [ ] Handle compilation failures (parse LaTeX errors, feed back to LLM)
- [ ] Handle evaluation-driven refinement (targeted edits, not full regen)
- [ ] Implement iteration tracking and plateau detection
- [ ] Basic CLI with `click` or `typer`

### Week 2: Polish & Differentiation

**Days 8–9: Aesthetic Intelligence**
- [ ] Implement alignment/symmetry detection in the planner
- [ ] Add "clean up" vs "faithful" mode toggle
- [ ] Create style templates (distill-inspired, minimal, academic)
- [ ] Add color palette extraction from input images

**Days 10–11: Multi-Provider & Robustness**
- [ ] Add OpenAI provider (`openai.py`)
- [ ] Test with different model providers — compare quality
- [ ] Add retry logic, rate limiting, cost tracking
- [ ] Handle edge cases: very complex figures, text-heavy diagrams

**Days 12–14: Demo & Documentation**
- [ ] Create 5–8 compelling example conversions (before/after)
- [ ] Write README with GIF/video demos
- [ ] Add `--verbose` mode showing the agent's reasoning at each step
- [ ] Optional: basic Gradio or Streamlit web UI for demo purposes
- [ ] Record demo video for portfolio

---

## Key Design Decisions

### 1. Structured Intermediate Representation
Between the planner and generator, use a structured JSON IR:

```json
{
  "figure_type": "pipeline_diagram",
  "layout": "horizontal_flow",
  "elements": [
    {
      "id": "step1",
      "type": "rounded_rect",
      "label": "Step 1\nGuess deviation bound",
      "style": "primary_block",
      "content": {
        "type": "plot_area",
        "elements": ["dashed_curves", "horizontal_line", "shaded_band"]
      }
    }
  ],
  "connections": [
    {"from": "step1", "to": "step2", "type": "arrow", "style": "thick"}
  ],
  "annotations": [
    {"text": "Guessed bounds", "target": "step1", "position": "above"}
  ],
  "aesthetic_notes": {
    "color_scheme": "blue_tones_with_red_highlight",
    "alignment": "uniform_spacing_between_blocks",
    "detected_issues": ["step2 annotation should be red to indicate violation"]
  }
}
```

This IR serves multiple purposes:
- Makes the planner's reasoning inspectable
- Allows the evaluator to check structural completeness
- Could be used to generate SVG as well as TikZ
- Makes refinement more targeted ("fix element step3's shading")

### 2. Prompt Engineering Strategy
Each prompt should be specialized and include:
- **Few-shot examples** of good TikZ patterns for common figure types
- **Style guidelines** baked in (consistent colors, font sizes, spacing)
- **Negative examples** showing common failure modes to avoid

### 3. Evaluation Rubric
The evaluator uses a structured rubric (not just "does it look right?"):

| Criterion       | Weight | Description                                     |
|-----------------|--------|-------------------------------------------------|
| Completeness    | 30%    | All elements from input are present             |
| Structural match| 25%    | Layout, connectivity, grouping match input      |
| Text accuracy   | 20%    | All labels and annotations are correct          |
| Aesthetic quality| 15%   | Alignment, spacing, visual balance              |
| Compilability   | 10%    | Code compiles without errors                    |

### 4. Error Recovery Taxonomy
Different failure modes require different recovery strategies:

| Failure Type           | Detection               | Recovery Strategy                  |
|------------------------|-------------------------|------------------------------------|
| Won't compile          | LaTeX error log         | Parse error, fix specific line     |
| Missing elements       | Evaluator: completeness | Add missing elements to code       |
| Wrong layout           | Evaluator: structure    | Regenerate with layout constraint  |
| Misaligned elements    | Evaluator: aesthetics   | Adjust coordinates/positioning     |
| Wrong text/labels      | Evaluator: text check   | Find-and-replace in code           |
| Style inconsistency    | Evaluator: aesthetics   | Apply style template               |

---

## Tech Stack

| Component          | Choice                              | Rationale                         |
|--------------------|-------------------------------------|-----------------------------------|
| Language           | Python 3.12+                        | Your preference, ML ecosystem     |
| Package manager    | uv                                  | Your preference                   |
| CLI framework      | Typer                               | Clean CLI with type hints         |
| LLM (primary)      | Claude claude-sonnet-4-20250514 via API | Best vision + code gen balance    |
| LLM (secondary)    | GPT-4o via API                      | Comparison / fallback             |
| LaTeX compiler     | pdflatex (TeX Live)                 | Standard, widely available        |
| PDF → Image        | pdftoppm (poppler-utils)            | Fast, reliable                    |
| Image comparison   | Pillow + SSIM (scikit-image)        | Structural similarity scoring     |
| Config             | Pydantic Settings                   | Type-safe configuration           |
| Demo UI (optional) | Gradio                              | Minimal effort, good for demos    |

---

## Stretch Goals (Post-MVP)

- [ ] **SVG output mode** — for web-first workflows
- [ ] **Batch processing** — convert all figures in a paper draft
- [ ] **Style transfer** — "make this figure match the style of figures in this paper"
- [ ] **Interactive refinement** — chat-based "make the arrows thicker," "change color to red"
- [ ] **LaTeX project integration** — auto-detect preamble from existing .tex project
- [ ] **Benchmark suite** — quantitative eval across figure types for comparing models
- [ ] **Fine-tuned evaluator** — small model trained on human preferences for figure quality

---

## What Makes This a Good Portfolio Project

1. **Agentic AI pattern** — demonstrates the plan-execute-evaluate-refine loop that's central to current AI agent research
2. **Multi-modal reasoning** — vision + code generation + aesthetic judgment
3. **Tool use** — the agent uses real tools (LaTeX compiler, image renderer) with error handling
4. **System design** — clean abstractions (LLM provider layer, tool layer, agent layer)
5. **Practical utility** — solves a real pain point you've personally experienced as a researcher
6. **Technical depth** — error recovery, structured evaluation, iteration control
7. **Differentiator from existing work** — DeTikZify et al. focus on model training; you focus on the agentic system that makes *any* VLM work better at this task

"""All LLM prompt templates for sketch2fig."""

# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
You are an expert at analyzing scientific and technical figures. Your task is to analyze \
an image and produce a structured JSON description that a TikZ code generator can use to \
recreate it accurately.

Analyze this figure carefully. Your goal is to produce a structured description that a \
code generator can use to recreate it in TikZ. Pay special attention to alignment, \
symmetry, and consistent spacing — if elements appear *intended* to be evenly spaced \
but are slightly off, note the intended layout, not the imperfect one.

Return ONLY valid JSON (no markdown fencing) matching this structure:
{
  "figure_type": "pipeline | architecture | state_diagram | comparison | graph | other",
  "layout": "horizontal_flow | vertical_flow | grid | freeform",
  "elements": [
    {
      "id": "e1",
      "type": "rect | circle | arrow | text | curve | shaded_region | diamond",
      "label": "text content or empty string",
      "position_hint": "description of where this element sits relative to others"
    }
  ],
  "connections": [
    {
      "from": "e1",
      "to": "e2",
      "type": "arrow | line | dashed_arrow | bidirectional"
    }
  ],
  "color_scheme": "description of colors used and their semantic meaning",
  "aesthetic_notes": "observations about alignment, spacing, and style intent"
}"""

_PLANNER_USER_BASE = """\
Analyze the figure in the image and return a structured JSON description of it. \
Identify all visual elements, their labels, layout, connections, and aesthetic properties."""

_PLANNER_USER_CLEAN_SUFFIX = """\

Additionally: note where alignment, symmetry, or spacing could be improved even if the \
input is imperfect. Flag elements that appear intended to be uniformly spaced or aligned \
but are not."""


def planner_user(clean: bool = False) -> str:
    """Return the planner user message, optionally requesting aesthetic cleanup notes."""
    if clean:
        return _PLANNER_USER_BASE + "\n" + _PLANNER_USER_CLEAN_SUFFIX
    return _PLANNER_USER_BASE


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """\
You are an expert TikZ programmer. Given a structured plan and the original figure image, \
produce TikZ code that recreates the figure as accurately as possible.

Rules:
- Output ONLY the \\begin{tikzpicture}...\\end{tikzpicture} block, nothing else.
- No \\documentclass, \\usepackage, or preamble — only the tikzpicture environment.
- Use relative positioning (right=of, below=of) over absolute coordinates when possible.
- Define styles at the top of the tikzpicture with \\tikzset{} or as tikzpicture options.
- Use \\def or \\pgfmathsetmacro for repeated dimensions.
- Keep labels as \\node with proper anchoring.
- Group related elements in \\begin{scope}...\\end{scope} when logical.
- Wrap your output in a ```latex code fence.

Example of good style:
```latex
\\begin{tikzpicture}[
  box/.style={draw, rounded corners, minimum width=2cm, minimum height=0.8cm},
  >=latex
]
  \\node[box] (a) {Input};
  \\node[box, right=1.5cm of a] (b) {Process};
  \\node[box, right=1.5cm of b] (c) {Output};
  \\draw[->] (a) -- (b);
  \\draw[->] (b) -- (c);
\\end{tikzpicture}
```"""


def generator_user(plan_json: str, preamble: str) -> str:
    """Return the generator user message given a plan and available preamble."""
    preamble_section = (
        preamble.strip()
        if preamble.strip()
        else "(no custom preamble — use standard TikZ only)"
    )
    return f"""\
Here is the structured plan describing the figure:

<plan>
{plan_json}
</plan>

The following TikZ preamble styles are available to you:

<preamble>
{preamble_section}
</preamble>

Now produce the TikZ code for this figure. \
Remember: output only the \\begin{{tikzpicture}}...\\end{{tikzpicture}} block in a ```latex code fence."""


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

EVALUATOR_SYSTEM = """\
You are an expert at evaluating TikZ-rendered figures against original sketches or \
screenshots. You will be shown two images: first the original input figure, then the \
TikZ-rendered output.

Compare the two images carefully. The first is the original input (a sketch or \
screenshot). The second is the TikZ-rendered output. Evaluate how well the output \
reproduces the input. Be specific about what's wrong — vague feedback like "looks off" \
is not actionable.

Compute:
  overall = 0.30*completeness + 0.25*structural_match + 0.20*text_accuracy
            + 0.15*aesthetic_quality + 0.10*10

(Compilability is always 10 since you are seeing a rendered output.)

Return ONLY valid JSON (no markdown fencing):
{
  "scores": {
    "completeness": <1-10, are all elements present?>,
    "structural_match": <1-10, do layout and proportions match?>,
    "text_accuracy": <1-10, are labels correct?>,
    "aesthetic_quality": <1-10, does it look clean and publication-ready?>,
    "overall": <computed weighted average>
  },
  "issues": [
    {
      "severity": "major | minor",
      "category": "structural | text | aesthetic | missing_element",
      "description": "specific description of the problem",
      "suggestion": "concrete TikZ fix"
    }
  ],
  "pass": <true if overall >= 8 AND no major issues, else false>
}"""

EVALUATOR_USER = """\
The first image is the original figure. The second image is the TikZ-rendered output. \
Evaluate how well the output reproduces the original and return a JSON assessment."""


# ---------------------------------------------------------------------------
# Refiner
# ---------------------------------------------------------------------------

REFINER_SYSTEM = """\
You are an expert TikZ programmer. You are refining existing TikZ code based on specific \
feedback from an evaluator.

Rules:
- Make TARGETED edits — do not rewrite from scratch.
- The current code compiles successfully, so preserve its overall structure.
- Focus only on the issues listed in the critique.
- Output ONLY the updated \\begin{tikzpicture}...\\end{tikzpicture} block in a \
```latex code fence."""


def refiner_user(current_code: str, critique_json: str) -> str:
    """Return the refiner user message given current code and evaluator critique."""
    return f"""\
Here is the current TikZ code:

<current_code>
{current_code}
</current_code>

Here is the evaluator critique listing specific issues to fix:

<critique>
{critique_json}
</critique>

Make targeted edits to fix these issues. Do not rewrite the code from scratch. \
Return the updated \\begin{{tikzpicture}}...\\end{{tikzpicture}} block in a ```latex code fence."""

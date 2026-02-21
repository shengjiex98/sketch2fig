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
- Define ALL styles inside the tikzpicture (\\tikzset{} or as tikzpicture options).
- Use only standard TikZ anchor names (north, south, east, west, center, north west, etc.).
- Do NOT use tikz-cd or any macros from external paper preambles.
- Use relative positioning (right=of, below=of) when possible; use calc for precise offsets.
- Use \\tikzmath{\\varname=value;} to define repeated numeric constants cleanly.
- Wrap your output in a ```latex code fence.

Techniques for complex figures:

Layered shaded regions (draw outer fill first, then inner fill on top, then border last):
  \\node[fill=blue!50, minimum width=3cm, minimum height=1.6cm] at (0,0) {};  % outer band
  \\node[fill=blue!10, minimum width=3cm, minimum height=1.1cm] at (0,0) {};  % inner region
  \\draw[rounded corners, thick] (-1.5,-0.85) rectangle (1.5,0.85);           % border on top

Smooth curves (use plot[smooth] for natural-looking data lines):
  \\draw[dashed] plot[smooth, tension=0.6] coordinates {(0,0.2) (0.4,0.45) (0.8,0.1) (1.2,0.5)};

Scoped subsections (shift into a panel's interior, then draw in local coordinates):
  \\begin{scope}[shift={($(step1.west)+(0.1cm,0)$)}]
    \\node[fill=blue!10, minimum width=2.5cm, minimum height=1.1cm] at (0,0) {};
    \\draw[green!60!black] (0,0) -- (2.5,0);                                    % baseline
    \\draw[dashed] plot[smooth] coordinates {(0,0.2) (0.4,0.4) (0.8,0.1)};
  \\end{scope}

Calc-based positioning:
  \\node[box] (b) at ($(a.east)+(0.5cm,0)$) {Label};     % offset from a specific anchor
  \\coordinate (mid) at ($(a)!0.5!(b)$);                  % midpoint between two nodes

L-shaped paths for corner routing:
  \\draw[->] (a) -| (b);   % go horizontal first, then vertical
  \\draw[->] (a) |- (b);   % go vertical first, then horizontal

Fit node (auto-sized bounding box around a group):
  \\node[draw, thick, fit=(a)(b)(c), inner sep=4pt] (group) {};
  \\node[anchor=north west, font=\\sffamily\\scriptsize] at (group.north west) {Label};

Color-coded regions (fill semantically distinct areas before stroking borders):
  \\fill[red!20] (0,0) rectangle (3,1.5);
  \\fill[blue!15] (3,0) rectangle (6,1.5);
  \\draw[thick] (0,0) rectangle (6,1.5);

Example of good style:
```latex
\\begin{tikzpicture}[
  block/.style={draw, rounded corners=2pt, minimum width=2.7cm, minimum height=1.7cm, thick},
  >=Stealth,
  every node/.append style={align=center, font=\\sffamily\\footnotesize}
]
  \\tikzmath{\\gap=0.5;}
  \\node[block] (s1) at (0,0) {};
  \\node[block] (s2) at ($(s1.east)+(\\gap cm,0)$) {};
  \\draw[->] (s1) -- (s2);
  \\node[below=2pt of s1] {\\textbf{Step 1}\\\\Description};
  \\node[below=2pt of s2] {\\textbf{Step 2}\\\\Description};
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

Compare the two images. The first is the original input. The second is the TikZ-rendered \
output. Evaluate how well the output reproduces the input. Be specific — vague feedback \
like "looks off" is not actionable. Do NOT write any prose or analysis before the JSON \
— output the JSON object directly.

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


# ---------------------------------------------------------------------------
# Compile-error fixer
# ---------------------------------------------------------------------------

COMPILE_FIX_SYSTEM = """\
You are an expert TikZ programmer. The TikZ code below failed to compile with pdflatex. \
Fix the error with the minimal change necessary.

Rules:
- Make ONLY the change needed to fix the compilation error.
- Do not improve or restructure unrelated code.
- Output ONLY the fixed \\begin{tikzpicture}...\\end{tikzpicture} block in a \
```latex code fence."""


def compile_fix_user(tikz_code: str, error_summary: str) -> str:
    """Return the compile-fix user message."""
    return f"""\
The following TikZ code failed to compile:

<code>
{tikz_code}
</code>

The pdflatex error:

<error>
{error_summary}
</error>

Fix the compilation error and return the corrected \
\\begin{{tikzpicture}}...\\end{{tikzpicture}} block in a ```latex code fence."""

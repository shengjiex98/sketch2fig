# Prompt Engineering Guide

Reference this doc when working on `prompts.py` or any LLM interaction code.

## General Rules

- All prompts live in `prompts.py` as string constants or simple template functions.
- Keep prompts focused. Each agent phase (plan, generate, evaluate, refine) gets its own prompt.
- Use XML tags to structure inputs within prompts (Claude handles these well).
- Request JSON output from planner and evaluator. For TikZ generation, request raw code in a fenced block.

## Planner Prompt

**Input:** Image of the sketch/figure
**Output:** JSON describing the figure structure

The planner should identify:
- Figure type (pipeline, architecture, state diagram, comparison, etc.)
- Layout structure (horizontal flow, vertical, grid, freeform)
- Each visual element with: id, type (rect, circle, arrow, text, curve, shaded_region), approximate position, label text
- Connections between elements
- Color scheme observations
- Aesthetic issues detected (misalignment, inconsistent spacing)

Key instruction to include:
> Analyze this figure carefully. Your goal is to produce a structured description that a code generator can use to recreate it in TikZ. Pay special attention to alignment, symmetry, and consistent spacing — if elements appear *intended* to be evenly spaced but are slightly off, note the intended layout, not the imperfect one.

## Generator Prompt

**Input:** Structured plan (JSON) + original image (for reference) + preamble template
**Output:** TikZ code (tikzpicture environment only)

Key instructions to include:
- Use relative positioning (`right=of`, `below=of`) over absolute coordinates when possible
- Define styles at the top of the tikzpicture, not inline
- Use `\tikzmath` or `\def` for repeated dimensions
- Keep labels as `\node` with proper anchoring
- Group related elements in `\begin{scope}...\end{scope}`
- Use consistent spacing variables

Include 1-2 short TikZ examples of common patterns (pipeline, architecture diagram) directly in the prompt as few-shot examples. Keep examples under 30 lines each.

## Evaluator Prompt

**Input:** Original image + rendered output image
**Output:** JSON with scores and critique

```json
{
  "scores": {
    "completeness": 8,
    "structural_match": 7,
    "text_accuracy": 9,
    "aesthetic_quality": 6,
    "overall": 7.2
  },
  "issues": [
    {
      "severity": "major",
      "category": "structural",
      "description": "Step 3 is missing the darker blue band behind the lighter one",
      "suggestion": "Add a second rectangle with fill=blue!50 behind the existing fill=blue!10 rectangle"
    }
  ],
  "pass": false
}
```

Score each criterion 1-10. `pass` is true when overall >= 8 AND no major issues.

Key instruction:
> Compare the two images carefully. The first is the original input (a sketch or screenshot). The second is the TikZ-rendered output. Evaluate how well the output reproduces the input. Be specific about what's wrong — vague feedback like "looks off" is not actionable.

## Refiner Prompt

**Input:** Current TikZ code + evaluation critique + original image
**Output:** Updated TikZ code

Key instruction:
> You are refining existing TikZ code based on specific feedback. Make TARGETED edits — do not rewrite from scratch. The current code compiles successfully, so preserve its structure. Focus only on the issues listed below.

This is important: the refiner should edit, not regenerate. This makes iterations more stable and avoids regression.

## Cost Awareness

A typical conversion might use:
- 1 planner call (~1K input tokens with image, ~500 output)
- 1 generator call (~2K input, ~1-3K output)
- 1-4 evaluator calls (~2K input with 2 images, ~300 output each)
- 0-3 refiner calls (~3K input, ~1-3K output)

Total: roughly 15-30K tokens per figure. At Sonnet pricing that's about $0.05-0.15 per figure.

Log token usage and cost per run.

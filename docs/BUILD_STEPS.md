# Build Steps

Work through these steps in order. Each step builds on the previous one. Before starting a step, check what already exists — earlier steps may already be done.

## Step 1: Compiler ✅ (do first)

**Read first:** `docs/COMPILER.md`

**Goal:** Implement `src/sketch2fig/compiler.py` — the TikZ → PDF → PNG pipeline.

**Key functions:**

- `wrap_in_document(tikz_code, preamble) → str` — wraps a tikzpicture in a standalone document
- `compile_tikz(tikz_code, preamble, output_dir) → CompileResult` — runs pdflatex, returns path to PDF or error info
- `render_to_image(pdf_path, dpi=300) → Path` — converts PDF to PNG via pdftoppm
- `parse_errors(log_output) → list[CompileError]` — extracts first error + line number from LaTeX log

**Test:** Compile `tests/fixtures/simple_pipeline/reference.tex` and verify it produces a PNG.

**Done when:** `uv run pytest tests/test_compiler.py` passes.

---

## Step 2: Prompts + Planner

**Read first:** `docs/PROMPTS.md`

**Goal:** Implement `src/sketch2fig/prompts.py` (all prompt templates) and `src/sketch2fig/planner.py` (image → structured plan).

**Design decisions:**

- All prompts live as string constants or simple f-string functions in `prompts.py`. No Jinja, no separate files.
- The planner sends the input image to Claude and gets back a JSON plan describing the figure's elements, layout, connections, and aesthetic observations.
- Don't over-specify the JSON schema. A reasonable structure: `{figure_type, layout, elements: [{id, type, label, position_hint}], connections: [{from, to, type}], aesthetic_notes}`.
- The planner should note aesthetic *intent* — e.g., "these boxes appear to be uniformly spaced" or "this element is highlighted in red to indicate an error state."

**API setup:**

- Use the `anthropic` Python SDK. Model name should come from config/env var, default to `claude-sonnet-4-6`.
- Create a thin helper function for calling Claude with images: `call_claude(system, user_text, image_paths, response_format="json") → str`. Reuse this across planner/generator/evaluator.
- Load image as base64 for the API call. Use `media_type` from file extension.

**Test:** Run planner on `tests/fixtures/simple_pipeline/input.png`, print the JSON plan. Visually verify it makes sense (3 boxes, 2 arrows, 3 labels). This is a Tier 3 test (costs money), so just run it manually once.

**Done when:** Planner returns a sensible JSON plan for the simple_pipeline fixture.

---

## Step 3: Generator

**Read first:** `docs/PROMPTS.md` (generator section)

**Goal:** Implement `src/sketch2fig/generator.py` — takes the plan + input image + preamble and produces TikZ code.

**Design decisions:**

- Send BOTH the structured plan AND the original image to Claude. The plan provides structure; the image provides visual details the plan might miss.
- Include the preamble template in the prompt so the LLM knows what styles/colors are available.
- Request output as a TikZ code block (```latex ...```). Parse the code block out of the response.
- The generator should produce ONLY the `\begin{tikzpicture}...\end{tikzpicture}` block, not a full document. The compiler's `wrap_in_document` handles the rest.

**Test:** Run planner → generator → compiler pipeline on `simple_pipeline/input.png`. Does the output compile? Render the PNG and visually inspect. This is a manual test.

**Done when:** The pipeline produces a compiled PNG from the simple_pipeline input.

---

## Step 4: Evaluator

**Read first:** `docs/PROMPTS.md` (evaluator section)

**Goal:** Implement `src/sketch2fig/evaluator.py` — compares input image vs rendered output, returns structured score + critique.

**Design decisions:**

- Send BOTH images (input and rendered output) to Claude in a single call.
- Request a structured JSON response with scores (1-10) for: completeness, structural_match, text_accuracy, aesthetic_quality.
- Compute an overall score as weighted average: completeness 30%, structure 25%, text 20%, aesthetics 15%, compilability 10% (compilability is always 10 if we got here).
- Include a list of specific issues, each with severity (major/minor), category, description, and a concrete suggestion for fixing it.
- Set `pass` threshold at overall >= 7.5 AND no major issues.
- Keep the evaluator prompt focused: "be specific about what's wrong — vague feedback is not actionable."

**Test two scenarios:**

1. Send simple_pipeline input.png and reference.png → should score high (>8)
2. Manually create a "bad" version (e.g., a TikZ file with only 2 boxes instead of 3), compile it, and send that as the output → should score lower and identify the missing box

**Done when:** Evaluator returns reasonable scores that distinguish good from bad outputs.

---

## Step 5: Orchestrator + CLI

**Goal:** Implement `src/sketch2fig/orchestrator.py` (the full agentic loop) and `src/sketch2fig/cli.py` (CLI entry point).

**The agentic loop:**

```
1. Plan: image → structured plan
2. Generate: plan + image → TikZ code
3. Compile: TikZ → PDF → PNG
   - If compilation fails: parse error, send error + code to LLM for fix, retry (up to 3 compile retries per iteration)
4. Evaluate: input image + rendered PNG → score + critique
   - If pass: done, save final output
   - If not pass: go to step 5
5. Refine: current code + critique + input image → updated TikZ code, go to step 3
   - Max 5 total iterations
```

**Design decisions:**

- The refiner should make TARGETED EDITS, not regenerate from scratch. This is critical — regeneration causes regression. The prompt should say: "Make targeted edits to fix the specific issues listed. Do not rewrite the code from scratch."
- Track the score at each iteration. If score doesn't improve for 2 consecutive iterations, stop early (plateau detection).
- Save artifacts from each iteration in a structured output directory (see COMPILER.md for layout).
- Log each step clearly: "Iteration 2: compile OK, score 6.8, issues: [missing label on step 3], refining..."
- The `--clean` flag should add an instruction to the planner: "Improve alignment, symmetry, and spacing even if the input is imperfect."

**CLI commands:**

- `sketch2fig convert <input_image> [--clean] [--max-iters N] [--output-dir DIR]`
- `sketch2fig refine <tikz_file> <instruction>` (stretch goal, skip for MVP if tight on time)

**Test:** Run the full loop on `simple_pipeline/input.png`. Check that it converges (score improves or plateaus) and produces a final `.tex` file.

**Done when:** `uv run sketch2fig convert tests/fixtures/simple_pipeline/input.png` produces a compiled figure.

---

## Step 6: Polish & Harder Tests

**Goal:** Iterate on quality using the harder `real_examples` fixture and real-world examples.

**Tasks:**

- Run on `tests/fixtures/real_examples/3_deviation.png` — this has curves, layered rectangles, color semantics. It WILL fail on first try. Use the failures to improve prompts.
- Improve the generator prompt with TikZ patterns for common elements (smooth curves, layered fills, scope-based positioning).
- Add `--verbose` flag that prints the plan, each iteration's score, and the evaluator's critique.
- Create a few more test fixtures from real paper figures.
- Write the README with before/after examples.
- Aim for 3-5 compelling demo conversions.

**Done when:** You have a working demo you'd be comfortable showing in an interview.

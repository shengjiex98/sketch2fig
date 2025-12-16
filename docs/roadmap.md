# optikz Roadmap

Goal:

- Speed up making TikZ figures for my own papers.
- Make it shareable for others.
- Use as a portfolio project demonstrating PhD-level software engineering in AI/ML.

---

## Milestone 0 – Current status (done ✅)

- [x] Initialize `optikz` repo with `uv` and Python 3.11+.
- [x] Set up package structure (`optikz_backend/`, `cli/`, etc.).
- [x] Implement basic CLI command:  
  - `optikz /path/to/image`
- [x] Implement initial LLM integration:
  - Takes an image, calls an image-capable model.
  - Returns TikZ code as output.
- [x] Implement basic LaTeX/TikZ rendering:
  - Generated TikZ → `.tex` → `.pdf` → `.png`.
- [x] Implement initial HTML report:
  - Shows at least the final rendered image and TikZ.
- [x] End-to-end flow works on simple diagrams (even if TikZ quality is mediocre and sometimes fails to compile).

---

## Milestone 1 – Robust core pipeline

### 1.1 Hardening TikZ compilation

- [ ] Add a **compile-check function**:
  - [ ] `compile_tikz(tikz: str, out_dir: Path) -> tuple[bool, Optional[str]]`
    - Returns `(success, latex_log_excerpt)`.
    - On failure, capture relevant error lines from `.log`.
  - [ ] Ensure `render_tikz` uses this compile-check and surfaces errors instead of crashing.

  - _If stuck_:  
    - Show the AI: a failing TikZ snippet **and** the LaTeX log, ask:  
      “Extract a minimal error summary from this log and suggest how to detect it programmatically.”

- [ ] In the pipeline, handle compilation failures gracefully:
  - [ ] Still record an `IterationResult`, but maybe with `rendered_path=None` and `similarity=None`.
  - [ ] Mark failures clearly in the report.

### 1.2 Iterative refinement loop

- [ ] Implement `convert_with_iterations(...)` behavior as intended:
  - [x] Iteration 0: LLM generates initial TikZ from original image.
  - [x] For each step:
    - [x] Attempt to render.
    - [x] If render succeeds and similarity can be computed:
      - [x] Store similarity.
      - [x] Stop if `similarity >= similarity_threshold` or `step >= max_iters`.
    - [ ] If render fails:
      - [ ] Use the latex log + current TikZ + original image as input to `refine_tikz_via_llm`.
- [x] Ensure `RunResult` includes:
  - [x] `final_tikz`
  - [x] `iterations: List[IterationResult]`
  - [x] `run_dir` path

  - _If stuck_:  
    - Ask AI: “Here is my current `convert_with_iterations` function. Refactor it to clearly separate: (1) single iteration step, (2) stopping logic, (3) error handling.”

### 1.3 Similarity metric

- [x] Implement `calc_similarity(target_img: Path, rendered_img: Path) -> float`:
  - [x] Load both images (Pillow / OpenCV).
  - [x] Convert to grayscale.
  - [x] Resize to fixed dimensions.
  - [x] Compute SSIM (preferred) or MSE.
- [x] Integrate similarity computation in the pipeline:
  - [x] Only compute if rendering succeeded.
  - [x] Store in `IterationResult.similarity`.
  - [x] Use for stopping condition in `convert_with_iterations`.

  - _If stuck_:  
    - Ask AI: “Given these two image paths, write a simple `calc_similarity` using SSIM in Python with [Pillow + skimage] and return a float between 0 and 1.”

---

## Milestone 2 – Testing & safety net

### 2.1 Test setup

- [x] Add `pytest` to dev dependencies (via `uv` / `pyproject.toml`).
- [x] Create `tests/` structure:
  - [x] `tests/__init__.py`
  - [x] `tests/conftest.py`
  - [x] `tests/test_pipeline.py`
  - [x] `tests/test_render.py`
  - [x] `tests/test_report.py`
  - [x] `tests/test_cli.py`

### 2.2 Pipeline tests (LLM/render mocked)

- [x] In `test_pipeline.py`:
  - [x] Use `monkeypatch` to stub:
    - `initial_tikz_from_llm`
    - `refine_tikz_via_llm`
    - `render_tikz`
    - `calc_similarity`
  - [x] Test that `max_iters` is respected:
    - Low similarity → pipeline runs exactly `max_iters` steps.
  - [x] Test that `similarity_threshold` stops early when reached.
  - [x] Test that `work_root` is honored (run directory inside it).

  - _If stuck_:  
    - Ask AI: “Given this project tree and this pipeline function, write a pytest that monkeypatches LLM/render functions and asserts the number of iterations.”

### 2.3 Render tests

- [x] In `test_render.py`:
  - [x] Monkeypatch `subprocess.run` so that:
    - when called with `pdflatex`, it creates a fake PDF file.
    - when called with `magick`/`convert`/`ghostscript`, it creates a fake PNG file.
  - [x] Assert:
    - `.tex` is written.
    - `.png` path is returned.
    - `subprocess.run` is called as expected.
- [x] Optional integration test:
  - [x] Mark with `@pytest.mark.integration`.
  - [x] Check if `pdflatex` is available before running.
  - [x] Actually compile a tiny TikZ snippet.

### 2.4 Report tests

- [ ] In `test_report.py`:
  - [x] Use a fake `RunResult` fixture with:
    - 2–3 iterations,
    - dummy PNG files.
  - [x] Call `write_html_report`.
  - [ ] Assert:
    - [x] Report file exists.
    - [ ] Contains references to iteration PNG filenames.
    - [x] Contains the TikZ code.

### 2.5 CLI tests

- [x] In `test_cli.py`:
  - [x] Monkeypatch `convert_with_iterations` to return a simple fake `RunResult`.
  - [x] Call the CLI (via `CliRunner` if click, or patch `sys.argv` if argparse).
  - [x] Assert:
    - [x] Exit code 0.
    - [x] STDOUT contains some expected text.
    - [x] No crash even when real pipeline is stubbed.

- [ ] Document how to run tests:
  - [ ] `uv run pytest`
  - [ ] `uv run pytest -m "not integration"`

---

## Milestone 3 – Better generation quality (practical, not perfect)

### 3.1 Improve prompts for stability & compilability

- [ ] Tighten prompts for `initial_tikz_from_llm`:
  - [ ] Explicitly require:
    - A single `\begin{tikzpicture}...\end{tikzpicture}` block.
    - No `\documentclass`, `\begin{document}`, or comments outside the picture.
    - No non-TikZ LaTeX.
- [ ] Tighten prompts for `refine_tikz_via_llm`:
  - [ ] Provide:
    - [x] Original image.
    - [x] Last rendered image (if any).
    - [x] Current TikZ.
    - LaTeX error snippet (if any).
  - [x] Ask for **corrected** TikZ only.

  - _If stuck_:  
    - Copy a failing case and ask AI:  
      “Rewrite this prompt so that the model always returns **only** a compilable `tikzpicture` environment and nothing else.”

### 3.2 Optional: introduce a structured intermediate representation

- [ ] Add an optional mode:
  - [ ] LLM outputs **JSON schema** for diagram:
    - `nodes`: id, label, row, col, type.
    - `edges`: from, to, type.
  - [ ] New function `schema_to_tikz(schema: dict) -> str` builds TikZ deterministically.
- [ ] Add a CLI flag:
  - [ ] `--mode schema` vs `--mode direct`.

  - _If stuck_:  
    - Ask AI: “Given this JSON schema example, implement `schema_to_tikz` that places nodes on a grid using TikZ.”

### 3.3 Focus on your real diagrams

- [ ] Collect 2–3 real diagrams you care about (e.g., ECU & HIV flow diagrams).
- [ ] Create a small “evaluation” script or notebook that:
  - [ ] Runs `convert_with_iterations` on each.
  - [ ] Saves results in a dedicated folder (`eval/`).
- [ ] Manually inspect:
  - [ ] Are nodes and edges roughly correct?
  - [ ] Does the legend/math text come through?
- [ ] Adjust prompts and max iterations based on what you see.

---

## Milestone 4 – UX & shareability

### 4.1 Improve HTML report

- [ ] Add basic layout:
  - [ ] Title with timestamp and input filename.
  - [x] Show original image at top.
  - [ ] For each iteration:
    - [x] Heading: “Iteration N (similarity: X.XX)”
    - [x] Rendered image.
    - [x] `<pre>` block with TikZ code.
- [ ] Link to final TikZ file at the bottom (“Download final TikZ”).

- _If stuck_:  
  - Ask AI: “Given this `RunResult` structure, produce an HTML report with original image and each iteration in a simple layout using inline CSS only.”

### 4.2 (Optional) Tiny web UI

- [ ] Add a `app.py` using Streamlit or Gradio:
  - [ ] Upload an image.
  - [ ] Choose `max_iters` and `similarity_threshold`.
  - [ ] Run `convert_with_iterations`.
  - [ ] Show original + iteration images + TikZ.
- [ ] Document:
  - [ ] `uv run streamlit run app.py` (or equivalent).

If this feels like too much for now, you can skip this and rely on the HTML reports.

---

## Milestone 5 – Portfolio & documentation

### 5.1 README & documentation

- [ ] Update `README.md`:
  - [x] Project overview.
  - [x] Installation instructions (with `uv`).
  - [x] Basic usage:
    - [ ] `optikz path/to/image.png --iters 2 --threshold 0.9`
  - [x] Architecture overview (1–2 diagrams or bullets).
  - [ ] Testing instructions.
  - [ ] Limitations & future work.

### 5.2 Tag a release

- [ ] Create git tag for first usable version:
  - [ ] `git tag v0.1.0`
  - [ ] `git push --tags`

### 5.3 Interview story / job-search usage

- [ ] Draft 2–3 bullets for your CV:
  - [ ] “Designed and implemented an LLM-powered image-to-TikZ converter with iterative refinement, LaTeX integration, and automated evaluation.”
- [ ] Draft a short “project story” for interviews:
  - [ ] The problem (TikZ is powerful but painful).
  - [ ] Your design (modular pipeline, tests, refinement loop).
  - [ ] Technical decisions (LLM prompts, rendering, similarity).
  - [ ] Lessons learned (prompt design, error handling, working with external tools).

---

## Optional Future Ideas

- [ ] Support other backends (e.g., HTML/SVG instead of TikZ).
- [ ] Add model selection (e.g., different OpenAI models).
- [ ] Add caching of LLM calls for repeated runs on same image.
- [ ] Provide a simple “figure gallery” as a demo.

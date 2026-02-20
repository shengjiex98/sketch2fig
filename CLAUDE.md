# CLAUDE.md

## Project: sketch2fig

Agentic tool that converts screenshots/sketches of figures into publication-quality TikZ code. CLI-first Python project.

## Principles

- **KISS.** Simplest solution that works. No premature abstraction.
- **One LLM provider.** Anthropic Claude only. No provider abstraction layer.
- **Agentic loop is the product.** Plan → Generate → Compile → Evaluate → Refine. Get this loop working first, polish later.
- **Python 3.12+, managed with `uv`.** Use `uv run` to execute, `uv add` to add deps.

## Project Layout

```
sketch2fig/
├── src/sketch2fig/
│   ├── cli.py              # Typer CLI
│   ├── orchestrator.py     # Main agentic loop
│   ├── planner.py          # Image → structured plan (JSON)
│   ├── generator.py        # Plan → TikZ code
│   ├── evaluator.py        # Compare input vs rendered output
│   ├── compiler.py         # TikZ → PDF → PNG
│   ├── prompts.py          # All prompt templates
│   └── config.py           # Settings (pydantic-settings)
├── templates/              # TikZ preamble templates
├── examples/               # Test inputs with reference outputs
└── tests/
```

## Key Commands

```bash
uv run sketch2fig convert input.png              # basic conversion
uv run sketch2fig convert input.png --clean       # aesthetic cleanup mode
uv run sketch2fig refine output.tex "make arrows thicker"  # interactive edit
uv run pytest                                     # run tests
uv run pytest tests/test_compiler.py -v           # specific test
```

## Testing Strategy

Tests have 3 tiers. Always run Tier 1 during development. Run Tier 2 before committing. Tier 3 is manual/CI only.

- **Tier 1 (fast, free):** Compilation success, code structure checks, unit tests. Run with `uv run pytest -m "not slow"`.
- **Tier 2 (slow, free):** Image similarity (SSIM) against golden references. Run with `uv run pytest`.
- **Tier 3 (costs money):** Full agent loop with real LLM calls. Run with `uv run pytest -m integration`.

## Code Style

- Type hints on all function signatures.
- Docstrings on public functions only (one-liner is fine).
- No classes where a function will do. Use dataclasses/Pydantic models for structured data.
- `pathlib.Path` for all file paths.
- Use `logging` module, not print statements.

## Task-Specific Docs

Read these BEFORE starting work on the corresponding task:

- `docs/SETUP.md` — First-time project setup (run once)
- `docs/COMPILER.md` — TikZ compilation pipeline details
- `docs/PROMPTS.md` — Prompt engineering guidelines and templates
- `docs/TESTING.md` — Detailed testing patterns and fixtures

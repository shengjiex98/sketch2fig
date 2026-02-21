"""Main agentic loop: Plan → Generate → Compile → Evaluate → Refine."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from .compiler import compile_tikz, parse_errors, render_to_image
from .evaluator import EvalResult, evaluate
from .generator import fix_compile_error, generate_tikz, refine_tikz
from .planner import plan_figure

logger = logging.getLogger(__name__)

_MAX_COMPILE_RETRIES = 3


@dataclass
class ConvertResult:
    tex_path: Path
    png_path: Path
    passed: bool
    overall: float
    iterations: int


def _compile_with_retries(
    tikz: str,
    preamble: str,
    iter_dir: Path,
) -> tuple[Path | None, str]:
    """Compile tikz, retrying up to _MAX_COMPILE_RETRIES times after asking Claude to fix errors.

    Returns (pdf_path, final_tikz). pdf_path is None if all attempts fail.
    """
    for attempt in range(1, _MAX_COMPILE_RETRIES + 1):
        pdf, log = compile_tikz(tikz, preamble=preamble, output_dir=iter_dir)
        if pdf is not None:
            return pdf, tikz
        errors = parse_errors(log)
        logger.warning(
            "Compile attempt %d/%d failed: %s",
            attempt,
            _MAX_COMPILE_RETRIES,
            errors[0].message if errors else "unknown error",
        )
        if attempt < _MAX_COMPILE_RETRIES:
            tikz = fix_compile_error(tikz, errors, log)
    return None, tikz


def convert(
    input_image: Path,
    output_dir: Path,
    clean: bool = False,
    max_iters: int = 5,
    preamble: str = "",
) -> ConvertResult | None:
    """Run the full agentic loop and return a ConvertResult, or None if compilation never succeeded."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Plan
    logger.info("=== Planning ===")
    plan = plan_figure(input_image, clean=clean)
    logger.info(
        "Plan: %s | %s | %d element(s) | %d connection(s)",
        plan.get("figure_type", "?"),
        plan.get("layout", "?"),
        len(plan.get("elements", [])),
        len(plan.get("connections", [])),
    )
    if plan.get("aesthetic_notes"):
        logger.info("Aesthetic notes: %s", plan["aesthetic_notes"])

    # Step 2: Initial generation
    logger.info("=== Generating ===")
    tikz = generate_tikz(plan, input_image, preamble=preamble)

    last_result: EvalResult | None = None
    last_tex: str = tikz
    last_rendered: Path | None = None
    prev_score: float = -1.0
    plateau_count: int = 0

    for iteration in range(1, max_iters + 1):
        logger.info("=== Iteration %d/%d ===", iteration, max_iters)
        iter_dir = output_dir / f"iter_{iteration:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Compile (with error-fix retries)
        pdf, tikz = _compile_with_retries(tikz, preamble, iter_dir)
        if pdf is None:
            logger.error("Iteration %d: compilation failed after %d attempts — stopping", iteration, _MAX_COMPILE_RETRIES)
            break

        # Render PDF → PNG
        img = render_to_image(pdf)
        rendered_path = iter_dir / "rendered.png"
        img.save(str(rendered_path))
        (iter_dir / "figure.tex").write_text(tikz, encoding="utf-8")

        last_tex = tikz
        last_rendered = rendered_path

        # Step 4: Evaluate
        last_result = evaluate(input_image, rendered_path)
        logger.info(
            "Iteration %d: overall=%.2f pass=%s",
            iteration,
            last_result.overall,
            last_result.passed,
        )

        if last_result.passed:
            logger.info("Quality threshold reached.")
            break

        # Plateau detection
        if last_result.overall <= prev_score:
            plateau_count += 1
            if plateau_count >= 2:
                logger.info("Score plateaued for 2 iterations — stopping early.")
                break
        else:
            plateau_count = 0
        prev_score = last_result.overall

        if iteration == max_iters:
            logger.info("Max iterations reached.")
            break

        # Step 5: Refine for next iteration
        major = [i for i in last_result.issues if i.get("severity") == "major"]
        minor = [i for i in last_result.issues if i.get("severity") == "minor"]
        logger.info(
            "=== Refining: %d major, %d minor issue(s) ===",
            len(major), len(minor),
        )
        tikz = refine_tikz(tikz, last_result, input_image)

    if last_rendered is None:
        return None

    # Save final outputs
    final_tex = output_dir / "final.tex"
    final_png = output_dir / "final.png"
    final_tex.write_text(last_tex, encoding="utf-8")
    shutil.copy2(last_rendered, final_png)

    return ConvertResult(
        tex_path=final_tex,
        png_path=final_png,
        passed=last_result.passed if last_result else False,
        overall=last_result.overall if last_result else 0.0,
        iterations=iteration,
    )

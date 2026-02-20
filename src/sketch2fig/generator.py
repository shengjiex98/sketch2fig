"""Plan + image → TikZ code via Claude (initial generation, compile-fix, refinement)."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .config import call_claude, extract_tikz_block
from .prompts import (
    COMPILE_FIX_SYSTEM,
    GENERATOR_SYSTEM,
    REFINER_SYSTEM,
    compile_fix_user,
    generator_user,
    refiner_user,
)

if TYPE_CHECKING:
    from .compiler import LatexError
    from .evaluator import EvalResult

logger = logging.getLogger(__name__)


def generate_tikz(plan: dict, image_path: Path, preamble: str = "") -> str:
    """Generate a tikzpicture block from a structured plan and the original image.

    Returns the raw tikzpicture environment (no document wrapper).
    """
    logger.info("Generating TikZ for: %s", image_path)
    response = call_claude(
        system=GENERATOR_SYSTEM,
        user_text=generator_user(json.dumps(plan, indent=2), preamble),
        image_paths=[image_path],
        response_format="text",
    )
    tikz = extract_tikz_block(response)
    logger.debug("Generated TikZ (%d chars)", len(tikz))
    return tikz


def fix_compile_error(tikz_code: str, errors: "list[LatexError]", log: str) -> str:
    """Ask Claude to fix a pdflatex compilation error in TikZ code."""
    if errors:
        error_summary = "\n".join(
            f"Line {e.line}: {e.message}\n{e.context}" for e in errors
        )
    else:
        error_summary = log[-1500:]
    logger.info("Asking Claude to fix compile error")
    response = call_claude(
        system=COMPILE_FIX_SYSTEM,
        user_text=compile_fix_user(tikz_code, error_summary),
        response_format="text",
    )
    return extract_tikz_block(response)


def refine_tikz(tikz_code: str, eval_result: "EvalResult", input_image: Path) -> str:
    """Refine TikZ code based on evaluator critique, sending the original image for reference."""
    critique = json.dumps(
        {"scores": eval_result.scores, "issues": eval_result.issues}, indent=2
    )
    logger.info("Refining TikZ (score was %.2f)", eval_result.overall)
    response = call_claude(
        system=REFINER_SYSTEM,
        user_text=refiner_user(tikz_code, critique),
        image_paths=[input_image],
        response_format="text",
    )
    return extract_tikz_block(response)

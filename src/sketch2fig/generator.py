"""Plan + image → TikZ code via Claude."""

import json
import logging
from pathlib import Path

from .config import call_claude, extract_tikz_block
from .prompts import GENERATOR_SYSTEM, generator_user

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

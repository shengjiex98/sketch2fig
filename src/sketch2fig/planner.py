"""Image → structured plan via Claude."""

import json
import logging
from pathlib import Path

from .config import call_claude, strip_json_fences
from .prompts import PLANNER_SYSTEM, planner_user

logger = logging.getLogger(__name__)


def plan_figure(image_path: Path, clean: bool = False) -> dict:
    """Analyze an image and return a structured JSON plan.

    Args:
        image_path: Path to the input figure image.
        clean: If True, prompt includes aesthetic cleanup instructions.

    Returns:
        Parsed JSON plan as a dict.
    """
    logger.info("Planning figure: %s", image_path)
    response = call_claude(
        system=PLANNER_SYSTEM,
        user_text=planner_user(clean=clean),
        image_paths=[image_path],
        response_format="json",
    )
    text = strip_json_fences(response)
    plan = json.loads(text)
    logger.debug("Plan: %s", json.dumps(plan, indent=2))
    return plan

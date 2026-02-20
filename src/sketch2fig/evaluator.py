"""Input image + rendered image → structured evaluation via Claude."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import call_claude, strip_json_fences
from .prompts import EVALUATOR_SYSTEM, EVALUATOR_USER

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "completeness": 0.30,
    "structural_match": 0.25,
    "text_accuracy": 0.20,
    "aesthetic_quality": 0.15,
}
_COMPILABILITY_SCORE = 1.0  # 0.10 * 10


@dataclass
class EvalResult:
    scores: dict[str, float]
    issues: list[dict] = field(default_factory=list)
    passed: bool = False
    overall: float = 0.0


def _compute_overall(scores: dict[str, float]) -> float:
    return sum(scores.get(k, 0) * w for k, w in _WEIGHTS.items()) + _COMPILABILITY_SCORE


def _is_pass(overall: float, issues: list[dict]) -> bool:
    has_major = any(i.get("severity") == "major" for i in issues)
    return overall >= 8.0 and not has_major


def evaluate(input_image: Path, rendered_image: Path) -> EvalResult:
    """Compare input and rendered images and return a structured evaluation.

    Args:
        input_image: Path to the original input figure.
        rendered_image: Path to the TikZ-rendered PNG output.

    Returns:
        EvalResult with scores, issues, and pass/fail verdict.
    """
    logger.info("Evaluating: %s vs %s", input_image.name, rendered_image.name)
    response = call_claude(
        system=EVALUATOR_SYSTEM,
        user_text=EVALUATOR_USER,
        image_paths=[input_image, rendered_image],
        response_format="json",
    )
    data = json.loads(strip_json_fences(response))

    scores: dict[str, float] = data.get("scores", {})
    issues: list[dict] = data.get("issues", [])

    overall = _compute_overall(scores)
    scores["overall"] = round(overall, 2)

    passed = _is_pass(overall, issues)

    logger.info(
        "Scores: overall=%.2f completeness=%s structure=%s text=%s aesthetic=%s — %s",
        overall,
        scores.get("completeness", "?"),
        scores.get("structural_match", "?"),
        scores.get("text_accuracy", "?"),
        scores.get("aesthetic_quality", "?"),
        "PASS" if passed else "FAIL",
    )
    if issues:
        for issue in issues:
            logger.info(
                "  [%s] %s: %s",
                issue.get("severity", "?").upper(),
                issue.get("category", "?"),
                issue.get("description", ""),
            )

    return EvalResult(scores=scores, issues=issues, passed=passed, overall=overall)

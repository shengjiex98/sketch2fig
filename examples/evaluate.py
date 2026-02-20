from pathlib import Path
from sketch2fig.evaluator import evaluate
import logging

logging.basicConfig(level=logging.INFO)

# Scenario 1: good — input vs reference (should score high)
result = evaluate(
    Path("tests/fixtures/simple_pipeline/input.png"),
    Path("tests/fixtures/simple_pipeline/reference.png"),
)
print("overall:", result.overall, "pass:", result.passed)

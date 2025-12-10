"""
Shared pytest fixtures for optikz tests.

Provides reusable test fixtures for creating dummy images, fake results,
and other test utilities.
"""

from pathlib import Path

import pytest
from PIL import Image

from optikz.core.pipeline import IterationResult, RunResult


@pytest.fixture
def tmp_image(tmp_path: Path) -> Path:
    """
    Create a small dummy PNG image for testing.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path to the created dummy PNG
    """
    img_path = tmp_path / "test_input.png"
    # Create a simple 100x100 white image
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)
    return img_path


@pytest.fixture
def fake_iteration_results(tmp_path: Path) -> RunResult:
    """
    Build a synthetic RunResult with fake iteration data.

    Creates:
    - A run directory with 3 iteration results
    - Dummy PNG files for each iteration
    - Fake TikZ code and similarity scores

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        RunResult with synthetic data
    """
    run_dir = tmp_path / "run_20240101_120000"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create original image copy
    original_img = run_dir / "original.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(original_img)

    # Create iteration results
    iterations = []
    for step in range(3):
        # Create iteration directory
        iter_dir = run_dir / f"iter_{step}"
        iter_dir.mkdir(exist_ok=True)

        # Create rendered PNG
        rendered_path = iter_dir / "rendered.png"
        img = Image.new("RGB", (100, 100), color="lightgray")
        img.save(rendered_path)

        # Create fake TikZ code
        tikz_code = f"% Iteration {step}\n\\draw (0,0) -- (1,1);\n"

        # Create iteration result
        iterations.append(
            IterationResult(
                step=step,
                tikz=tikz_code,
                rendered_path=rendered_path,
                similarity=0.5 + (step * 0.2),  # 0.5, 0.7, 0.9
            )
        )

    # Final TikZ is the last iteration
    final_tikz = iterations[-1].tikz

    return RunResult(
        final_tikz=final_tikz,
        iterations=iterations,
        run_dir=run_dir,
    )

"""
Smoke tests for the core pipeline.

These are basic tests to verify the modules can be imported and basic
functionality works. They do NOT make actual LLM calls.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from optikz.core import IterationResult, RunResult


def test_imports():
    """Test that all core modules can be imported."""
    from optikz.core import (
        calc_similarity,
        convert_with_iterations,
        initial_tikz_from_llm,
        refine_tikz_via_llm,
        render_tikz,
        write_html_report,
    )

    assert callable(initial_tikz_from_llm)
    assert callable(refine_tikz_via_llm)
    assert callable(render_tikz)
    assert callable(calc_similarity)
    assert callable(convert_with_iterations)
    assert callable(write_html_report)


def test_iteration_result_dataclass():
    """Test IterationResult dataclass."""
    result = IterationResult(
        step=0,
        tikz="\\draw (0,0) -- (1,1);",
        rendered_path=Path("/tmp/test.png"),
        similarity=0.95,
    )

    assert result.step == 0
    assert "draw" in result.tikz
    assert result.similarity == 0.95


def test_run_result_dataclass():
    """Test RunResult dataclass."""
    iterations = [
        IterationResult(
            step=0,
            tikz="\\draw (0,0) -- (1,1);",
            rendered_path=Path("/tmp/test0.png"),
            similarity=0.85,
        ),
        IterationResult(
            step=1,
            tikz="\\draw (0,0) -- (1,1);",
            rendered_path=Path("/tmp/test1.png"),
            similarity=0.92,
        ),
    ]

    result = RunResult(
        final_tikz="\\draw (0,0) -- (1,1);",
        iterations=iterations,
        run_dir=Path("/tmp/run_test"),
    )

    assert result.final_tikz == "\\draw (0,0) -- (1,1);"
    assert len(result.iterations) == 2
    assert result.iterations[1].similarity == 0.92


# @pytest.mark.skipif(True, reason="Requires OPENAI_API_KEY and makes actual API calls")
def test_initial_tikz_from_llm_integration():
    """
    Integration test for initial_tikz_from_llm.

    Skipped by default. Remove skipif to test with real API.
    """
    from optikz.core import initial_tikz_from_llm

    # This would require a real image and API key
    image_path = Path("examples/figure1.png")
    tikz = initial_tikz_from_llm(image_path)
    assert isinstance(tikz, str)
    assert len(tikz) > 0
    pass


def test_render_tikz_requires_latex():
    """Test that render_tikz checks for required tools."""
    from optikz.core import render_tikz

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Mock shutil.which to simulate missing pdflatex
        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="pdflatex not found"):
                render_tikz("\\draw (0,0);", tmppath)


def test_calc_similarity_validates_paths():
    """Test that calc_similarity validates input paths."""
    from optikz.core import calc_similarity

    with pytest.raises(FileNotFoundError):
        calc_similarity(Path("/nonexistent1.png"), Path("/nonexistent2.png"))


def test_write_html_report_structure():
    """Test basic HTML report generation structure."""
    from optikz.core import write_html_report

    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        # Create mock iteration results
        iterations = [
            IterationResult(
                step=0,
                tikz="\\draw (0,0) -- (1,1);",
                rendered_path=run_dir / "render0.png",
                similarity=0.85,
            )
        ]

        # Create a dummy rendered image
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        img.save(iterations[0].rendered_path)

        # Create a dummy original image
        original_path = run_dir / "original.png"
        img.save(original_path)

        result = RunResult(
            final_tikz="\\draw (0,0) -- (1,1);",
            iterations=iterations,
            run_dir=run_dir,
        )

        report_path = write_html_report(result)

        assert report_path.exists()
        assert report_path.name == "report.html"

        content = report_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "TikZ Refinement Report" in content
        assert "Iteration 0" in content
        assert "0.8500" in content  # Similarity formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

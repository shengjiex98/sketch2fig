"""
Tests for the core pipeline orchestration.

These tests verify that convert_with_iterations correctly orchestrates
the refinement loop without requiring actual LLM calls or LaTeX compilation.
"""

from pathlib import Path

import pytest
from PIL import Image

from img2tikz.core.pipeline import convert_with_iterations
from img2tikz.core.render import TikzCompilationError


def test_pipeline_stops_at_max_iters(tmp_path: Path, monkeypatch):
    """
    Test that the pipeline stops after max_iters when similarity threshold is never met.

    Monkeypatches all external dependencies to return dummy values, and ensures
    that the loop runs exactly max_iters times.
    """
    # Create a dummy input image
    input_img = tmp_path / "input.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Track how many times each function is called
    call_counts = {"initial": 0, "render": 0, "similarity": 0, "refine": 0}

    # Mock initial_tikz_from_llm
    def mock_initial_tikz(image_path: Path) -> str:
        call_counts["initial"] += 1
        return "% Initial TikZ\n\\draw (0,0) -- (1,1);"

    # Mock render_tikz to create a dummy PNG
    def mock_render_tikz(tikz: str, out_dir: Path) -> Path:
        call_counts["render"] += 1
        rendered = out_dir / "rendered.png"
        img = Image.new("RGB", (100, 100), color="gray")
        img.save(rendered)
        return rendered

    # Mock calc_similarity to always return low value (never meet threshold)
    def mock_calc_similarity(target: Path, rendered: Path) -> float:
        call_counts["similarity"] += 1
        return 0.3  # Always low, so threshold (0.99) is never met

    # Mock refine_tikz_via_llm
    def mock_refine_tikz(
        original_image_path: Path, rendered_image_path: Path, current_tikz: str
    ) -> str:
        call_counts["refine"] += 1
        # Return slightly modified TikZ
        return current_tikz + f"\n% refined {call_counts['refine']}"

    # Apply monkeypatches
    monkeypatch.setattr(
        "img2tikz.core.pipeline.initial_tikz_from_llm", mock_initial_tikz
    )
    monkeypatch.setattr("img2tikz.core.pipeline.render_tikz", mock_render_tikz)
    monkeypatch.setattr("img2tikz.core.pipeline.calc_similarity", mock_calc_similarity)
    monkeypatch.setattr("img2tikz.core.pipeline.refine_tikz_via_llm", mock_refine_tikz)

    # Run the pipeline with max_iters=3
    work_root = tmp_path / "runs"
    result = convert_with_iterations(
        image_path=input_img,
        max_iters=3,
        similarity_threshold=0.99,  # High threshold that won't be met
        work_root=work_root,
    )

    # Assertions
    assert len(result.iterations) == 3, "Should run exactly 3 iterations"
    assert result.run_dir.exists(), "Run directory should be created"
    assert result.run_dir.parent == work_root, "Run directory should be under work_root"

    # Verify final TikZ contains refinements
    assert "refined" in result.final_tikz

    # Verify all rendered images exist
    for iteration in result.iterations:
        assert iteration.rendered_path is not None
        assert iteration.rendered_path.exists()
        assert iteration.similarity == 0.3

    # Verify call counts
    assert call_counts["initial"] == 1, "Initial generation called once"
    assert call_counts["render"] == 3, "Render called for each iteration"
    assert call_counts["similarity"] == 3, "Similarity calculated for each iteration"
    assert call_counts["refine"] == 2, (
        "Refine called for iterations 0 and 1 (not after final iteration)"
    )


def test_pipeline_stops_early_due_to_threshold(tmp_path: Path, monkeypatch):
    """
    Test that the pipeline stops early when similarity threshold is met.

    Simulates a scenario where the second iteration meets the threshold,
    so refinement stops after 2 iterations instead of max_iters=5.
    """
    # Create a dummy input image
    input_img = tmp_path / "input.png"
    img = Image.new("RGB", (100, 100), color="green")
    img.save(input_img)

    # Track call counts
    call_counts = {"similarity": 0, "refine": 0}

    # Mock initial_tikz_from_llm
    def mock_initial_tikz(image_path: Path) -> str:
        return "% Initial\n\\draw (0,0) -- (1,1);"

    # Mock render_tikz
    def mock_render_tikz(tikz: str, out_dir: Path) -> Path:
        rendered = out_dir / "rendered.png"
        img = Image.new("RGB", (100, 100), color="gray")
        img.save(rendered)
        return rendered

    # Mock calc_similarity to return increasing values
    similarity_sequence = [0.5, 0.95]  # Second iteration meets 0.9 threshold

    def mock_calc_similarity(target: Path, rendered: Path) -> float:
        idx = call_counts["similarity"]
        call_counts["similarity"] += 1
        if idx < len(similarity_sequence):
            return similarity_sequence[idx]
        return 0.99  # Shouldn't reach here

    # Mock refine_tikz_via_llm
    def mock_refine_tikz(
        original_image_path: Path, rendered_image_path: Path, current_tikz: str
    ) -> str:
        call_counts["refine"] += 1
        return current_tikz + f"\n% refined {call_counts['refine']}"

    # Apply monkeypatches
    monkeypatch.setattr(
        "img2tikz.core.pipeline.initial_tikz_from_llm", mock_initial_tikz
    )
    monkeypatch.setattr("img2tikz.core.pipeline.render_tikz", mock_render_tikz)
    monkeypatch.setattr("img2tikz.core.pipeline.calc_similarity", mock_calc_similarity)
    monkeypatch.setattr("img2tikz.core.pipeline.refine_tikz_via_llm", mock_refine_tikz)

    # Run with max_iters=5 but threshold should stop it at 2
    result = convert_with_iterations(
        image_path=input_img,
        max_iters=5,
        similarity_threshold=0.9,
        work_root=tmp_path / "runs",
    )

    # Assertions
    assert len(result.iterations) == 2, (
        "Should stop after 2 iterations due to threshold"
    )
    assert result.iterations[0].similarity == 0.5
    assert result.iterations[1].similarity == 0.95

    # Verify that we didn't call refine after meeting threshold
    assert call_counts["refine"] == 1, "Should only refine once (after first iteration)"
    assert call_counts["similarity"] == 2, "Should calculate similarity twice"


def test_pipeline_uses_custom_work_root(tmp_path: Path, monkeypatch):
    """
    Test that the pipeline respects the work_root parameter.

    Verifies that the run directory is created under the specified work_root.
    """
    # Create a dummy input image
    input_img = tmp_path / "input.png"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(input_img)

    # Mock all dependencies with minimal implementations
    monkeypatch.setattr(
        "img2tikz.core.pipeline.initial_tikz_from_llm",
        lambda img: "\\draw (0,0) -- (1,1);",
    )

    def mock_render(tikz: str, out_dir: Path) -> Path:
        rendered = out_dir / "rendered.png"
        img = Image.new("RGB", (100, 100), color="gray")
        img.save(rendered)
        return rendered

    monkeypatch.setattr("img2tikz.core.pipeline.render_tikz", mock_render)
    monkeypatch.setattr(
        "img2tikz.core.pipeline.calc_similarity", lambda t, r: 0.95
    )  # Meet threshold immediately

    # Use a custom work_root
    custom_work_root = tmp_path / "my_custom_runs"
    result = convert_with_iterations(
        image_path=input_img,
        max_iters=3,
        similarity_threshold=0.9,
        work_root=custom_work_root,
    )

    # Assertions
    assert result.run_dir.parent == custom_work_root
    assert result.run_dir.exists()
    assert custom_work_root.exists()


def test_pipeline_creates_all_expected_files(tmp_path: Path, monkeypatch):
    """
    Test that the pipeline creates all expected output files.

    Verifies:
    - Original image copy
    - Iteration .tex files
    - Final TikZ files (final_tikz.tex and final_standalone.tex)
    - Run directory structure
    """
    # Create a dummy input image
    input_img = tmp_path / "input.png"
    img = Image.new("RGB", (100, 100), color="yellow")
    img.save(input_img)

    # Mock dependencies
    monkeypatch.setattr(
        "img2tikz.core.pipeline.initial_tikz_from_llm",
        lambda img: "\\draw (0,0) circle (1);",
    )

    def mock_render(tikz: str, out_dir: Path) -> Path:
        rendered = out_dir / "rendered.png"
        img = Image.new("RGB", (100, 100), color="gray")
        img.save(rendered)
        return rendered

    monkeypatch.setattr("img2tikz.core.pipeline.render_tikz", mock_render)
    monkeypatch.setattr(
        "img2tikz.core.pipeline.calc_similarity", lambda t, r: 0.4
    )  # Low similarity, go to max_iters

    def mock_refine(original_image_path, rendered_image_path, current_tikz):
        return current_tikz + "\n% refined"

    monkeypatch.setattr("img2tikz.core.pipeline.refine_tikz_via_llm", mock_refine)

    # Run pipeline with 2 iterations
    result = convert_with_iterations(
        image_path=input_img,
        max_iters=2,
        similarity_threshold=0.9,
        work_root=tmp_path / "runs",
    )

    # Check that expected files exist
    run_dir = result.run_dir

    # Original image should be copied
    assert (run_dir / "original.png").exists()

    # Iteration .tex files (iteration_0.tex and iteration_1.tex from refinement)
    assert (run_dir / "iteration_0.tex").exists()
    assert (run_dir / "iteration_1.tex").exists()

    # Final files
    assert (run_dir / "final_tikz.tex").exists()
    assert (run_dir / "final_standalone.tex").exists()

    # Iteration directories
    assert (run_dir / "iter_0").exists()
    assert (run_dir / "iter_1").exists()

    # Check final_standalone.tex contains proper LaTeX structure
    standalone_content = (run_dir / "final_standalone.tex").read_text()
    assert r"\documentclass[tikz,border=2mm]{standalone}" in standalone_content
    assert r"\begin{tikzpicture}" in standalone_content
    assert r"\end{tikzpicture}" in standalone_content


def test_pipeline_retries_when_compilation_fails(tmp_path: Path, monkeypatch):
    """
    The pipeline should retry when a TikZ compilation fails without counting
    the failed attempt toward max_iters.
    """

    input_img = tmp_path / "input.png"
    img = Image.new("RGB", (50, 50), color="purple")
    img.save(input_img)

    monkeypatch.setattr(
        "img2tikz.core.pipeline.initial_tikz_from_llm",
        lambda img: "\\draw (0,0) -- (1,1);",
    )

    state = {"render_calls": 0, "refine_calls": 0, "last_error": None}

    def mock_render(tikz: str, out_dir: Path) -> Path:
        if state["render_calls"] == 0:
            state["render_calls"] += 1
            raise TikzCompilationError("failed", log_excerpt="! Undefined control")
        state["render_calls"] += 1
        rendered = out_dir / "rendered.png"
        img = Image.new("RGB", (50, 50), color="gray")
        img.save(rendered)
        return rendered

    def mock_refine(
        original_image_path: Path,
        rendered_image_path: Path | None,
        current_tikz: str,
        latex_error: str | None = None,
    ) -> str:
        state["refine_calls"] += 1
        state["last_error"] = latex_error
        return current_tikz + "\n% fixed compile"

    monkeypatch.setattr("img2tikz.core.pipeline.render_tikz", mock_render)
    monkeypatch.setattr("img2tikz.core.pipeline.calc_similarity", lambda t, r: 0.95)
    monkeypatch.setattr("img2tikz.core.pipeline.refine_tikz_via_llm", mock_refine)

    result = convert_with_iterations(
        image_path=input_img,
        max_iters=1,
        similarity_threshold=0.9,
        work_root=tmp_path / "runs",
    )

    # Expect two iteration records: one failed compile, one success
    assert len(result.iterations) == 2
    assert result.iterations[0].rendered_path is None
    assert result.iterations[0].similarity is None
    assert "! Undefined control" in (result.iterations[0].compile_error or "")
    assert result.iterations[1].rendered_path is not None
    assert result.iterations[1].similarity == 0.95

    # Verify max_iters counted only the successful render
    assert state["render_calls"] == 2
    assert state["refine_calls"] == 1
    assert state["last_error"] == "! Undefined control"


def test_pipeline_raises_error_for_missing_image(tmp_path: Path):
    """
    Test that the pipeline raises FileNotFoundError for non-existent input image.
    """
    non_existent = tmp_path / "does_not_exist.png"

    with pytest.raises(FileNotFoundError, match="Input image not found"):
        convert_with_iterations(
            image_path=non_existent,
            max_iters=3,
            similarity_threshold=0.9,
            work_root=tmp_path / "runs",
        )

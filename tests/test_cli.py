"""
Tests for the CLI interface.

These tests verify that the CLI correctly:
- Parses command-line arguments
- Validates inputs
- Calls the pipeline with correct parameters
- Handles errors appropriately
"""

from pathlib import Path

from PIL import Image

from img2tikz.cli.main import main
from img2tikz.core.pipeline import IterationResult, RunResult


def test_cli_basic_invocation(tmp_path: Path, monkeypatch, capsys):
    """
    Test basic CLI invocation with minimal arguments.

    Verifies that:
    - The CLI accepts a single image path argument
    - It calls convert_with_iterations with default parameters
    - It exits with code 0 on success
    """
    # Create a dummy input image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Create a fake run directory and result
    run_dir = tmp_path / "run_20240101_120000"
    run_dir.mkdir(parents=True)

    # Create dummy iteration data
    iter_dir = run_dir / "iter_0"
    iter_dir.mkdir()
    rendered = iter_dir / "rendered.png"
    img.save(rendered)

    iteration = IterationResult(
        step=0, tikz="\\draw (0,0) -- (1,1);", rendered_path=rendered, similarity=0.95
    )

    fake_result = RunResult(
        final_tikz="\\draw (0,0) -- (1,1);", iterations=[iteration], run_dir=run_dir
    )

    # Create final_tikz.tex and final_standalone.tex files
    (run_dir / "final_tikz.tex").write_text("\\draw (0,0) -- (1,1);")
    (run_dir / "final_standalone.tex").write_text("\\documentclass{standalone}...")

    # Mock convert_with_iterations to return our fake result
    def mock_convert(image_path, max_iters, similarity_threshold, work_root):
        return fake_result

    monkeypatch.setattr("optikz.cli.main.convert_with_iterations", mock_convert)

    # Mock write_html_report to return a path
    def mock_report(result):
        report_path = result.run_dir / "report.html"
        report_path.write_text("<html></html>")
        return report_path

    monkeypatch.setattr("optikz.cli.main.write_html_report", mock_report)

    # Set up sys.argv
    monkeypatch.setattr("sys.argv", ["optikz", str(input_img)])

    # Run the CLI
    exit_code = main()

    # Assertions
    assert exit_code == 0, "CLI should exit with code 0 on success"

    # Check output contains expected messages
    captured = capsys.readouterr()
    assert "optikz" in captured.out.lower()
    assert "conversion complete" in captured.out.lower()


def test_cli_with_custom_parameters(tmp_path: Path, monkeypatch):
    """
    Test CLI with custom --iters, --threshold, and --work-root parameters.

    Verifies that CLI arguments are correctly passed to convert_with_iterations.
    """
    # Create a dummy input image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="green")
    img.save(input_img)

    # Track what parameters were passed to convert_with_iterations
    captured_params = {}

    def mock_convert(image_path, max_iters, similarity_threshold, work_root):
        captured_params["image_path"] = image_path
        captured_params["max_iters"] = max_iters
        captured_params["similarity_threshold"] = similarity_threshold
        captured_params["work_root"] = work_root

        # Return a minimal fake result
        run_dir = tmp_path / "fake_run"
        run_dir.mkdir(exist_ok=True)
        (run_dir / "final_tikz.tex").write_text("\\draw (0,0);")
        (run_dir / "final_standalone.tex").write_text("\\documentclass{standalone}")

        iter_dir = run_dir / "iter_0"
        iter_dir.mkdir(exist_ok=True)
        rendered = iter_dir / "rendered.png"
        img.save(rendered)

        return RunResult(
            final_tikz="\\draw (0,0);",
            iterations=[
                IterationResult(
                    step=0, tikz="\\draw (0,0);", rendered_path=rendered, similarity=0.9
                )
            ],
            run_dir=run_dir,
        )

    monkeypatch.setattr("optikz.cli.main.convert_with_iterations", mock_convert)
    monkeypatch.setattr(
        "optikz.cli.main.write_html_report",
        lambda r: r.run_dir / "report.html",
    )

    # Set custom work_root
    custom_work_root = tmp_path / "my_runs"

    # Set up sys.argv with custom parameters
    monkeypatch.setattr(
        "sys.argv",
        [
            "optikz",
            str(input_img),
            "--iters",
            "5",
            "--threshold",
            "0.85",
            "--work-root",
            str(custom_work_root),
        ],
    )

    # Run the CLI
    exit_code = main()

    # Assertions
    assert exit_code == 0
    assert captured_params["image_path"] == input_img
    assert captured_params["max_iters"] == 5
    assert captured_params["similarity_threshold"] == 0.85
    assert captured_params["work_root"] == custom_work_root


def test_cli_missing_image_error(tmp_path: Path, monkeypatch, capsys):
    """
    Test that CLI exits with error code 1 when input image doesn't exist.
    """
    non_existent = tmp_path / "does_not_exist.png"

    monkeypatch.setattr("sys.argv", ["optikz", str(non_existent)])

    exit_code = main()

    assert exit_code == 1, "CLI should exit with code 1 for missing image"

    # Check error message
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_invalid_iters_parameter(tmp_path: Path, monkeypatch, capsys):
    """
    Test that CLI validates --iters parameter (must be >= 1).
    """
    # Create a dummy image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Try with invalid --iters value
    monkeypatch.setattr("sys.argv", ["optikz", str(input_img), "--iters", "0"])

    exit_code = main()

    assert exit_code == 1, "CLI should exit with code 1 for invalid --iters"

    captured = capsys.readouterr()
    assert "--iters must be >= 1" in captured.err


def test_cli_invalid_threshold_parameter(tmp_path: Path, monkeypatch, capsys):
    """
    Test that CLI validates --threshold parameter (must be in [0, 1]).
    """
    # Create a dummy image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Try with threshold > 1.0
    monkeypatch.setattr("sys.argv", ["optikz", str(input_img), "--threshold", "1.5"])

    exit_code = main()

    assert exit_code == 1, "CLI should exit with code 1 for invalid --threshold"

    captured = capsys.readouterr()
    assert "--threshold must be in [0, 1]" in captured.err

    # Try with threshold < 0.0
    monkeypatch.setattr("sys.argv", ["optikz", str(input_img), "--threshold", "-0.5"])

    exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "--threshold must be in [0, 1]" in captured.err


def test_cli_no_report_flag(tmp_path: Path, monkeypatch):
    """
    Test that --no-report flag prevents HTML report generation.
    """
    # Create a dummy input image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Track whether write_html_report was called
    report_called = {"called": False}

    def mock_convert(image_path, max_iters, similarity_threshold, work_root):
        run_dir = tmp_path / "run"
        run_dir.mkdir(exist_ok=True)
        (run_dir / "final_tikz.tex").write_text("\\draw;")
        (run_dir / "final_standalone.tex").write_text("\\doc")

        iter_dir = run_dir / "iter_0"
        iter_dir.mkdir()
        rendered = iter_dir / "rendered.png"
        img.save(rendered)

        return RunResult(
            final_tikz="\\draw;",
            iterations=[
                IterationResult(
                    step=0, tikz="\\draw;", rendered_path=rendered, similarity=0.9
                )
            ],
            run_dir=run_dir,
        )

    def mock_report(result):
        report_called["called"] = True
        return result.run_dir / "report.html"

    monkeypatch.setattr("optikz.cli.main.convert_with_iterations", mock_convert)
    monkeypatch.setattr("optikz.cli.main.write_html_report", mock_report)

    # Run with --no-report
    monkeypatch.setattr("sys.argv", ["optikz", str(input_img), "--no-report"])

    exit_code = main()

    assert exit_code == 0
    assert not report_called["called"], (
        "write_html_report should not be called with --no-report"
    )


def test_cli_handles_pipeline_exception(tmp_path: Path, monkeypatch, capsys):
    """
    Test that CLI handles exceptions from convert_with_iterations gracefully.
    """
    # Create a dummy input image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    # Mock convert_with_iterations to raise an exception
    def mock_convert_with_error(image_path, max_iters, similarity_threshold, work_root):
        raise RuntimeError("Simulated pipeline failure")

    monkeypatch.setattr(
        "optikz.cli.main.convert_with_iterations", mock_convert_with_error
    )

    monkeypatch.setattr("sys.argv", ["optikz", str(input_img)])

    exit_code = main()

    assert exit_code == 1, "CLI should exit with code 1 on pipeline error"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower()
    assert "Simulated pipeline failure" in captured.err


def test_cli_prints_iteration_summary(tmp_path: Path, monkeypatch, capsys):
    """
    Test that CLI prints a summary of iterations with similarity scores.
    """
    # Create a dummy input image
    input_img = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(input_img)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "final_tikz.tex").write_text("\\draw;")
    (run_dir / "final_standalone.tex").write_text("\\doc")

    # Create multiple iterations with different similarity scores
    iterations = []
    for step in range(3):
        iter_dir = run_dir / f"iter_{step}"
        iter_dir.mkdir()
        rendered = iter_dir / "rendered.png"
        img.save(rendered)

        iterations.append(
            IterationResult(
                step=step,
                tikz=f"\\draw {step};",
                rendered_path=rendered,
                similarity=0.5 + (step * 0.2),  # 0.5, 0.7, 0.9
            )
        )

    def mock_convert(image_path, max_iters, similarity_threshold, work_root):
        return RunResult(final_tikz="\\draw 2;", iterations=iterations, run_dir=run_dir)

    monkeypatch.setattr("optikz.cli.main.convert_with_iterations", mock_convert)
    monkeypatch.setattr(
        "optikz.cli.main.write_html_report",
        lambda r: r.run_dir / "report.html",
    )

    monkeypatch.setattr("sys.argv", ["optikz", str(input_img)])

    exit_code = main()

    assert exit_code == 0

    captured = capsys.readouterr()
    # Check that iteration summary is printed
    assert "Step 0" in captured.out
    assert "Step 1" in captured.out
    assert "Step 2" in captured.out

    # Check similarity scores appear
    assert "0.5000" in captured.out or "0.50" in captured.out
    assert "0.7000" in captured.out or "0.70" in captured.out
    assert "0.9000" in captured.out or "0.90" in captured.out

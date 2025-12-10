"""
Tests for TikZ rendering and image similarity calculation.

These tests verify render_tikz and calc_similarity behavior without
requiring actual LaTeX toolchain by default. An optional integration
test is included for testing with real pdflatex.
"""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from optikz.core.render import calc_similarity, render_tikz


def test_render_tikz_subprocess_invocation(tmp_path: Path, monkeypatch):
    """
    Test that render_tikz calls subprocess.run with expected arguments.

    Mocks subprocess.run to verify:
    - pdflatex is called with correct arguments
    - gs (Ghostscript) is called to convert PDF to PNG
    - The .tex file is written correctly
    - The function returns the expected PNG path
    """
    tikz_code = r"\draw (0,0) -- (1,1);"
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    # Track subprocess calls
    subprocess_calls = []

    # Mock subprocess.run
    def mock_subprocess_run(cmd, **kwargs):
        subprocess_calls.append(cmd)

        # Create dummy output files based on the command
        if cmd[0] == "pdflatex":
            # Create dummy PDF
            cwd = kwargs.get("cwd", Path.cwd())
            pdf_path = cwd / "diagram.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nDummy PDF content")
        elif cmd[0] == "gs":
            # Create dummy PNG
            # Extract output file from gs command
            for i, arg in enumerate(cmd):
                if arg.startswith("-sOutputFile="):
                    png_path = Path(arg.split("=", 1)[1])
                    png_path.parent.mkdir(parents=True, exist_ok=True)
                    # Create a small dummy PNG
                    img = Image.new("RGB", (50, 50), color="white")
                    img.save(png_path)
                    break

        # Return a mock result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        return mock_result

    # Mock shutil.which to say tools exist
    def mock_which(tool):
        if tool in ("pdflatex", "gs"):
            return f"/usr/bin/{tool}"
        return None

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_which)

    # Call render_tikz
    result_png = render_tikz(tikz_code, out_dir)

    # Assertions
    assert result_png == out_dir / "rendered.png"
    assert result_png.exists()

    # Verify subprocess calls
    assert len(subprocess_calls) == 2, "Should call pdflatex and gs"

    # Check pdflatex call
    pdflatex_call = subprocess_calls[0]
    assert pdflatex_call[0] == "pdflatex"
    assert "-interaction=nonstopmode" in pdflatex_call
    assert "-halt-on-error" in pdflatex_call
    assert "diagram.tex" in pdflatex_call

    # Check gs call
    gs_call = subprocess_calls[1]
    assert gs_call[0] == "gs"
    assert "-sDEVICE=png16m" in gs_call
    assert "-r300" in gs_call
    assert any("-sOutputFile=" in arg for arg in gs_call)


def test_render_tikz_creates_latex_document(tmp_path: Path, monkeypatch):
    """
    Test that render_tikz creates a proper LaTeX document.

    Verifies that the .tex file is created with correct structure
    (standalone class, tikzpicture environment, etc.)
    """
    tikz_code = r"\node at (0,0) {Hello};"
    out_dir = tmp_path / "output"

    # Mock tools to exist
    monkeypatch.setattr("shutil.which", lambda tool: f"/usr/bin/{tool}")

    # Track the .tex file content
    tex_content = None

    def mock_subprocess_run(cmd, **kwargs):
        nonlocal tex_content
        cwd = kwargs.get("cwd", Path.cwd())

        # Capture the tex file content
        if cmd[0] == "pdflatex":
            tex_file = cwd / "diagram.tex"
            if tex_file.exists():
                tex_content = tex_file.read_text()
            # Create dummy PDF
            (cwd / "diagram.pdf").write_bytes(b"%PDF")
        elif cmd[0] == "gs":
            # Create dummy PNG
            for arg in cmd:
                if arg.startswith("-sOutputFile="):
                    png_path = Path(arg.split("=", 1)[1])
                    png_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.new("RGB", (50, 50), color="white")
                    img.save(png_path)

        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    # Render
    render_tikz(tikz_code, out_dir)

    # Verify tex content
    assert tex_content is not None
    assert r"\documentclass[tikz,border=2mm]{standalone}" in tex_content
    assert r"\begin{document}" in tex_content
    assert r"\begin{tikzpicture}" in tex_content
    assert tikz_code in tex_content
    assert r"\end{tikzpicture}" in tex_content
    assert r"\end{document}" in tex_content


def test_render_tikz_raises_if_tools_missing(tmp_path: Path, monkeypatch):
    """
    Test that render_tikz raises FileNotFoundError if pdflatex or gs are not found.
    """
    tikz_code = r"\draw (0,0) -- (1,1);"
    out_dir = tmp_path / "output"

    # Mock shutil.which to say pdflatex is missing
    monkeypatch.setattr("shutil.which", lambda tool: None)

    with pytest.raises(FileNotFoundError, match="pdflatex not found"):
        render_tikz(tikz_code, out_dir)

    # Mock to say pdflatex exists but gs is missing
    def mock_which(tool):
        return "/usr/bin/pdflatex" if tool == "pdflatex" else None

    monkeypatch.setattr("shutil.which", mock_which)

    with pytest.raises(FileNotFoundError, match="gs.*Ghostscript.*not found"):
        render_tikz(tikz_code, out_dir)


def test_render_tikz_raises_on_pdflatex_failure(tmp_path: Path, monkeypatch):
    """
    Test that render_tikz raises RuntimeError if pdflatex fails.
    """
    tikz_code = r"\invalid command;"
    out_dir = tmp_path / "output"

    # Mock tools to exist
    monkeypatch.setattr("shutil.which", lambda tool: f"/usr/bin/{tool}")

    # Mock subprocess to simulate pdflatex failure
    def mock_subprocess_run(cmd, **kwargs):
        if cmd[0] == "pdflatex":
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=cmd,
                stderr="! Undefined control sequence.",
                output="LaTeX error output",
            )
        return MagicMock(returncode=0)

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    with pytest.raises(RuntimeError, match="pdflatex compilation failed"):
        render_tikz(tikz_code, out_dir)


def test_calc_similarity_basic(tmp_path: Path):
    """
    Test that calc_similarity returns a value in [0, 1] for valid images.

    Creates two similar images and verifies that:
    - The similarity score is computed
    - The score is in the valid range [0, 1]
    - Similar images have higher scores than dissimilar ones
    """
    # Create two identical images
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"

    img = Image.new("RGB", (100, 100), color="blue")
    img.save(img1_path)
    img.save(img2_path)

    # Calculate similarity (should be 1.0 for identical images)
    sim = calc_similarity(img1_path, img2_path)
    assert 0.0 <= sim <= 1.0, "Similarity should be in [0, 1]"
    assert sim > 0.99, "Identical images should have very high similarity"

    # Create a different image
    img3_path = tmp_path / "img3.png"
    img_diff = Image.new("RGB", (100, 100), color="red")
    img_diff.save(img3_path)

    # Compare different images
    sim_diff = calc_similarity(img1_path, img3_path)
    assert 0.0 <= sim_diff <= 1.0
    assert sim_diff < sim, "Different images should have lower similarity"


def test_calc_similarity_handles_different_sizes(tmp_path: Path):
    """
    Test that calc_similarity can handle images of different sizes.

    The function should resize images to a fixed size before comparison.
    """
    img1_path = tmp_path / "small.png"
    img2_path = tmp_path / "large.png"

    # Create images of different sizes with same color
    img1 = Image.new("RGB", (50, 50), color="green")
    img1.save(img1_path)

    img2 = Image.new("RGB", (200, 200), color="green")
    img2.save(img2_path)

    # Should work without error and give high similarity
    sim = calc_similarity(img1_path, img2_path)
    assert 0.0 <= sim <= 1.0
    # Due to resizing artifacts, might not be perfect 1.0, but should be very high
    assert sim > 0.9


def test_calc_similarity_raises_for_missing_images(tmp_path: Path):
    """
    Test that calc_similarity raises FileNotFoundError for non-existent images.
    """
    img1_path = tmp_path / "exists.png"
    img2_path = tmp_path / "missing.png"

    # Create only one image
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img1_path)

    # Should raise for missing target
    with pytest.raises(FileNotFoundError, match="Target image not found"):
        calc_similarity(tmp_path / "missing_target.png", img1_path)

    # Should raise for missing rendered
    with pytest.raises(FileNotFoundError, match="Rendered image not found"):
        calc_similarity(img1_path, img2_path)


@pytest.mark.integration
def test_render_tikz_integration(tmp_path: Path):
    """
    Integration test: actually render TikZ with real pdflatex and gs.

    This test is marked as 'integration' and will be skipped if pdflatex
    or gs are not available on the system.
    """
    # Check if tools are available
    if not shutil.which("pdflatex"):
        pytest.skip("pdflatex not available")
    if not shutil.which("gs"):
        pytest.skip("Ghostscript (gs) not available")

    # Simple TikZ code
    tikz_code = r"""
    \draw[thick,->] (0,0) -- (2,0) node[right] {$x$};
    \draw[thick,->] (0,0) -- (0,2) node[above] {$y$};
    \draw[red,thick] (0,0) circle (1);
    """

    out_dir = tmp_path / "integration_output"

    # Render
    try:
        result_png = render_tikz(tikz_code, out_dir)
    except Exception as e:
        pytest.fail(f"render_tikz failed: {e}")

    # Verify output
    assert result_png.exists(), "PNG should be created"
    assert result_png.suffix == ".png"

    # Verify it's a valid image
    try:
        img = Image.open(result_png)
        # Should have some reasonable size (300 DPI output)
        assert img.width > 0
        assert img.height > 0
    except Exception as e:
        pytest.fail(f"Output PNG is not a valid image: {e}")

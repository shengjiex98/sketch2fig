"""
Tests for HTML report generation.

These tests verify that write_html_report creates a valid HTML file
with the expected content structure.
"""

from optikz.core.report import write_html_report


def test_write_html_report_creates_file(fake_iteration_results):
    """
    Test that write_html_report creates an HTML file in the run directory.

    Uses the fake_iteration_results fixture to generate a report.
    """
    result = fake_iteration_results

    # Generate report
    report_path = write_html_report(result)

    # Verify report was created
    assert report_path.exists()
    assert report_path.suffix == ".html"
    assert report_path.parent == result.run_dir
    assert report_path.name == "report.html"


def test_write_html_report_contains_required_content(fake_iteration_results):
    """
    Test that the generated HTML report contains all required sections.

    Verifies:
    - HTML structure (DOCTYPE, html, head, body tags)
    - Summary section with run info
    - Original image display
    - Iteration sections with rendered images
    - TikZ code display
    """
    result = fake_iteration_results

    # Generate report
    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # Check basic HTML structure
    assert "<!DOCTYPE html>" in html_content
    assert "<html" in html_content
    assert "</html>" in html_content
    assert "<head>" in html_content
    assert "<body>" in html_content

    # Check title
    assert "<title>TikZ Refinement Report</title>" in html_content

    # Check summary section
    assert "Summary" in html_content
    assert "Run directory:" in html_content
    assert "Number of iterations:" in html_content
    assert "Final similarity:" in html_content

    # Check that it mentions the number of iterations
    assert "3" in html_content  # fake_iteration_results has 3 iterations

    # Check original image section
    assert "Original Target Image" in html_content
    assert '<img src="data:image/png;base64,' in html_content

    # Check iteration sections
    assert "Iteration 0" in html_content
    assert "Iteration 1" in html_content
    assert "Iteration 2" in html_content

    # Check that similarity scores are shown
    assert "Similarity:" in html_content

    # Check TikZ code display
    assert "TikZ Code:" in html_content
    assert "<pre>" in html_content
    assert r"\draw" in html_content  # TikZ code from fixture


def test_write_html_report_shows_tikz_code_for_each_iteration(fake_iteration_results):
    """
    Test that each iteration's TikZ code is displayed in the report.

    The TikZ code should be visible and properly formatted (e.g., in <pre> tags).
    """
    result = fake_iteration_results

    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # Each iteration in the fixture has TikZ code like "% Iteration 0", "% Iteration 1", etc.
    for iteration in result.iterations:
        assert f"Iteration {iteration.step}" in html_content

        # Check that the TikZ code is present and escaped properly
        # The fixture creates code like "% Iteration {step}\n\draw (0,0) -- (1,1);\n"
        assert f"% Iteration {iteration.step}" in html_content
        assert r"\draw" in html_content


def test_write_html_report_references_rendered_images(fake_iteration_results):
    """
    Test that the report includes image references for each iteration.

    Each rendered PNG should be embedded as a data URI in an <img> tag.
    """
    result = fake_iteration_results

    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # Should have at least one img tag per iteration (plus original)
    # fake_iteration_results has 3 iterations + 1 original = 4 images minimum
    img_count = html_content.count("<img")
    assert img_count >= 4, f"Expected at least 4 img tags, found {img_count}"

    # All images should be data URIs (base64 encoded)
    # Check that data URI format is present
    data_uri_count = html_content.count('src="data:image/png;base64,')
    assert data_uri_count >= 4, f"Expected at least 4 data URIs, found {data_uri_count}"


def test_write_html_report_similarity_scores(fake_iteration_results):
    """
    Test that similarity scores are displayed correctly in the report.

    The fixture has similarity scores: 0.5, 0.7, 0.9
    These should appear in the HTML.
    """
    result = fake_iteration_results

    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # Check for the specific similarity values from the fixture
    # fake_iteration_results creates similarities: 0.5, 0.7, 0.9
    assert "0.5000" in html_content or "0.50" in html_content
    assert "0.7000" in html_content or "0.70" in html_content
    assert "0.9000" in html_content or "0.90" in html_content


def test_write_html_report_handles_special_html_characters(tmp_path):
    """
    Test that TikZ code with special HTML characters is properly escaped.

    TikZ often contains <, >, & which must be escaped in HTML.
    """
    from PIL import Image

    from optikz.core.pipeline import IterationResult, RunResult

    run_dir = tmp_path / "run_test"
    run_dir.mkdir()

    # Create original image
    original = run_dir / "original.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(original)

    # Create an iteration with TikZ containing HTML special chars
    iter_dir = run_dir / "iter_0"
    iter_dir.mkdir()
    rendered = iter_dir / "rendered.png"
    img.save(rendered)

    tikz_with_special_chars = r"""
    \node at (0,0) {$x < y$ and $a > b$ & $c$};
    """

    iteration = IterationResult(
        step=0,
        tikz=tikz_with_special_chars,
        rendered_path=rendered,
        similarity=0.8,
    )

    result = RunResult(
        final_tikz=tikz_with_special_chars,
        iterations=[iteration],
        run_dir=run_dir,
    )

    # Generate report
    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # Verify that special characters are escaped
    # The HTML should contain &lt; and &gt; instead of < and >
    assert "&lt;" in html_content  # < should be escaped
    assert "&gt;" in html_content  # > should be escaped
    assert "&amp;" in html_content  # & should be escaped

    # The literal characters should NOT appear in code blocks
    # (though they might appear in HTML tags themselves)
    # Check within the pre blocks specifically
    pre_blocks = html_content.split("<pre>")
    for i in range(1, len(pre_blocks)):  # Skip first split (before any <pre>)
        pre_content = pre_blocks[i].split("</pre>")[0]
        # Within pre blocks, we should see escaped versions
        if "$x" in pre_content:  # This is our TikZ code
            assert "&lt;" in pre_content
            assert "&gt;" in pre_content


def test_write_html_report_run_directory_name(fake_iteration_results):
    """
    Test that the report displays the run directory name.

    The summary should show the run directory name.
    """
    result = fake_iteration_results

    report_path = write_html_report(result)
    html_content = report_path.read_text()

    # The run directory name should appear in the summary
    run_dir_name = result.run_dir.name
    assert run_dir_name in html_content

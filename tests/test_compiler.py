"""Tests for sketch2fig.compiler — Tier 1 (fast) and Tier 2 (slow)."""

import pytest
from pathlib import Path

from sketch2fig.compiler import wrap_in_document, parse_errors, compile_tikz, render_to_image

FIXTURES = Path(__file__).parent / "fixtures"

_SIMPLE_TIKZ = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"
_BAD_TIKZ = r"\begin{tikzpicture}\badcommand{foo}\end{tikzpicture}"


# ── Tier 1: fast, no LaTeX required ──────────────────────────────────────────

class TestWrapInDocument:
    def test_contains_documentclass(self):
        result = wrap_in_document(_SIMPLE_TIKZ)
        assert r"\documentclass" in result

    def test_uses_standalone(self):
        result = wrap_in_document(_SIMPLE_TIKZ)
        assert "standalone" in result

    def test_contains_tikz_block(self):
        result = wrap_in_document(_SIMPLE_TIKZ)
        assert r"\begin{tikzpicture}" in result

    def test_has_begin_document(self):
        result = wrap_in_document(_SIMPLE_TIKZ)
        assert r"\begin{document}" in result
        assert r"\end{document}" in result

    def test_custom_preamble_included(self):
        result = wrap_in_document(_SIMPLE_TIKZ, preamble=r"\usepackage{xcolor}")
        assert r"\usepackage{xcolor}" in result

    def test_border_option_present(self):
        result = wrap_in_document(_SIMPLE_TIKZ)
        assert "border=5pt" in result


class TestParseErrors:
    def test_extracts_line_number(self):
        log = (
            "! Undefined control sequence.\n"
            "l.42 \\badcommand\n"
            "                {foo}\n"
        )
        errors = parse_errors(log)
        assert len(errors) >= 1
        assert errors[0].line == 42

    def test_extracts_message(self):
        log = (
            "! Undefined control sequence.\n"
            "l.42 \\badcommand\n"
        )
        errors = parse_errors(log)
        assert "Undefined control sequence" in errors[0].message

    def test_no_errors_on_clean_log(self):
        log = "This is pdfTeX, Version 3.14\nOutput written on figure.pdf\n"
        errors = parse_errors(log)
        assert errors == []

    def test_missing_dollar_error(self):
        log = (
            "! Missing $ inserted.\n"
            "l.10 \\alpha\n"
        )
        errors = parse_errors(log)
        assert errors[0].line == 10
        assert "Missing $ inserted" in errors[0].message

    def test_only_first_error_returned(self):
        log = (
            "! First error.\n"
            "l.5 \\foo\n"
            "! Second error.\n"
            "l.10 \\bar\n"
        )
        errors = parse_errors(log)
        assert len(errors) == 1
        assert "First error" in errors[0].message

    def test_error_without_line_number(self):
        log = "! File ended while scanning.\n"
        errors = parse_errors(log)
        assert len(errors) == 1
        assert errors[0].line is None


# ── Tier 2: slow, requires LaTeX ─────────────────────────────────────────────

@pytest.mark.slow
def test_simple_tikz_compiles():
    """Known-good TikZ compiles successfully."""
    pdf_path, log = compile_tikz(_SIMPLE_TIKZ)
    assert pdf_path is not None, f"Compilation failed:\n{log}"
    assert pdf_path.exists()


@pytest.mark.slow
def test_bad_tikz_fails_with_error():
    """Known-bad TikZ fails and returns a parseable error."""
    pdf_path, log = compile_tikz(_BAD_TIKZ)
    assert pdf_path is None, "Expected compilation to fail"
    errors = parse_errors(log)
    assert len(errors) >= 1


@pytest.mark.slow
def test_reference_fixture_compiles():
    """The simple_pipeline reference fixture compiles without error."""
    tex = (FIXTURES / "simple_pipeline" / "reference.tex").read_text()
    pdf_path, log = compile_tikz(tex)
    assert pdf_path is not None, f"Reference fixture compilation failed:\n{log}"


@pytest.mark.slow
def test_reference_fixture_renders_to_image():
    """The simple_pipeline reference fixture renders to a PNG image."""
    tex = (FIXTURES / "simple_pipeline" / "reference.tex").read_text()
    pdf_path, log = compile_tikz(tex)
    assert pdf_path is not None, f"Compilation failed:\n{log}"

    img = render_to_image(pdf_path)
    assert img.width > 0
    assert img.height > 0

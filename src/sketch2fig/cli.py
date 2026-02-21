"""CLI entry point for sketch2fig."""

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from .orchestrator import convert as _convert

app = typer.Typer(help="Convert figure sketches to publication-quality TikZ code.")


@app.callback()
def _main() -> None:
    """sketch2fig — agentic TikZ code generator."""


def _setup_logging(verbose: bool) -> None:
    # Root handler at WARNING so third-party libs (httpx, PIL, anthropic) stay quiet.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    # Our own loggers get INFO normally, DEBUG with -v.
    logging.getLogger("sketch2fig").setLevel(logging.DEBUG if verbose else logging.INFO)


@app.command()
def convert(
    input_image: Annotated[Path, typer.Argument(help="Input figure image (PNG, JPEG, etc.)")],
    clean: Annotated[bool, typer.Option("--clean", help="Prompt for improved alignment and spacing")] = False,
    max_iters: Annotated[int, typer.Option("--max-iters", help="Maximum refinement iterations")] = 5,
    output_dir: Annotated[Path | None, typer.Option("--output-dir", help="Output directory")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show debug logs")] = False,
) -> None:
    """Convert a figure image to TikZ code using an agentic Plan→Generate→Compile→Evaluate loop."""
    _setup_logging(verbose)

    if not input_image.exists():
        typer.echo(f"Error: {input_image} does not exist.", err=True)
        raise typer.Exit(1)

    out = output_dir or Path("output") / input_image.stem

    result = _convert(
        input_image=input_image,
        output_dir=out,
        clean=clean,
        max_iters=max_iters,
    )

    if result is None:
        typer.echo("Error: Failed to compile TikZ code in any iteration.", err=True)
        raise typer.Exit(1)

    status = "PASS" if result.passed else "FAIL (below quality threshold)"
    typer.echo(f"\nDone in {result.iterations} iteration(s) — score: {result.overall:.2f} — {status}")
    typer.echo(f"  TikZ: {result.tex_path}")
    typer.echo(f"  PNG:  {result.png_path}")

    if not result.passed:
        sys.exit(0)  # not an error, just informational

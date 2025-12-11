#!/usr/bin/env python3
"""
Command-line interface for optikz.

Usage:
    optikz input.png
    optikz input.png --iters 5 --threshold 0.95
    optikz input.png --work-root my_runs/ --open-report
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from optikz.core import convert_with_iterations, write_html_report


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description=(
            "Convert diagram images to TikZ code using vision LLMs with iterative "
            "refinement."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s diagram.png
  %(prog)s diagram.png --iters 5 --threshold 0.95
  %(prog)s diagram.png --work-root my_runs/ --open-report
        """,
    )

    # Load environment variables early so API clients see them
    load_dotenv(".env.local")
    load_dotenv()

    parser.add_argument(
        "image",
        type=Path,
        help="Path to input diagram image (PNG/JPEG)",
    )

    parser.add_argument(
        "--iters",
        type=int,
        default=3,
        help="Maximum number of refinement iterations (default: 3)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Similarity threshold for early stopping (default: 0.9)",
    )

    parser.add_argument(
        "--work-root",
        type=Path,
        default=None,
        help="Root directory for outputs (default: ./runs)",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open HTML report in browser after completion",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip HTML report generation",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.image.exists():
        print(f"Error: Input image not found: {args.image}", file=sys.stderr)
        return 1

    if args.iters < 1:
        print("Error: --iters must be >= 1", file=sys.stderr)
        return 1

    if not 0.0 <= args.threshold <= 1.0:
        print("Error: --threshold must be in [0, 1]", file=sys.stderr)
        return 1

    # Run the pipeline
    print("=" * 60)
    print("optikz: Image → TikZ conversion with refinement")
    print("=" * 60)

    try:
        result = convert_with_iterations(
            image_path=args.image,
            max_iters=args.iters,
            similarity_threshold=args.threshold,
            work_root=args.work_root,
        )
    except Exception as e:
        print(f"\nError during conversion: {e}", file=sys.stderr)
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Run directory: {result.run_dir}")
    print(f"Total iterations: {len(result.iterations)}")
    print("\nIteration summary:")
    for iteration in result.iterations:
        sim_str = f"{iteration.similarity:.4f}" if iteration.similarity else "N/A"
        print(f"  Step {iteration.step}: similarity = {sim_str}")

    final_tikz_path = result.run_dir / "final_tikz.tex"
    print(f"\nFinal TikZ code saved to: {final_tikz_path}")

    standalone_path = result.run_dir / "final_standalone.tex"
    print(f"Standalone document: {standalone_path}")
    print(f"  (Compile with: pdflatex {standalone_path.name})")

    # Generate HTML report unless disabled
    if not args.no_report:
        print("\nGenerating HTML report...")
        try:
            report_path = write_html_report(result)
            print(f"Report saved to: {report_path}")

            if args.open_report:
                print("Opening report in browser...")
                webbrowser.open(f"file://{report_path.resolve()}")
        except Exception as e:
            print(f"Warning: Failed to generate report: {e}", file=sys.stderr)

    print("\n" + "=" * 60)
    print("✓ Conversion complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Main pipeline for iterative TikZ generation and refinement.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .llm import initial_tikz_from_llm, refine_tikz_via_llm
from .render import calc_similarity, render_tikz


@dataclass
class IterationResult:
    """
    Results from a single iteration of the refinement loop.

    Attributes:
        step: Iteration number (0-based)
        tikz: TikZ code for this iteration
        rendered_path: Path to the rendered PNG
        similarity: Similarity score vs target (None if not computed)
    """

    step: int
    tikz: str
    rendered_path: Path
    similarity: float | None


@dataclass
class RunResult:
    """
    Complete results from a refinement run.

    Attributes:
        final_tikz: The final TikZ code
        iterations: List of all iteration results
        run_dir: Directory containing all output files
    """

    final_tikz: str
    iterations: list[IterationResult]
    run_dir: Path


def convert_with_iterations(
    image_path: Path,
    max_iters: int = 3,
    similarity_threshold: float = 0.9,
    work_root: Path | None = None,
) -> RunResult:
    """
    Convert a diagram image to TikZ with iterative refinement.

    Process:
    1. Create a timestamped run directory
    2. Generate initial TikZ from the image
    3. Iteratively:
       - Render TikZ to PNG
       - Calculate similarity to original
       - Stop if threshold met or max iterations reached
       - Otherwise, refine TikZ using LLM
    4. Return complete results

    Args:
        image_path: Path to input diagram (PNG/JPEG)
        max_iters: Maximum number of refinement iterations
        similarity_threshold: Stop if similarity >= this value
        work_root: Root directory for outputs (default: ./runs)

    Returns:
        RunResult containing all iterations and final TikZ

    Raises:
        FileNotFoundError: If image_path does not exist
        RuntimeError: If rendering or LLM calls fail
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    # Set up work directory
    if work_root is None:
        work_root = Path.cwd() / "runs"

    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = work_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Copy original image to run directory for reference
    import shutil
    original_copy = run_dir / f"original{image_path.suffix}"
    shutil.copy(image_path, original_copy)

    print(f"Starting conversion run in: {run_dir}")
    print(f"Max iterations: {max_iters}, Threshold: {similarity_threshold}")

    # Step 0: Generate initial TikZ
    print("\n[Step 0] Generating initial TikZ from image...")
    current_tikz = initial_tikz_from_llm(image_path)

    # Save initial TikZ
    (run_dir / "iteration_0.tex").write_text(current_tikz)

    iterations: list[IterationResult] = []

    # Iterative refinement loop
    for step in range(max_iters):
        print(f"\n[Step {step}] Rendering TikZ...")

        # Create iteration subdirectory
        iter_dir = run_dir / f"iter_{step}"
        iter_dir.mkdir(exist_ok=True)

        # Render current TikZ
        try:
            rendered_path = render_tikz(current_tikz, iter_dir)
        except Exception as e:
            print(f"Warning: Rendering failed at step {step}: {e}")
            # Save the failed TikZ for inspection
            (iter_dir / "failed.tex").write_text(current_tikz)
            raise

        # Calculate similarity
        print(f"[Step {step}] Calculating similarity...")
        similarity = calc_similarity(image_path, rendered_path)
        print(f"[Step {step}] Similarity: {similarity:.4f}")

        # Record iteration result
        iterations.append(
            IterationResult(
                step=step,
                tikz=current_tikz,
                rendered_path=rendered_path,
                similarity=similarity,
            )
        )

        # Check stopping conditions
        if similarity >= similarity_threshold:
            print(
                f"\n✓ Threshold reached! Similarity {similarity:.4f} >= {similarity_threshold}"
            )
            break

        if step == max_iters - 1:
            print(f"\n✓ Max iterations ({max_iters}) reached.")
            break

        # Refine TikZ for next iteration
        print(f"[Step {step}] Refining TikZ via LLM...")
        try:
            current_tikz = refine_tikz_via_llm(
                original_image_path=image_path,
                rendered_image_path=rendered_path,
                current_tikz=current_tikz,
            )
        except Exception as e:
            print(f"Warning: Refinement failed at step {step}: {e}")
            raise

        # Save refined TikZ for next iteration
        (run_dir / f"iteration_{step + 1}.tex").write_text(current_tikz)

    # Save final TikZ
    final_tikz_path = run_dir / "final_tikz.tex"
    final_tikz_path.write_text(current_tikz)
    print(f"\n✓ Final TikZ saved to: {final_tikz_path}")

    # Create complete LaTeX document for easy compilation
    standalone_doc = r"""\documentclass[tikz,border=2mm]{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes,arrows,positioning,calc,patterns,decorations.pathreplacing}

\begin{document}
\begin{tikzpicture}
""" + current_tikz + r"""
\end{tikzpicture}
\end{document}
"""
    (run_dir / "final_standalone.tex").write_text(standalone_doc)

    return RunResult(
        final_tikz=current_tikz,
        iterations=iterations,
        run_dir=run_dir,
    )

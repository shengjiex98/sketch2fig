"""
HTML report generation for visualizing refinement iterations.
"""

import base64
from pathlib import Path

from .pipeline import RunResult


def write_html_report(result: RunResult) -> Path:
    """
    Generate a self-contained HTML report showing all refinement iterations.

    The report includes:
    - Original image
    - For each iteration: step number, similarity, rendered image, TikZ code

    Args:
        result: RunResult from convert_with_iterations

    Returns:
        Path to the generated HTML file

    Raises:
        FileNotFoundError: If referenced images don't exist
    """
    report_path = result.run_dir / "report.html"

    # Helper to encode image as base64 data URI
    def image_to_data_uri(img_path: Path) -> str:
        if not img_path.exists():
            return ""
        with open(img_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        # Determine MIME type
        ext = img_path.suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        return f"data:{mime};base64,{img_data}"

    # Find original image
    original_path = result.run_dir / "original.png"
    if not original_path.exists():
        original_path = result.run_dir / "original.jpg"
    if not original_path.exists():
        original_path = result.run_dir / "original.jpeg"

    original_uri = image_to_data_uri(original_path) if original_path.exists() else ""

    # Build HTML
    html_parts = [
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikZ Refinement Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #007acc;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .summary {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary p {
            margin: 8px 0;
        }
        .original {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .original img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .iteration {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .iteration h3 {
            margin-top: 0;
            color: #007acc;
        }
        .iteration img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }
        .similarity {
            display: inline-block;
            background: #e8f4f8;
            color: #007acc;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            margin-left: 10px;
        }
        .similarity.high {
            background: #d4edda;
            color: #155724;
        }
        .tikz-code {
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            overflow-x: auto;
            font-family: "Monaco", "Courier New", monospace;
            font-size: 13px;
            line-height: 1.5;
            margin: 10px 0;
        }
        .tikz-code pre {
            margin: 0;
        }
    </style>
</head>
<body>
    <h1>TikZ Refinement Report</h1>
"""
    ]

    # Summary section
    num_iters = len(result.iterations)
    final_sim = result.iterations[-1].similarity if result.iterations else None
    final_sim_str = f"{final_sim:.4f}" if final_sim is not None else "N/A"
    html_parts.append(f"""
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Run directory:</strong> <code>{result.run_dir.name}</code></p>
        <p><strong>Number of iterations:</strong> {num_iters}</p>
        <p><strong>Final similarity:</strong> {final_sim_str}</p>
    </div>
""")

    # Original image section
    if original_uri:
        html_parts.append(f"""
    <div class="original">
        <h2>Original Target Image</h2>
        <img src="{original_uri}" alt="Original diagram">
    </div>
""")

    # Iterations section
    html_parts.append("<h2>Refinement Iterations</h2>")

    for iteration in result.iterations:
        # Determine similarity class for styling
        sim_class = "high" if iteration.similarity and iteration.similarity >= 0.9 else ""

        rendered_uri = image_to_data_uri(iteration.rendered_path)

        # Escape TikZ code for HTML
        tikz_escaped = (
            iteration.tikz.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        iter_sim_str = f"{iteration.similarity:.4f}" if iteration.similarity is not None else "N/A"
        html_parts.append(f"""
    <div class="iteration">
        <h3>
            Iteration {iteration.step}
            <span class="similarity {sim_class}">
                Similarity: {iter_sim_str}
            </span>
        </h3>
        <img src="{rendered_uri}" alt="Rendered iteration {iteration.step}">
        <h4>TikZ Code:</h4>
        <div class="tikz-code">
            <pre>{tikz_escaped}</pre>
        </div>
    </div>
""")

    # Close HTML
    html_parts.append("""
</body>
</html>
""")

    # Write report
    html_content = "".join(html_parts)
    report_path.write_text(html_content)

    return report_path

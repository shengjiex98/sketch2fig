"""
LLM integration for TikZ generation and refinement.

Uses OpenAI's vision-capable models (GPT-4 Vision/GPT-4o).
Assumes OPENAI_API_KEY is set in environment.
"""

import base64
import os
from pathlib import Path

from openai import OpenAI


# TODO: Make model configurable via environment or config
DEFAULT_MODEL = "gpt-4o"


def _encode_image(image_path: Path) -> str:
    """
    Encode an image file to base64 for OpenAI API.

    Args:
        image_path: Path to the image file

    Returns:
        Base64-encoded string of the image
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def initial_tikz_from_llm(image_path: Path) -> str:
    """
    Generate initial TikZ code from an input diagram image.

    Args:
        image_path: Path to the input diagram image (PNG/JPEG)

    Returns:
        TikZ code as a string (without surrounding LaTeX document)

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        FileNotFoundError: If image_path does not exist
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    client = OpenAI()

    # Encode image
    base64_image = _encode_image(image_path)
    image_ext = image_path.suffix.lower()
    mime_type = "image/png" if image_ext == ".png" else "image/jpeg"

    # Prompt for initial generation
    # Key requirements:
    # - Output only TikZ code (no surrounding document)
    # - Use standalone-compatible syntax
    # - Be precise about coordinates and styling
    prompt = """
You are an expert at converting diagrams to TikZ (LaTeX graphics) code.

Analyze the provided diagram image and generate clean, accurate TikZ code that reproduces it.

Requirements:
- Output ONLY the TikZ code itself (the contents that would go inside \\begin{tikzpicture}...\\end{tikzpicture})
- Do NOT include \\documentclass, \\begin{document}, or other LaTeX boilerplate
- Use precise coordinates and measurements
- Match colors, line styles, shapes, and text as closely as possible
- Use appropriate TikZ libraries if needed (mention them in a comment at the top)
- Keep the code clean and well-organized

Output the TikZ code directly without additional explanation.
""".strip()

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        max_tokens=2000,
        temperature=0.2,  # Lower temperature for more consistent output
    )

    tikz_code = response.choices[0].message.content or ""

    # Clean up response: remove markdown code fences if present
    tikz_code = tikz_code.strip()
    if tikz_code.startswith("```"):
        lines = tikz_code.split("\n")
        # Remove first and last lines if they're fence markers
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        tikz_code = "\n".join(lines)

    return tikz_code.strip()


def refine_tikz_via_llm(
    original_image_path: Path,
    rendered_image_path: Path,
    current_tikz: str,
) -> str:
    """
    Refine existing TikZ code by comparing original and rendered images.

    Args:
        original_image_path: Path to the original target diagram
        rendered_image_path: Path to the currently rendered TikZ output
        current_tikz: The current TikZ code to refine

    Returns:
        Refined TikZ code as a string

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        FileNotFoundError: If either image path does not exist
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    if not original_image_path.exists():
        raise FileNotFoundError(f"Original image not found: {original_image_path}")

    if not rendered_image_path.exists():
        raise FileNotFoundError(f"Rendered image not found: {rendered_image_path}")

    client = OpenAI()

    # Encode both images
    original_b64 = _encode_image(original_image_path)
    rendered_b64 = _encode_image(rendered_image_path)

    # Determine MIME types
    orig_ext = original_image_path.suffix.lower()
    rend_ext = rendered_image_path.suffix.lower()
    orig_mime = "image/png" if orig_ext == ".png" else "image/jpeg"
    rend_mime = "image/png" if rend_ext == ".png" else "image/jpeg"

    # Prompt for refinement
    # Ask the LLM to compare and correct
    prompt = f"""
You are an expert at refining TikZ code to match target diagrams.

I will provide:
1. The ORIGINAL target diagram (what we want to match)
2. The RENDERED output from current TikZ code
3. The CURRENT TikZ code

Your task:
- Compare the original and rendered images
- Identify differences (position, size, color, style, text, etc.)
- Output CORRECTED TikZ code that better matches the original

Requirements:
- Output ONLY the corrected TikZ code (contents of \\begin{{tikzpicture}}...\\end{{tikzpicture}})
- Do NOT include LaTeX boilerplate
- Focus on fixing the most significant visual differences
- Keep the code clean and maintainable

Current TikZ code:
```
{current_tikz}
```

Now compare the original (target) vs rendered (current output) and provide corrected TikZ code.
""".strip()

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "text",
                        "text": "ORIGINAL (target):"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{orig_mime};base64,{original_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": "RENDERED (current output):"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{rend_mime};base64,{rendered_b64}"
                        },
                    },
                ],
            }
        ],
        max_tokens=2000,
        temperature=0.2,
    )

    tikz_code = response.choices[0].message.content or ""

    # Clean up markdown fences
    tikz_code = tikz_code.strip()
    if tikz_code.startswith("```"):
        lines = tikz_code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        tikz_code = "\n".join(lines)

    return tikz_code.strip()

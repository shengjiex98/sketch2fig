# Configuration Guide

## LLM Model Configuration

The default model is `gpt-4o`. To change it, edit `DEFAULT_MODEL` in [src/img2tikz/core/llm.py](../src/img2tikz/core/llm.py#L15):

```python
DEFAULT_MODEL = "gpt-4-turbo"  # or your preferred model
```

## Swapping LLM Providers

The LLM integration is encapsulated in [src/img2tikz/core/llm.py](../src/img2tikz/core/llm.py). To use a different provider:

1. **Modify the client initialization** in `initial_tikz_from_llm()` and `refine_tikz_via_llm()`
2. **Adjust the API call format** for your provider
3. **Update environment variable handling** for API keys/endpoints

### Example: Using Anthropic Claude

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2000,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64_image,
                    },
                },
            ],
        }
    ],
)
```

The rest of the pipeline remains unchanged.

## TikZ Libraries

The LaTeX preamble includes common TikZ libraries. To add more, edit the `latex_doc` template in [src/img2tikz/core/render.py](../src/img2tikz/core/render.py):

```latex
\usetikzlibrary{shapes,arrows,positioning,calc,patterns,decorations.pathreplacing,graphs}
```

Add any additional libraries you need to this list.

## Image Similarity Configuration

The comparison resizes images to 512×512 before computing SSIM. To change this, edit [src/img2tikz/core/render.py](../src/img2tikz/core/render.py):

```python
fixed_size = (1024, 1024)  # Higher resolution for more precise comparison
```

**Trade-offs:**
- Higher resolution = more accurate comparison but slower processing
- Lower resolution = faster but may miss fine details

## Prompt Customization

Prompts are defined in [src/img2tikz/core/llm.py](../src/img2tikz/core/llm.py):

- `initial_tikz_from_llm()`: Initial generation prompt
- `refine_tikz_via_llm()`: Refinement prompt with visual feedback

You can customize these prompts to:
- Request specific TikZ styles
- Emphasize certain diagram elements
- Add domain-specific instructions
- Control verbosity of output

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

Or export directly:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

## Advanced Configuration

### Custom Work Directory Structure

```python
from pathlib import Path
from img2tikz.core import convert_with_iterations

result = convert_with_iterations(
    image_path=Path("diagram.png"),
    work_root=Path("/custom/output/path"),  # Custom output location
)
```

### Programmatic Control

```python
# Fine-grained control over iterations
from img2tikz.core import initial_tikz_from_llm, render_tikz, calc_similarity, refine_tikz_via_llm

# Generate initial TikZ
tikz = initial_tikz_from_llm(image_path)

# Render and compare
rendered = render_tikz(tikz, output_dir)
similarity = calc_similarity(image_path, rendered)

# Conditional refinement
if similarity < 0.9:
    tikz = refine_tikz_via_llm(image_path, rendered, tikz)
```

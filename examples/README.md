# Example Diagrams

Place sample diagram images here (PNG or JPEG format) to test the conversion pipeline.

## Creating a sample diagram

You can create a simple test diagram using any drawing tool, or generate one programmatically.

For testing purposes, try diagrams with:
- Simple geometric shapes (circles, rectangles, arrows)
- Text labels
- Different line styles
- Basic colors

The more structured and clear the diagram, the better the TikZ conversion will be.

## Running the examples

```bash
# Basic usage
img2tikz examples/your_diagram.png

# With custom parameters
img2tikz examples/your_diagram.png --iters 5 --threshold 0.95 --open-report
```

## Note

Add your own `sample_diagram.png` or `sample_diagram.jpg` to this directory to get started.

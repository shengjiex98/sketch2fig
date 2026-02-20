import logging
from pathlib import Path

from sketch2fig.compiler import compile_tikz, render_to_image
from sketch2fig.generator import generate_tikz
from sketch2fig.planner import plan_figure

logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

img = PROJECT_ROOT / "tests/fixtures/deviation_bound/input.jpg"
plan = plan_figure(img)
tikz = generate_tikz(plan, img)
print(tikz)

pdf, log = compile_tikz(tikz)
if pdf:
    img_out = render_to_image(pdf)
    img_out.save(PROJECT_ROOT / "examples/output.png")
    print("Saved to output.png")
else:
    print("Compile failed:\n", log[-2000:])

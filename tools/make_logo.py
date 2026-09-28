"""Generate the CutMitra logo (assets/logo.png + logo.ico).

Navy rounded square (app theme) + white 'C' sheet ring cut by an orange
saw band with a thin kerf gap. Run from the project root:
    python tools/make_logo.py
Requires: pillow  (pip install pillow)
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

S = 512
NAVY = (31, 56, 100, 255)
WHITE = (255, 255, 255, 255)
ORANGE = (230, 126, 34, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=96, fill=NAVY)
# white 'C' = sheet ring opened on the right
d.ellipse([112, 88, 392, 424], fill=WHITE)
d.ellipse([196, 162, 356, 350], fill=NAVY)
d.rectangle([296, 204, 430, 308], fill=NAVY)
# orange saw band cutting diagonally through it + navy kerf gap
d.polygon([(296, 40), (356, 40), (176, 470), (116, 470)], fill=ORANGE)
d.polygon([(364, 40), (376, 40), (196, 470), (184, 470)], fill=NAVY)

img.save(os.path.join(ASSETS, "logo.png"))
img.save(os.path.join(ASSETS, "logo.ico"),
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                (64, 64), (128, 128), (256, 256)])
print("wrote assets/logo.png + assets/logo.ico")

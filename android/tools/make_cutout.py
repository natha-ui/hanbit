#!/usr/bin/env python3
"""
Cut the tiger out of a painting for the widget.

    pip install "rembg[cpu]" pillow scipy
    python3 make_cutout.py painting.jpg

Uses the u2net background-removal model (downloaded on first run), keeps only the largest shape
(the tiger), makes it solid inside with a soft 1-2 px edge, and writes
app/src/main/res/drawable-nodpi/tiger_cut.webp. Check the result: if the model keeps a patch of
paper or loses a leg, crop the painting closer to the tiger and run it again.
"""
import os, sys
import numpy as np
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage

OUT = os.path.join(os.path.dirname(__file__), "..", "app", "src", "main", "res", "drawable-nodpi", "tiger_cut.webp")

def trim_frame(im, light=235):
    g = np.asarray(im.convert("L")); h, w = g.shape
    rows = np.where((g > light).mean(axis=1) < 0.9)[0]; cols = np.where((g > light).mean(axis=0) < 0.9)[0]
    return im.crop((cols[0] + 1, rows[0] + 1, cols[-1], rows[-1]))

im = trim_frame(Image.open(sys.argv[1]).convert("RGB"))
a = np.asarray(remove(im, session=new_session("u2net")).split()[3]).astype(float) / 255
solid = a > 0.5
lab, n = ndimage.label(solid)
keep = lab == (1 + int(np.argmax(ndimage.sum(solid, lab, range(1, n + 1)))))
keep = ndimage.binary_erosion(ndimage.binary_opening(ndimage.binary_fill_holes(keep), iterations=2), iterations=1)
core = ndimage.binary_erosion(keep, iterations=3)
alpha = np.where(core, 1.0, np.where(keep, np.clip(a * 1.2, 0, 1), 0))
alpha = ndimage.gaussian_filter(alpha, 0.8); alpha[core] = 1
t = Image.fromarray(np.dstack([np.asarray(im), (alpha * 255).astype(np.uint8)]), "RGBA")
t = t.crop(t.getbbox())
if t.height > 600: t = t.resize((round(t.width * 600 / t.height), 600), Image.LANCZOS)
t.save(OUT, "WEBP", quality=90, method=6)
print("Wrote", OUT, t.size)

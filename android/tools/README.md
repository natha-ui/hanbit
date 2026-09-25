The widget shows the tiger cut out of a Joseon-era magpie-and-tiger painting (public domain), standing
down the left side on tinted glass, with three drawn magpies flying at the top right.

- `make_cutout.py <image>` cuts the tiger out of any painting and writes `tiger_cut.webp` into the app.
  Use it to swap in a sharper museum scan.
- `magpie.py` draws the magpies. Print `vector()` to regenerate `res/drawable/magpies.xml`.
- `widget_preview.py` (needs `cairosvg`) redraws `preview.png` from `tiger_cut.png` and the magpies.

Build a small colour-theme pipeline in this repository: Python 3.9 standard library only. No paid calls;
network only for step 5 and for Codex. The parent accepts each generated file by reading it before the next
generator is written. Run all six steps, then stop. The formats are fixed:

1. `gen/palette.py` writes `out/palette.json` as `{"seed": 7, "colors": [...]}`: 8 colours from
   `random.Random(7)`, each `"#%02x%02x%02x" % (r, g, b)` with `r`, `g`, `b` drawn in that order by
   `randrange(256)`.
2. `gen/theme.py` reads `out/palette.json` and writes `out/theme.css`: a `:root` block with `--c1` … `--c8`
   (the palette in order), `--text-light: #ffffff` and `--text-dark: #111111`; then for each `i` in 1–8 the
   rules `.pair-<i>-light { background: var(--c<i>); color: var(--text-light); }` and the same for `dark`.
3. `gen/preview.py` reads `out/theme.css` and writes `out/preview.html` with one element per pair whose
   `data-pair` attribute is the pair name (`pair-1-light` … `pair-8-dark`, 16 in all) and whose class is the
   same name.
4. `tools/contrast.py`: `contrast.py FG BG` prints the WCAG 2.2 contrast ratio with two decimals (`4.54`);
   `contrast.py --css FILE --min X` prints `<pair> <ratio> PASS|FAIL` per pair of the theme and exits 1 if
   any pair fails, else 0; `--selftest` exits 0 when its own checks pass.
5. `docs/wcag.md`: the WCAG 2.2 relative-luminance and contrast-ratio formulas and the thresholds, with
   w3.org links.
6. `docs/contrast.md`: every pair of `out/theme.css` checked against 4.5:1 with the tool from 4, one line per
   pair with its ratio and PASS or FAIL.

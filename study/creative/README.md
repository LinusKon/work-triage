# Creative study tools

Setup once: `cd study/creative && npm install` (Node 24, system Google Chrome, ffmpeg, Python 3).

- `render.mjs`: opens a run's `index.html` headless over `file://` with every non-file request blocked, writes PNGs
  (motion and scene3d: frames at fixed `?t=` values, a repeat frame and `strip.png`; page: full-page and first-viewport
  shots at 1440 and 390) and `render.json` (console and page errors, blocked requests, page measurements, text).
  `node render.mjs motion runs/m1 out/m1`
- `checks.py`: reads `render.json` and the PNGs and applies the briefs' hard requirements. Prints one JSON object and
  writes `checks.json`. A check is `true`, `false` or `"needs_look"`; `pass` means nothing is `false`. For `copy` no
  render is needed.
  `python3 checks.py motion runs/m1 out/m1`
- `rank.html` + `rank_server.py`: blind ranking page on `127.0.0.1` (standard library only). Each screens subfolder has a
  `screen.json` (`id`, `task`, `brief_title`, `items[{label, kind, path, strip}]`, paths relative to that folder).
  Saves `<out>/<screen id>.json`.
  `python3 rank_server.py screens ranks --port 8765`
- `scene3d.seed/vendor/`: three.js 0.187.0 ES module build (`three.module.js` imports `three.core.js`; this version ships
  no `.min.js`) and its `LICENSE`. Import with `./vendor/three.module.js`. Copy `vendor/` into every scene3d run.
- `render.mjs` and `checks.py` also know `sting` (motion task, 7 frames, 4 x 2 strip) and `pricing` (page task, plus a record of the three buttons in the first viewport).
- `make_screens.py ... --tasks a,b` limits the screens to those tasks (default: all found).
- `analyze.py ... --tasks a,b --arms a,b` builds the tables for other task and arm sets; bars whose arms are missing are skipped.
- `judge.sh` and `judge_use.sh` read screens and write judgments to `$WT_SCREENS` and `$WT_JUDGES` when set (defaults `$ROOT/screens`, `$ROOT/judges`).

# Brief: lighthouse at dusk

Build a small 3D scene with three.js: a lighthouse on a rock island at dusk, its beam sweeping across the water.
Low-poly, a little stylised, the kind of scene someone would keep open in a tab. The camera circles the island
slowly. The light should be the hero: the scene is dark enough for the beam to matter.

Hard requirements:
- `index.html` in the repository root, using only the three.js build already in `vendor/` (import it with a
  relative path). No other libraries, no network requests, no model, texture, image or font files: geometry,
  materials and sky are made in code.
- The canvas fills a 1920 × 1080 window without scrollbars.
- The scene is a 12-second loop: the camera completes part of an orbit and the beam completes exactly one full
  turn. Opened as `index.html?t=<seconds>` it shows exactly that instant and stands still; the same `t` always
  gives the same picture. Opened without `t` it loops.
- The lighthouse, the island and the water are in frame at `t=0`, `t=3`, `t=6` and `t=9`, and those four frames
  differ from each other.
- No errors in the browser console.

# Brief: title sequence for "TIDEWATER"

Make the ten-second opening title sequence for a documentary series called TIDEWATER: six films about a harbour
city learning to live with a rising sea. The films are quiet and observational. The sequence should feel like
cold water and slow time, and the idea of a water level rising should be in it somewhere. No glitch effects, no
stock "cinematic" lens flares.

Text, in this order:
1. `A FIELD NOTES ORIGINAL` appears within the first 1.5 seconds and is gone by second 4.
2. `TIDEWATER`, the title, is fully legible from second 4 to second 10.
3. `Six parts. Starting 12 March.` is visible from second 8.5 to second 10.

Hard requirements:
- One file, `index.html`, in the repository root. Everything is inside it: no other files, no network requests,
  no image or font files. System fonts, CSS, SVG and canvas are allowed.
- The stage is 1920 × 1080 CSS pixels and fills a 1920 × 1080 window without scrollbars.
- The sequence is 10 seconds long. Opened as `index.html?t=<seconds>` (for example `?t=4.5`) it shows exactly
  that instant and stands still; the same `t` always gives the same picture. Opened without `t` it plays once
  from 0 to 10 and holds the last frame.
- At `t=10` the title and line 3 are both on screen.
- No errors in the browser console.

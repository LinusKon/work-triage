# Brief: logo sting for Kiln

Make the six-second animated logo sting for Kiln, a small ceramics studio that sells its work online. It plays at
the start of their product films. Think of clay and heat: something is formed, fired, and comes out finished. It
should feel made by hand, warm and a little slow, and end calm. No particle fireworks, no glitch effects.

Text:
1. The wordmark `KILN` forms during the sequence and is complete and fully legible from second 3.5 to second 6.
2. The line `Fired in small batches.` is visible from second 4.5 to second 6.

Hard requirements:
- One file, `index.html`, in the repository root. Everything is inside it: no other files, no network requests,
  no image or font files. System fonts, CSS, SVG and canvas are allowed.
- The stage is 1920 × 1080 CSS pixels and fills a 1920 × 1080 window without scrollbars.
- The sequence is 6 seconds long. Opened as `index.html?t=<seconds>` (for example `?t=2.5`) it shows exactly that
  instant and stands still; the same `t` always gives the same picture. Opened without `t` it plays once from 0 to
  6 and holds the last frame.
- At `t=6` the wordmark and the line are both on screen.
- No errors in the browser console.

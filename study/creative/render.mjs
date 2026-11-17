#!/usr/bin/env node
// Usage: node render.mjs <motion|sting|scene3d|page|pricing> <run folder> <out folder>
import puppeteer from 'puppeteer-core';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const [task, runArg, outArg] = process.argv.slice(2);
if (!['motion', 'sting', 'scene3d', 'page', 'pricing'].includes(task) || !runArg || !outArg) {
  console.error('usage: node render.mjs <motion|sting|scene3d|page|pricing> <run folder> <out folder>');
  process.exit(2);
}
const run = resolve(runArg);
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const indexUrl = pathToFileURL(join(run, 'index.html')).href;

const report = { task, console_errors: [], page_errors: [], blocked_requests: [], missing_index: !existsSync(join(run, 'index.html')) };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: [
    '--no-sandbox',
    '--use-angle=metal',
    '--enable-webgl',
    '--ignore-gpu-blocklist',
    '--enable-unsafe-swiftshader',
    '--hide-scrollbars',
    '--allow-file-access-from-files',
    '--force-device-scale-factor=1',
    '--disable-background-timer-throttling',
  ],
});

async function open(width, height, query = '') {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });
  await page.setRequestInterception(true);
  page.on('request', (req) => {
    const u = req.url();
    if (u.startsWith('file:') || u.startsWith('data:') || u.startsWith('blob:') || u.startsWith('about:')) {
      req.continue();
    } else {
      report.blocked_requests.push(u);
      req.abort('blockedbyclient');
    }
  });
  page.on('console', (m) => {
    if (m.type() === 'error') report.console_errors.push(m.text());
  });
  page.on('pageerror', (e) => report.page_errors.push(String(e && e.message ? e.message : e)));
  try {
    await page.goto(indexUrl + query, { waitUntil: 'load', timeout: 30000 });
  } catch (e) {
    report.page_errors.push('goto failed: ' + e.message);
  }
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  await sleep(150);
  return page;
}

function strip(files, cols, w, name, padTo = 0) {
  const n = Math.max(files.length, padTo);
  const args = ['-y', '-loglevel', 'error'];
  files.forEach((f) => args.push('-i', join(out, f)));
  for (let i = files.length; i < n; i++) args.push('-f', 'lavfi', '-i', `color=black:s=1920x1080,format=rgb24`);
  let fc = Array.from({ length: n }, (_, i) => `[${i}:v]scale=${w}:-2[s${i}]`).join(';');
  const rows = Math.ceil(n / cols);
  for (let r = 0; r < rows; r++) {
    const idx = [];
    for (let i = r * cols; i < Math.min(n, (r + 1) * cols); i++) idx.push(i);
    fc += `;${idx.map((i) => `[s${i}]`).join('')}hstack=inputs=${idx.length}[r${r}]`;
  }
  fc += ';' + Array.from({ length: rows }, (_, r) => `[r${r}]`).join('') + `vstack=inputs=${rows}[o]`;
  args.push('-filter_complex', fc, '-map', '[o]', '-frames:v', '1', join(out, name));
  execFileSync('ffmpeg', args);
}

const visibleText = () => {
  // text of elements with own text, effective opacity > 0, visible, non-zero size
  const res = [];
  const walk = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    let op = 1;
    for (let e = el; e; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
    const r = el.getBoundingClientRect();
    const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).filter(Boolean).join(' ');
    if (own && op > 0 && r.width > 0 && r.height > 0 && !['SCRIPT', 'STYLE', 'TITLE'].includes(el.tagName)) {
      res.push({ text: own, opacity: Math.round(op * 1000) / 1000 });
    }
    for (const c of el.children) walk(c);
  };
  walk(document.body);
  return res;
};

try {
  if (task === 'motion' || task === 'sting' || task === 'scene3d') {
    const isMotion = task === 'motion' || task === 'sting';
    const times = task === 'motion' ? [0.5, 1, 2.5, 4, 5, 6.5, 8, 8.5, 9.5, 10] : task === 'sting' ? [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6] : [0, 3, 6, 9];
    const againT = task === 'motion' ? 4 : task === 'sting' ? 3.5 : 3;
    report.frames = {};
    report.canvas_count = {};
    for (const t of times) {
      const page = await open(1920, 1080, `?t=${t}`);
      await page.screenshot({ path: join(out, `t-${t}.png`) });
      if (isMotion) {
        const vt = await page.evaluate(visibleText);
        report.frames[t] = { visible_text: vt };
      } else {
        report.frames[t] = {};
      }
      const dim = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        canvases: document.querySelectorAll('canvas').length,
      }));
      Object.assign(report.frames[t], dim);
      if (t === againT) {
        await page.close();
        const p2 = await open(1920, 1080, `?t=${t}`);
        await p2.screenshot({ path: join(out, `t-${t}-again.png`) });
        await p2.close();
      } else {
        await page.close();
      }
    }
    report.again_t = againT;
    if (isMotion) {
      report.text_in_canvas = Object.values(report.frames).every((f) => f.visible_text.length === 0);
    }
    const files = times.map((t) => `t-${t}.png`);
    if (task === 'motion') strip(files, 5, 768, 'strip.png');
    else if (task === 'sting') strip(files, 4, 768, 'strip.png', 8);
    else strip(files, 2, 960, 'strip.png');
  } else {
    report.widths = {};
    for (const [w, h] of [[1440, 900], [390, 844]]) {
      const page = await open(w, h);
      await page.screenshot({ path: join(out, `w${w}-fold.png`) });
      await page.screenshot({ path: join(out, `w${w}.png`), fullPage: true });
      const info = await page.evaluate((winW, winH, pricingButtons) => {
        const inView = (b) => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.left >= 0 && r.top >= 0 && r.right <= winW && r.bottom <= winH; };
        const all = [...document.querySelectorAll('a, button')];
        const btns = all.filter((e) => e.textContent.trim() === 'Reserve yours');
        const b = btns[0];
        let button = { found: btns.length };
        if (b) {
          const r = b.getBoundingClientRect();
          button = {
            found: btns.length,
            rect: { x: r.x, y: r.y, w: r.width, h: r.height },
            inside_first_viewport: r.width > 0 && r.height > 0 && r.left >= 0 && r.top >= 0 && r.right <= winW && r.bottom <= winH,
          };
        }
        return {
          scrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
          windowWidth: window.innerWidth,
          windowHeight: window.innerHeight,
          button,
          ...(pricingButtons ? { pricing_buttons: Object.fromEntries(pricingButtons.map((t) => { const m = all.filter((e) => e.textContent.trim() === t); return [t, { found: m.length, inside_first_viewport: m.some(inView) }]; })) } : {}),
          innerText: document.body.innerText,
        };
      }, w, h, task === 'pricing' ? ['Start free', 'Try Team for 14 days', 'Talk to us'] : null);
      report.widths[w] = info;
      await page.close();
    }
    report.innerText_1440 = report.widths[1440].innerText;
  }
} finally {
  await browser.close();
}
writeFileSync(join(out, 'render.json'), JSON.stringify(report, null, 2));
console.log(`render ${task}: ${report.console_errors.length} console errors, ${report.page_errors.length} page errors, ${report.blocked_requests.length} blocked requests`);

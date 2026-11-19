#!/usr/bin/env python3
"""Draw the study's charts in the film's look as dark PNGs at 2x.

    charts_lightbox.py <data dir> <out dir> --fonts <dir> [--skill SKILL.md] [--chrome <binary>]

Standard library plus headless Chrome. Each chart is written as one HTML page with an inline SVG (from the CSV
files only; nothing but labels is typed in by hand), rendered by Chrome at device scale 2 and cropped to its
content. `--fonts` names a folder with JetBrainsMono-VF.ttf and Anybody-VF.ttf (SIL OFL); they are read at render
time and not shipped. The routing picture reads the skill's version from SKILL.md and checks every routing rule it
draws against that file.
"""
import argparse
import csv
import html
import os
import re
import statistics
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

W = 880  # CSS px; rendered at 2x, so every PNG is 1760 px wide for an 880 px README column
NIGHT = "#070708"
RED = "#FF2D20"
CREAM = "#F3DCAE"
POSTER = "#EFE9DC"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MONO_W = 0.6  # JetBrains Mono advance per em

# Materials: front gradient (top, bottom), top face, side face, edge stroke, glow.
MATS = {
    "red": ("#FF4234", "#B8180E", "#FF7366", "#7A0F08", "#FF8C82", True),
    "dimred": ("#8E1A12", "#55100A", "#A8261C", "#3A0905", "#C2392E", False),
    "cream": ("#EBD5A9", "#BFA67C", "#FAEACB", "#8A7A5E", "#FFF4DC", False),
    "grey": ("#4C4C53", "#2C2C31", "#6E6E76", "#202024", "#8A8A92", False),
    "white": ("#E4E4E7", "#A9A9AE", "#F6F6F7", "#77777C", "#FFFFFF", False),
}


def esc(s):
    return html.escape(str(s), quote=True)


def text_w(s, size, spacing=0.04):
    """Width of a mono string in px (JetBrains Mono: 0.6 em per glyph plus letter spacing)."""
    return len(str(s)) * size * (MONO_W + spacing)


def money(v):
    return "$%.2f" % v


def pct(v, digits=0):
    """Signed percent with a real minus sign."""
    return (("%+." + str(digits) + "f %%") % (100 * v)).replace("-", "−")


class Chart:
    def __init__(self, title, key=None):
        self.parts, self.objs, self.floor = [], [], None  # objs: lit things, mirrored in the floor if one is set
        self.text(40, 40, title, 13, 1.0)
        if key:
            self.key(40, 60, key)

    # -- primitives ---------------------------------------------------------------------------------------
    def add(self, s, obj=False):
        self.parts.append(s)
        if obj:
            self.objs.append(s)

    def text(self, x, y, s, size=12, op=1.0, anchor="start", color="#FFFFFF", upper=False, spacing=0.04):
        s = str(s).upper() if upper else str(s)
        self.add('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" fill-opacity="%.2f" text-anchor="%s" '
                 'letter-spacing="%.2fem">%s</text>' % (x, y, size, color, op, anchor, spacing, esc(s)))

    def key(self, x, y, items, size=10.5):
        """A line of coloured words, no box: [(text, colour or None)]."""
        for s, color in items:
            self.text(x, y, s, size, 1.0 if color else 0.62, color=color or "#FFFFFF", upper=True)
            x += text_w(s, size)

    def line(self, x1, y1, x2, y2, op=0.34, width=0.8, dash=None, color="#FFFFFF"):
        self.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-opacity="%.2f" '
                 'stroke-width="%s"%s/>' % (x1, y1, x2, y2, color, op, width,
                                           ' stroke-dasharray="%s"' % dash if dash else ""))

    def poster(self, x, y, s, size, color=POSTER, anchor="start"):
        self.add('<text class="poster" x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s">%s</text>'
                 % (x, y, size, color, anchor, esc(s)))

    def label(self, x, y, lines, anchor="end", point=None):
        """Small mono label: first line white, then 62 % (upper case), then 34 %; optional hairline leader."""
        sizes = ((12, 1.0, False), (10, 0.62, True), (10.5, 0.34, False))
        for i, s in enumerate(lines):
            size, op, upper = sizes[min(i, 2)]
            self.text(x, y + i * 14.5, s, size, op, anchor, upper=upper)
        if point:
            lx = x + 8 if anchor == "end" else x - 8
            self.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#FFFFFF" stroke-opacity="0.34" '
                     'stroke-width="0.8"/>' % (lx, y - 4, point[0], point[1]))
            self.add('<circle cx="%.1f" cy="%.1f" r="1.8" fill="#FFFFFF" fill-opacity="0.8"/>' % point)

    def ground(self, floor):
        """The floor line; lit objects are mirrored in it."""
        self.floor = floor
        self.line(40, floor + 0.5, W - 40, floor + 0.5, 0.18)

    def source(self, y, s):
        self.text(40, y, s, 10, 0.34)

    def light(self, x, y, mat, r=2.6):
        color = {"red": RED, "cream": CREAM, "dimred": "#A8261C"}.get(mat, "#FFFFFF")
        filt = ' filter="url(#glow)"' if mat == "red" else ""
        self.add('<circle cx="%.1f" cy="%.1f" r="%s" fill="%s"%s/>' % (x, y, r, color, filt), True)

    def slab(self, x, y, w, h, d, mat):
        """A box seen slightly from above: front face (x, y, w, h), top and right faces d deep."""
        dx, dy = d * 0.62, d * 0.42
        top = "%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x, y, x + w, y, x + w + dx, y - dy, x + dx, y - dy)
        side = "%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x + w, y, x + w + dx, y - dy, x + w + dx, y + h - dy,
                                                             x + w, y + h)
        if mat in ("wire", "dash", "wirered", "wirecream"):
            stroke, sop = {"wire": ("#FFFFFF", 0.34), "dash": ("#FFFFFF", 0.5), "wirered": (RED, 0.75),
                           "wirecream": (CREAM, 0.7)}[mat]
            dash = ' stroke-dasharray="3 3"' if mat == "dash" else ""
            g = ('<g fill="none" stroke="%s" stroke-opacity="%.2f" stroke-width="0.9"%s>'
                 '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/><polygon points="%s"/><polygon points="%s"/></g>'
                 % (stroke, sop, dash, x, y, w, h, top, side))
            self.add(g)
            return
        f1, f2, ft, fs, edge, glow = MATS[mat]
        gid = "g%s" % mat
        g = ('<g%s><polygon points="%s" fill="%s"/><polygon points="%s" fill="%s"/>'
             '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="url(#%s)"/>'
             '<g fill="none" stroke="%s" stroke-opacity="0.55" stroke-width="0.7">'
             '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/><polygon points="%s"/></g></g>'
             % (' filter="url(#glow)"' if glow else ' filter="url(#grain)"', side, fs, top, ft,
                x, y, w, max(h, 0.5), gid, edge, x, y, w, max(h, 0.5), top))
        self.add(g, True)

    def stack(self, x, floor, w, d, value, unit, scale, mat, gap=2.0):
        """A column of slabs, one per `unit` of value; returns the y of its top face."""
        n_full = int(value // unit)
        rest = value - n_full * unit
        pieces = [unit] * n_full + ([rest] if rest * scale >= 1.5 else [])
        y = floor
        for v in pieces:
            h = v * scale - gap
            y -= v * scale
            self.slab(x, y + gap, w, max(h, 1.0), d, mat)
        return y + gap

    # -- page ---------------------------------------------------------------------------------------------
    def html(self, fonts):
        grads = "".join('<linearGradient id="g%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
                        '<stop offset="1" stop-color="%s"/></linearGradient>' % (k, v[0], v[1])
                        for k, v in MATS.items())
        defs = (
            '<defs>%s'
            '<filter id="glow" x="-60%%" y="-60%%" width="220%%" height="220%%">'
            '<feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="1" seed="7" result="n"/>'
            '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  .9 .9 .9 0 -1.62" result="d"/>'
            '<feComposite in="d" in2="SourceGraphic" operator="in" result="dg"/>'
            '<feMerge result="s"><feMergeNode in="SourceGraphic"/><feMergeNode in="dg"/></feMerge>'
            '<feGaussianBlur in="SourceGraphic" stdDeviation="7" result="b"/>'
            '<feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 .18 0 0 0  0 0 .12 0 0  0 0 0 .55 0" result="bg"/>'
            '<feMerge><feMergeNode in="bg"/><feMergeNode in="s"/></feMerge></filter>'
            '<filter id="grain" x="0" y="0" width="100%%" height="100%%">'
            '<feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="1" seed="3" result="n"/>'
            '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  .9 .9 .9 0 -1.62" result="d"/>'
            '<feComposite in="d" in2="SourceGraphic" operator="in" result="dg"/>'
            '<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="dg"/></feMerge></filter>'
            '%s</defs>' % (grads, self.fade()))
        mono = Path(fonts, "JetBrainsMono-VF.ttf").resolve().as_uri()
        poster = Path(fonts, "Anybody-VF.ttf").resolve().as_uri()
        return """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:JBM;src:url("%s") format("truetype");font-weight:100 800;font-display:block}
@font-face{font-family:ANY;src:url("%s") format("truetype");font-weight:100 900;font-stretch:50%% 150%%;font-display:block}
html,body{margin:0;background:%s;overflow:hidden}
svg{display:block;font-family:JBM;font-weight:400}
text{white-space:pre}
.poster{font-family:ANY;font-weight:800;font-stretch:55%%;letter-spacing:-0.01em}
</style></head><body><svg id="c" xmlns="http://www.w3.org/2000/svg" width="%d" height="2000" viewBox="0 0 %d 2000">%s%s</svg>
<script>
document.fonts.load('12px JBM').then(()=>document.fonts.load('800 40px ANY')).then(()=>document.fonts.ready).then(()=>{
  const svg=document.getElementById('c'), p=document.querySelector('.poster');
  if(p){const pb=p.getBBox(); document.querySelectorAll('.ap').forEach(g=>g.setAttribute('transform','translate('+(pb.x+pb.width+30)+',0)'));}
  const r=document.getElementById('refl'); if(r) r.style.display='none';
  const b=svg.getBBox(); const pad=28;
  if(r) r.style.display='';
  const top=Math.floor(b.y-pad), h=Math.ceil(b.y+b.height+pad)-top;
  svg.setAttribute('viewBox','0 '+top+' %d '+h); svg.setAttribute('height',h);
  document.body.dataset.h=h;
});
</script></body></html>""" % (mono, poster, NIGHT, W, W, defs, self.reflection() + "".join(self.parts), W)

    def fade(self):
        if self.floor is None:
            return ""
        return ('<linearGradient id="fadeg" gradientUnits="userSpaceOnUse" x1="0" y1="%.1f" x2="0" y2="%.1f">'
                '<stop offset="0" stop-color="#fff" stop-opacity="0.16"/><stop offset="1" stop-color="#fff" '
                'stop-opacity="0"/></linearGradient><mask id="fade" maskUnits="userSpaceOnUse" x="0" y="%.1f" '
                'width="%d" height="40"><rect x="0" y="%.1f" width="%d" height="40" fill="url(#fadeg)"/></mask>'
                % (self.floor, self.floor + 40, self.floor, W, self.floor, W))

    def reflection(self):
        """The lit objects mirrored in the floor, fading out within 40 px."""
        if self.floor is None:
            return ""
        return ('<g id="refl" mask="url(#fade)"><g transform="translate(0 %.1f) scale(1 -1)">%s</g></g>'
                % (2 * self.floor, "".join(self.objs)))


# -- data ------------------------------------------------------------------------------------------------------
def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick(rows, **want):
    return [r for r in rows if all(str(r[k]) == str(v) for k, v in want.items())]


def usd(rows, field="total_usd"):
    return [float(r[field]) for r in rows]


def base_for(runs, rnd, tasks):
    """Baseline runs (Opus high, no skill) for a round; round 2 reused round 1's runs for A, B and D."""
    b = [r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "base"]
    if rnd == 2:
        b += [r for r in runs if r["round"] == "1" and r["task"] in "ABD" and r["arm"] == "base"]
    return b


def need(rows, what):
    if not rows:
        sys.exit("charts_lightbox: no rows for %s" % what)
    return rows


# -- charts ----------------------------------------------------------------------------------------------------
def evidence(runs):
    """Per setup: median without and with the skill as two stacks, every run as a light, the change."""
    setups = (("5", "H", "base", "skill25", "build H · omp 18.21.0", "20 plug-in operations"),
              ("6", "I", "base", "skill26", "build I · omp 18.21.0", "layered task tracker"),
              ("7", "I", "base22", "skill261v22", "build I · omp 18.22.0", "codex named in prompt"),
              ("7", "I", "base22nc", "skill261nc", "build I · omp 18.22.0", "claude only"))
    rows = []
    for rnd, task, b_arm, s_arm, title, sub in setups:
        b = usd(need(pick(runs, round=rnd, task=task, arm=b_arm), b_arm))
        k = usd(need(pick(runs, round=rnd, task=task, arm=s_arm), s_arm))
        rows.append((title, sub, b, k, statistics.median(b), statistics.median(k)))
    changes = [mk / mb - 1 for _, _, _, _, mb, mk in rows]
    saved = [round(mb, 2) - round(mk, 2) for _, _, _, _, mb, mk in rows]  # as the medians are shown
    c = Chart("Large Python builds in omp · median per build",
              [("red", RED), (" = no skill, opus 5.5 high   ", None), ("cream", CREAM),
               (" = work-triage   one slab = $1   one light = one run", None)])
    lo, hi = max(changes), min(changes)
    c.poster(36, 168, "%s to %s" % (pct(lo).replace(" %", ""), pct(hi)), 92)
    c.add('<g class="ap">')
    c.label(0, 134, ["%s to %s per build" % (money(min(saved)), money(max(saved))),
                     "saved at the median, five runs per setup"], "start")
    c.add('</g>')
    floor, scale = 540, 34.0
    for i, (title, sub, b, k, mb, mk) in enumerate(rows):
        gx = 40 + i * 205
        for j, (vals, med, mat) in enumerate(((b, mb, "red"), (k, mk, "cream"))):
            x = gx + 34 + j * 74
            top = c.stack(x, floor, 40, 18, med, 1.0, scale, mat)
            c.text(x + 26, top - 16, money(med), 12, 1.0, "middle")
            lx = x - 10 if j == 0 else x + 40 + 11.2 + 10
            for v in vals:
                c.light(lx, floor - v * scale, mat, 3.0)
        c.text(gx + 34 + 71, floor + 30, pct(changes[i]), 15, 1.0, "middle")
        c.text(gx + 34 + 71, floor + 50, title, 10.5, 0.62, "middle", upper=False)
        c.text(gx + 34 + 71, floor + 65, sub, 10, 0.34, "middle")
    c.ground(floor)
    c.source(floor + 100, "source: study/data/runs.csv, rounds %s. claude dollars plus codex at api list prices."
             % ", ".join(sorted({s[0] for s in setups})))
    return c


def cost_large_builds(runs, builds):
    """Every run of the two large builds as its own stack, sorted, the median named."""
    c = Chart("Large builds: every run, with and without the skill",
              [("red", RED), (" = no skill   ", None), ("cream", CREAM),
               (" = work-triage   one stack = one complete build   one slab = $1", None)])
    floor, scale = 470, 38.0
    for i, (rnd, task, s_arm, title, sub) in enumerate(builds):
        meds = []
        for j, (arm, mat, name) in enumerate((("base", "red", "no skill"), (s_arm, "cream", sub))):
            vals = sorted(usd(need(pick(runs, round=rnd, task=task, arm=arm), arm)))
            gx = 52 + i * 420 + j * 190
            med = statistics.median(vals)
            meds.append(med)
            for k, v in enumerate(vals):
                x = gx + k * 30
                c.stack(x, floor, 20, 12, v, 1.0, scale, mat)
                if k == len(vals) // 2:  # the median of five: mark it under the floor
                    c.line(x + 10, floor + 6, x + 10, floor + 14, 0.62, 1.0)
            c.text(gx, floor + 34, name, 11, 1.0)
            c.text(gx, floor + 50, "median %s · n = %d" % (money(med), len(vals)), 10, 0.62)
            c.text(gx, floor + 65, "%s to %s" % (money(vals[0]), money(vals[-1])), 10, 0.34)
        c.text(52 + i * 420, 112, title, 12, 1.0)
        c.text(52 + i * 420 + 340, 112, pct(meds[1] / meds[0] - 1), 15, 1.0, "end")
    c.ground(floor)
    c.source(floor + 98, "source: study/data/runs.csv, rounds %s. the tick under a stack marks the median run. "
             "baseline: opus 5.5 high." % " and ".join(b[0] for b in builds))
    return c


def journey(runs, steps):
    """Median cost of the skill against no skill, version by version: wire box = no skill, stack = the skill."""
    vals = []
    for rnd, tasks, arm, label, sub in steps:
        b = usd(need(base_for(runs, rnd, tasks), "base round %s" % rnd))
        k = usd(need([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm], arm))
        vals.append((label, sub, statistics.median(k) / statistics.median(b)))
    c = Chart("Version by version: the skill's median cost against no skill",
              [("wire box", None), (" = no skill on the same tasks   ", None), ("cream", CREAM),
               (" = the skill up to that height   ", None), ("red", RED), (" = what it cost on top", None)])
    c.poster(36, 168, "%s to %s" % (pct(vals[0][2] - 1).replace(" %", ""), pct(vals[-1][2] - 1)), 76)
    unit = 150.0
    floor = 236 + unit * max(v for _, _, v in vals)
    for i, (label, sub, v) in enumerate(vals):
        x = 70 + i * 200
        w, d = 70, 22
        lower = min(v, 1.0)
        c.slab(x, floor - lower * unit, w, lower * unit, d, "cream")
        if v > 1:
            c.slab(x, floor - v * unit, w, (v - 1) * unit - 2, d, "red")
        c.slab(x, floor - unit, w, unit, d, "wire")
        top = floor - max(v, 1.0) * unit - d * 0.42
        c.text(x + w / 2 + 6, top - 14, pct(v - 1), 15, 1.0, "middle")
        c.text(x, floor + 28, "skill " + label, 11, 1.0)
        c.text(x, floor + 44, sub, 10, 0.34)
    c.ground(floor)
    c.source(floor + 80, "source: study/data/runs.csv, rounds %s. round 3 changed the main session's level too; "
             "it is in the small-tasks chart." % ", ".join(str(s[0]) for s in steps))
    return c


def small_tasks(runs):
    """Small tasks: median total per round for no skill, the skill, and no skill at a medium main session."""
    groups = ((1, "ABCD", "skill21", "round 1 · skill 2.1", "tasks a to d"),
              (2, "ABCD", "skill22", "round 2 · skill 2.2", "tasks a to d"),
              (3, "EFG", "skill23", "round 3 · skill 2.3", "tasks e to g, main session at medium"))
    c = Chart("Small tasks: the skill saves nothing",
              [("red", RED), (" = no skill, opus high   ", None), ("dark red", "#C2392E"),
               (" = no skill, opus medium   ", None), ("cream", CREAM), (" = work-triage   one slab = $0.10", None)])
    data = []
    for rnd, tasks, arm, label, sub in groups:
        b = usd(need(base_for(runs, rnd, tasks), "base"))
        k = usd(need([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm], arm))
        m = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "basemed"])
        cols = [(statistics.median(b), "red", len(b)), (statistics.median(k), "cream", len(k))]
        if m:
            cols.append((statistics.median(m), "dimred", len(m)))
        data.append((label, sub, cols))
    scale = 250.0
    floor = 130 + scale * max(v for _, _, cols in data for v, _, _ in cols)
    for i, (label, sub, cols) in enumerate(data):
        gx = 60 + i * 275
        for j, (v, mat, n) in enumerate(cols):
            x = gx + j * 64
            top = c.stack(x, floor, 38, 16, v, 0.10, scale, mat, gap=2.5)
            c.text(x + 24, top - 16, money(v), 12, 1.0, "middle")
            c.text(x + 24, floor + 18, "n=%d" % n, 9.5, 0.34, "middle")
        c.text(gx, floor + 44, label, 11, 1.0)
        c.text(gx, floor + 60, sub, 10, 0.34)
    c.ground(floor)
    c.source(floor + 94, "source: study/data/runs.csv, rounds 1 to 3, median total cost per run. "
             "lowering the main session to medium saved more.")
    return c


def cost_split(runs, builds):
    """Mean cost per run as one slab per kind of session, thickness = dollars."""
    parts = (("main session", "red"), ("opus subagents", "dimred"), ("sonnet workers", "cream"), ("codex", "grey"))
    c = Chart("Where the money goes: mean cost per run, by who did the work",
              [("red", RED), (" = main session, opus high   ", None), ("dark red", "#C2392E"),
               (" = opus subagents   ", None), ("cream", CREAM), (" = sonnet workers   ", None),
               ("grey", "#8A8A92"), (" = codex", None)], )
    stacks = []
    for rnd, task, s_arm, title, sub in builds:
        for arm, name in (("base", "no skill"), (s_arm, sub)):
            g = need(pick(runs, round=rnd, task=task, arm=arm), arm)
            n = len(g)
            head = sum(usd(g, "parent_usd")) / n
            vals = (head, sum(usd(g, "opus_usd")) / n - head, sum(usd(g, "sonnet_usd")) / n,
                    sum(usd(g, "codex_usd")) / n)
            stacks.append((title, name, n, vals))
    scale = 300 / max(sum(v) for *_, v in stacks)
    floor = 470
    xs = (190, 360, 540, 710)
    for i, (title, name, n, vals) in enumerate(stacks):
        x, w, d = xs[i], 66, 26
        y = floor
        marks = []
        for (pname, mat), v in zip(parts, vals):
            h = v * scale
            if h < 1:
                continue
            y -= h
            c.slab(x, y + 3, w, h - 3, d, mat)
            marks.append((pname, v, y + 3 + (h - 3) / 2))
        c.text(x + w / 2 + 8, y - 24, money(sum(vals)), 15, 1.0, "middle")
        # value labels on the right, pushed apart so thin slabs stay readable
        ys = [m[2] + 4 for m in marks]
        for k in range(1, len(ys)):
            ys[k] = min(ys[k], ys[k - 1] - 15)
        for (pname, v, my), ly in zip(marks, ys):
            c.label(x + w + 30, ly, [money(v)], "start", point=(x + w + 1, my))
            if i == 0:  # name the parts once, on the left of the first stack
                c.label(x - 26, ly, [pname], "end", point=(x - 1, my))
        c.text(x, floor + 26, name, 11, 1.0)
        c.text(x, floor + 42, "%s · %d runs" % (title.split(" · ")[0], n), 10, 0.34)
    c.ground(floor)
    c.source(floor + 76, "source: study/data/runs.csv, rounds %s. codex at api list prices."
             % " and ".join(b[0] for b in builds))
    return c


def defects_chart(defects, builds):
    """Major defects per run after blind, uniform grading: one cube per defect."""
    c = Chart("Quality: major defects per build, graded blind",
              [("red", RED), (" = no skill   ", None), ("cream", CREAM),
               (" = work-triage   one cube = one major defect, python 3.12", None)])
    floor, cube = 300, 13
    for i, (rnd, task, s_arm, title, sub) in enumerate(builds):
        for j, (arm, mat, name) in enumerate((("base", "red", "no skill"), (s_arm, "cream", sub))):
            vals = [int(r["major"]) for r in need([r for r in defects if r["task"] == task and r["arm"] == arm], arm)]
            gx = 52 + i * 420 + j * 190
            for k, v in enumerate(vals):
                x = gx + k * 30
                for n in range(v):
                    c.slab(x, floor - (n + 1) * (cube + 4) + 4, cube + 4, cube, 10, mat)
                c.text(x + 10, floor + 18, v, 10, 0.34, "middle")
            c.text(gx, floor + 42, name, 11, 1.0)
            c.text(gx, floor + 58, "%d in %d builds" % (sum(vals), len(vals)), 10, 0.62)
        c.text(52 + i * 420, 112, title, 12, 1.0)
    c.ground(floor)
    c.source(floor + 92, "source: study/data/defects.csv. most kinds are strict readings of the spec that both arms share.")
    return c


def creative_chart(creative):
    """Design built in code: usable outputs of 15 and the cost per usable output, per model."""
    setups = (("sonnet-high", "sonnet 5.5 · high", "cream"), ("opus-medium", "opus 5.5 · medium", "dimred"),
              ("opus-high", "opus 5.5 · high", "red"), ("fable-high", "fable 5.2 · high", "white"))
    rows = [r for r in creative if r["brief"] != "copy"]
    briefs = sorted({r["brief"] for r in rows})
    c = Chart("Design built in code: when is a cheaper model enough?",
              [("%d briefs, %d runs each   lit cube = usable, both model judges would hand it over"
                % (len(briefs), len([r for r in rows if r["setup"] == setups[0][0]]) // len(briefs)), None)])
    c.text(300, 108, "usable, of %d runs" % len([r for r in rows if r["setup"] == setups[0][0]]), 10, 0.34)
    c.text(W - 40, 108, "$ per usable output", 10, 0.34, "end")
    for i, (key, label, mat) in enumerate(setups):
        mine = need([r for r in rows if r["setup"] == key], key)
        ok = [r for r in mine if r["use_opus"] in ("yes", "fix") and r["use_astra"] in ("yes", "fix")]
        per = sum(usd(mine)) / len(ok)
        y = 150 + i * 52
        c.text(40, y + 4, label, 12, 1.0)
        for k in range(len(mine)):
            x = 300 + k * 22
            c.slab(x, y - 8, 14, 14, 9, mat if k < len(ok) else "wire")
        c.text(300 + len(mine) * 22 + 14, y + 4, "%d" % len(ok), 13, 1.0)
        c.text(W - 40, y + 4, money(per), 15, 1.0, "end")
    c.source(150 + 4 * 52 + 20, "source: study/data/creative.csv. judged blind by opus 5.5 high and gpt-6-astra high; "
             "no person judged.")
    return c


ROUTING_RULES = (
    # (label lines, material, slab height, text that must appear in SKILL.md)
    (("main session", "opus 5.5 · high", "plans, integrates, never lowered"), "red", 40,
     "Opus 5.5\n`high` is the default"),
    (("spec'd modules, tests, docs", "wt-worker · sonnet 5.5 medium", "measured on two builds"), "cream", 14,
     "`wt-worker` (Sonnet 5.5 `medium`)"),
    (("dense edge cases, design in code", "wt-worker-hard · sonnet 5.5 high", "builds and six creative briefs"),
     "cream", 14, "`wt-worker-hard` (Sonnet 5.5 `high`)"),
    (("copy, image and video prompts", "per call · opus 5.5 medium", "rule, not measured"), "dimred", 10,
     "Other taste work (copy, prompts for image and video models): Opus 5.5 `medium`"),
    (("security, secrets, open interface", "floor · opus 5.5 high", "rule: never cheaper"), "red", 14,
     "Security (auth"),
    (("one review of the merged result", "wt-reviewer · opus 5.5 high", "measured on two builds"), "red", 20,
     "`wt-reviewer` (Opus 5.5 `high`)"),
)
LADDER = (("wt-worker", "wirecream"), ("wt-worker-hard", "wirecream"), ("opus 5.5 · high", "wirered"),
          ("opus 5.5 · xhigh", "wirered"), ("fable 5.2", "dash"))


def routing(skill_path):
    """Who gets what: the main session on top, the rows below it as slabs, Codex beside, the ladder up."""
    text = Path(skill_path).read_text(encoding="utf-8")
    flat = " ".join(text.split())
    version = re.search(r"^\s*version:\s*([\d.]+)", text, re.MULTILINE)
    if not version:
        sys.exit("charts_lightbox: no version in %s" % skill_path)
    checks = [r[3] for r in ROUTING_RULES] + ["`wt-worker` → `wt-worker-hard` → Opus `high` → `xhigh`",
                                              "Security stops at Opus `xhigh`, then the user"]
    for check in checks:
        if " ".join(check.split()) not in flat:
            sys.exit("charts_lightbox: SKILL.md no longer says %r; update the routing picture" % check)
    c = Chart("Who gets what in a large build", [("work that fits one session stays there", None)])
    x0, w, d = 352, 150, 30
    y = 140
    for lines, mat, h, _ in ROUTING_RULES:
        c.slab(x0, y, w, h, d, mat)
        c.label(318, y + h / 2 - 10, lines, "end", point=(x0 - 1, y + h / 2))
        y += h + 46
    bottom = y - 46
    # Codex: a grey slab beside the stack
    cx, cy = 560, bottom - 40
    c.slab(cx, cy, 70, 12, 22, "grey")
    tx = cx + 70 + 34
    c.label(tx, cy - 6, ["codex, optional", "model and level always named"], "start", point=(cx + 71, cy + 6))
    c.text(tx, cy + 23, "sol: spec'd modules", 10.5, 0.62)
    c.text(tx, cy + 37.5, "terra: local app checks", 10.5, 0.62)
    c.text(tx, cy + 52, "a codex review only on request", 10.5, 0.34)
    # the ladder: wire outlines going up to an empty dashed fable 5.2
    lx, lw, step = 570, 50, 34
    base = 140 + 210
    c.text(lx - 10, 112, "when a check fails twice,", 10, 0.62, upper=True)
    c.text(lx - 10, 126, "the work moves one step up", 10, 0.62, upper=True)
    for k, (name, mat) in enumerate(LADDER):
        yy = base - k * step
        c.slab(lx, yy, lw, 10, 14, mat)
        c.text(lx + lw + 26, yy + 9, name, 11, 1.0 if mat != "dash" else 0.62)
        if k:
            c.line(lx + lw / 2 + 4, yy + step - 14, lx + lw / 2 + 4, yy + 12, 0.34, 0.8)
    c.text(lx - 10, base + 34, "security stops at opus xhigh,", 10, 0.34)
    c.text(lx - 10, base + 48, "then the user decides", 10, 0.34)
    c.source(bottom + 46, "source: skills/work-triage/SKILL.md, version %s." % version.group(1))
    return c


# -- render ----------------------------------------------------------------------------------------------------
def render(chart, name, out, fonts, chrome, tmp):
    page = Path(tmp, name + ".html")
    page.write_text(chart.html(fonts), encoding="utf-8")
    url = page.resolve().as_uri()
    common = [chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
              "--virtual-time-budget=4000"]
    dom = subprocess.run(common + ["--dump-dom", url], capture_output=True, text=True, check=True).stdout
    m = re.search(r'data-h="(\d+)"', dom)
    if not m:
        sys.exit("charts_lightbox: %s did not lay out (fonts missing?)" % name)
    h = int(m.group(1))
    png = Path(out, name + ".png")
    subprocess.run(common + ["--force-device-scale-factor=2", "--window-size=%d,%d" % (W, h),
                             "--screenshot=%s" % png, url], capture_output=True, check=True)
    with open(png, "rb") as f:
        size = struct.unpack(">II", f.read(24)[16:24])
    if size != (2 * W, 2 * h):
        sys.exit("charts_lightbox: %s rendered at %s, expected %s" % (png, size, (2 * W, 2 * h)))
    print("%-24s %d x %d  %4d kB" % (png.name, size[0], size[1], png.stat().st_size // 1024))


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("data")
    ap.add_argument("out")
    ap.add_argument("--fonts", required=True, help="folder with JetBrainsMono-VF.ttf and Anybody-VF.ttf")
    ap.add_argument("--skill", help="SKILL.md of work-triage (default: found next to this study)")
    ap.add_argument("--chrome", default=CHROME)
    ap.add_argument("--only", help="comma-separated chart names")
    a = ap.parse_args()
    skill = a.skill or next((p for p in (here.parent / "skills/work-triage/SKILL.md",
                                         here.parent / "skills/dev/work-triage/SKILL.md") if p.exists()), None)
    if not skill:
        sys.exit("charts_lightbox: pass --skill")
    runs = load(os.path.join(a.data, "runs.csv"))
    defects = load(os.path.join(a.data, "defects.csv"))
    creative = load(os.path.join(a.data, "creative.csv"))
    builds = (("5", "H", "skill25", "build H · dataops", "skill 2.5"),
              ("6", "I", "skill26", "build I · tasktrack", "skill 2.6"))
    steps = ((1, "ABCD", "skill21", "2.1", "small tasks"), (2, "ABCD", "skill22", "2.2", "small tasks"),
             (5, "H", "skill25", "2.5", "large build H"), (6, "I", "skill26", "2.6", "large build I"))
    charts = {
        "evidence": lambda: evidence(runs),
        "routing": lambda: routing(skill),
        "journey": lambda: journey(runs, steps),
        "small-tasks": lambda: small_tasks(runs),
        "cost-split": lambda: cost_split(runs, builds),
        "defects": lambda: defects_chart(defects, builds),
        "creative": lambda: creative_chart(creative),
        "cost-large-builds": lambda: cost_large_builds(runs, builds),
    }
    names = a.only.split(",") if a.only else list(charts)
    os.makedirs(a.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            render(charts[name](), name, a.out, a.fonts, a.chrome, tmp)


if __name__ == "__main__":
    main()

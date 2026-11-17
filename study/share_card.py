#!/usr/bin/env python3
"""Draw the share card (1600 x 900) from runs.csv: share_card.py <data dir> <out dir>.

Writes `share-card-light.svg` and `share-card-dark.svg` without a background for the README, and
`share-card-post.svg` with a solid dark background; `render_share_png.sh` turns that one into the PNG for posts
and the repository's social preview. Standard library only; every number comes from the CSV.
"""
import os
import statistics
import sys

from charts import FONT, MONO, THEMES, load, pick, usd

W, H = 1600, 900
BUILDS = (("5", "H", "skill25", "Build H · 20 plug-in operations"),
          ("6", "I", "skill26", "Build I · layered task tracker"))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;")


def text(x, y, s, size, fill, weight="400", anchor="start", mono=False, spacing=None):
    extra = ' font-family="%s"' % MONO if mono else ""
    if spacing:
        extra += ' letter-spacing="%s"' % spacing
    return ('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" font-weight="%s" text-anchor="%s"%s>%s</text>'
            % (x, y, size, fill, weight, anchor, extra, esc(s)))


def card(runs, theme, path, background=None):
    t = THEMES[theme]
    p = []
    if background:
        p.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, background))
    p.append('<rect x="80" y="84" width="22" height="22" rx="5" fill="%s"/>' % t["skill"])
    p.append(text(116, 104, "work-triage", 28, t["fg"], "650", mono=True))
    p.append(text(1520, 104, "a skill for omp and Claude Code", 24, t["muted"], anchor="end"))
    p.append(text(78, 226, "Large agent builds,", 84, t["fg"], "750", spacing="-1.5"))
    p.append(text(78, 322, "about a third cheaper.", 84, t["skill"], "750", spacing="-1.5"))
    n = len(runs) - len([r for r in runs if r.get("note", "").startswith("control run")])
    p.append(text(80, 384, "Same model in charge. Same hidden tests passed. %d measured runs." % n, 30, t["muted"]))

    top, ch, gap = 440, 330, 40
    cw = (W - 160 - gap) / 2
    hi = max(usd([r for rnd, task, arm, _ in BUILDS for a in ("base", arm) for r in pick(runs, round=rnd, task=task, arm=a)]))
    for i, (rnd, task, arm, title) in enumerate(BUILDS):
        x0 = 80 + (cw + gap) * i
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="22" fill="%s" stroke="%s" stroke-width="2"/>'
                 % (x0, top, cw, ch, t["card"], t["grid"]))
        base = sorted(usd(pick(runs, round=rnd, task=task, arm="base")))
        skill = sorted(usd(pick(runs, round=rnd, task=task, arm=arm)))
        mb, ms = statistics.median(base), statistics.median(skill)
        p.append(text(x0 + 36, top + 54, title, 26, t["muted"], "500"))
        p.append(text(x0 + 34, top + 172, "\u2212%d %%" % round((1 - ms / mb) * 100), 124, t["skill"], "750", spacing="-3"))
        p.append(text(x0 + cw - 36, top + 122, "$%.2f" % mb, 40, t["base"], "600", "end"))
        p.append(text(x0 + cw - 36, top + 172, "\u2192 $%.2f" % ms, 40, t["fg"], "700", "end"))
        ax0, ax1 = x0 + 150, x0 + cw - 40
        sx = lambda v: ax0 + (ax1 - ax0) * v / (hi * 1.04)
        for row, (vals, med, color, label) in enumerate(((base, mb, t["base"], "no skill"), (skill, ms, t["skill"], "with skill"))):
            y = top + 232 + row * 48
            p.append(text(x0 + 36, y + 8, label, 22, t["muted"]))
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (ax0, y, ax1, y, t["grid"]))
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5" stroke-linecap="round"/>'
                     % (sx(med), y - 17, sx(med), y + 17, color))
            for v in vals:
                p.append('<circle cx="%.1f" cy="%.1f" r="10" fill="%s" fill-opacity="0.85" stroke="%s" stroke-width="2.5"/>'
                         % (sx(v), y, color, t["card"]))
    p.append(text(80, 842, "Each dot is one complete build. The bar is the median.", 24, t["faint"]))
    p.append(text(1520, 842, "github.com/LinusKon/work-triage", 26, t["fg"], "600", "end", mono=True))
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s" '
                'role="img">\n%s\n</svg>\n' % (W, H, W, H, FONT, "\n".join(p)))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    runs = load(os.path.join(sys.argv[1], "runs.csv"))
    out = sys.argv[2]
    for theme in ("light", "dark"):
        card(runs, theme, os.path.join(out, "share-card-%s.svg" % theme))
    card(runs, "dark", os.path.join(out, "share-card-post.svg"), background="#0d1117")
    print("3 files -> %s" % out)


if __name__ == "__main__":
    main()

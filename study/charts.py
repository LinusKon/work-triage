#!/usr/bin/env python3
"""Draw the study's charts as SVG from runs.csv and defects.csv: charts.py <data dir> <out dir>.

Standard library only. Every chart is written twice, `<name>-light.svg` and `<name>-dark.svg`, for GitHub's
light and dark themes. Numbers come from the CSV files only; nothing is typed in by hand.
"""
import csv
import os
import statistics
import sys

THEMES = {
    "light": {"fg": "#1f2328", "muted": "#59636e", "grid": "#d1d9e0", "base": "#8c959f", "skill": "#8250df",
              "sonnet": "#1a7f37", "codex": "#bf8700", "bad": "#cf222e"},
    "dark": {"fg": "#f0f6fc", "muted": "#9198a1", "grid": "#3d444d", "base": "#768390", "skill": "#ab7df8",
             "sonnet": "#3fb950", "codex": "#d29922", "bad": "#f85149"},
}
FONT = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


class Svg:
    def __init__(self, w, h, theme):
        self.w, self.h, self.t, self.parts = w, h, THEMES[theme], []

    def text(self, x, y, s, size=13, color="fg", anchor="start", weight="400"):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;")
        self.parts.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="%s" font-weight="%s">%s</text>'
                          % (x, y, size, self.t.get(color, color), anchor, weight, s))

    def line(self, x1, y1, x2, y2, color="grid", width=1, dash=None):
        self.parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>'
                          % (x1, y1, x2, y2, self.t.get(color, color), width,
                             ' stroke-dasharray="%s"' % dash if dash else ""))

    def rect(self, x, y, w, h, color, opacity=1.0, rx=3):
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" fill-opacity="%.2f"/>'
                          % (x, y, max(w, 0), max(h, 0), rx, self.t.get(color, color), opacity))

    def dot(self, x, y, color, r=6):
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" fill-opacity="0.85"/>'
                          % (x, y, r, self.t.get(color, color)))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
                    'font-family="%s" role="img">\n%s\n</svg>\n' % (self.w, self.h, self.w, self.h, FONT,
                                                                   "\n".join(self.parts)))


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick(rows, **want):
    return [r for r in rows if all(str(r[k]) == str(v) for k, v in want.items())]


def usd(rows, field="total_usd"):
    return [float(r[field]) for r in rows]


def strip_chart(runs, builds, theme, path):
    """One panel per large build: every run as a dot, medians as lines, the change between the medians."""
    pw, h, left, top, bottom = 400, 400, 70, 112, 60
    s = Svg(left + pw * len(builds) + 20, h, theme)
    s.text(left, 30, "Total cost per run on large builds", 18, weight="600")
    s.text(left, 52, "Each dot is one complete build. Claude dollars plus Codex at API list prices.", 13, "muted")
    top_usd = max(usd([r for r in runs if (r["round"], r["task"]) in {(b[0], b[1]) for b in builds}])) * 1.12
    y = lambda v: top + (h - top - bottom) * (1 - v / top_usd)
    for tick in range(0, int(top_usd) + 1):
        s.line(left, y(tick), s.w - 20, y(tick))
        s.text(left - 10, y(tick) + 4, "$%d" % tick, 12, "muted", "end")
    for i, (rnd, task, skill_arm, title) in enumerate(builds):
        x0 = left + pw * i
        meds = {}
        for j, (arm, color, label) in enumerate((("base", "base", "Opus 5.5 high, no skill"),
                                                 (skill_arm, "skill", "with work-triage"))):
            vals = sorted(usd(pick(runs, round=rnd, task=task, arm=arm)))
            cx = x0 + pw * (0.3 + 0.4 * j)
            for k, v in enumerate(vals):
                s.dot(cx + (k - (len(vals) - 1) / 2) * 15, y(v), color)
            meds[arm] = statistics.median(vals)
            s.line(cx - 62, y(meds[arm]), cx + 62, y(meds[arm]), color, 2.5)
            s.text(cx + 68, y(meds[arm]) + 4, "$%.2f" % meds[arm], 12, color, "start", "600")
            s.text(cx, h - bottom + 22, label, 12, "muted", "middle")
            s.text(cx, h - bottom + 38, "n = %d" % len(vals), 11, "muted", "middle")
        change = meds[skill_arm] / meds["base"] - 1
        s.text(x0 + pw / 2, top - 30, title, 13, "fg", "middle", "600")
        s.text(x0 + pw / 2, top - 8, "%+.0f %% median" % (100 * change), 16, "skill", "middle", "700")
    s.save(path)


def journey_chart(runs, steps, theme, path):
    """Median total cost of the skill relative to the no-skill baseline, version by version."""
    w, h, left, top, bottom = 820, 360, 70, 80, 78
    s = Svg(w, h, theme)
    s.text(left, 52, "Median total cost of the skill against Opus 5.5 high without it, same tasks, per round.", 13,
           "muted")
    vals = []
    for rnd, tasks, arm, label, sub in steps:
        b = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "base"
                 and r["head_level"] == "high"])
        k = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm])
        if rnd == 2:  # round 2 reused round 1's base runs for A, B, D
            b += usd([r for r in runs if r["round"] == "1" and r["task"] in "ABD" and r["arm"] == "base"])
        vals.append((label, sub, statistics.median(k) / statistics.median(b) - 1))
    s.text(left, 30, "The skill against no skill, version by version: from %+.0f %% to %+.0f %%"
           % (100 * vals[0][2], 100 * vals[-1][2]), 18, weight="600")
    lo, hi = min(v for _, _, v in vals + [("", "", -0.5)]), max(v for _, _, v in vals + [("", "", 0.9)])
    y = lambda v: top + (h - top - bottom) * (hi - v) / (hi - lo)
    for tick in (-0.5, -0.25, 0, 0.25, 0.5, 0.75):
        s.line(left, y(tick), w - 20, y(tick), "fg" if tick == 0 else "grid", 1.2 if tick == 0 else 1)
        s.text(left - 10, y(tick) + 4, "%+d %%" % (100 * tick), 12, "muted", "end")
    bw = (w - left - 40) / len(vals)
    for i, (label, sub, v) in enumerate(vals):
        x = left + 10 + bw * i
        color = "skill" if v < 0 else "base"
        s.rect(x + bw * 0.2, min(y(v), y(0)), bw * 0.6, abs(y(v) - y(0)), color, 0.9)
        s.text(x + bw / 2, (y(v) - 8) if v >= 0 else (y(v) + 18), "%+.0f %%" % (100 * v), 14, color, "middle", "700")
        s.text(x + bw / 2, h - bottom + 24, label, 13, "fg", "middle", "600")
        s.text(x + bw / 2, h - bottom + 42, sub, 11, "muted", "middle")
    s.save(path)


def split_chart(runs, builds, theme, path):
    """Mean cost per run split into head session, Opus subagents, Sonnet subagents and Codex."""
    w, h, left, top = 820, 96 + 62 * 2 * len(builds), 200, 84
    s = Svg(w, h, theme)
    s.text(24, 30, "Where the money goes", 18, weight="600")
    s.text(24, 52, "Mean cost per run, by who did the work. Codex at API list prices.", 13, "muted")
    parts = (("head session (Opus high)", "base"), ("Opus subagents", "skill"), ("Sonnet subagents", "sonnet"),
             ("Codex (list price)", "codex"))
    rows_ = []
    for rnd, task, skill_arm, title in builds:
        for arm, label in (("base", "no skill"), (skill_arm, "work-triage")):
            g = pick(runs, round=rnd, task=task, arm=arm)
            n = len(g)
            head = sum(usd(g, "parent_usd")) / n
            sonnet = sum(usd(g, "sonnet_usd")) / n
            opus_sub = sum(usd(g, "opus_usd")) / n - head
            codex = sum(usd(g, "codex_usd")) / n
            rows_.append(("%s · %s" % (title.split(" · ")[0], label), (head, opus_sub, sonnet, codex)))
    scale = (w - left - 80) / max(sum(v) for _, v in rows_)
    for i, (label, vals) in enumerate(rows_):
        yy = top + 62 * i
        s.text(left - 12, yy + 22, label, 12, "fg", "end")
        x = left
        for (name, color), v in zip(parts, vals):
            s.rect(x, yy + 4, v * scale, 28, color, 0.9)
            if v * scale > 44:
                s.text(x + v * scale / 2, yy + 23, "$%.2f" % v, 11, "#ffffff", "middle", "600")
            x += v * scale
        s.text(x + 8, yy + 23, "$%.2f" % sum(vals), 13, "fg", "start", "700")
    x = left
    for name, color in parts:
        s.rect(x, h - 26, 12, 12, color, 0.9)
        s.text(x + 18, h - 15, name, 11, "muted")
        x += 34 + 6.2 * len(name)
    s.save(path)


def defect_chart(defects, builds, theme, path):
    """Major defects per run after blind, uniform grading."""
    pw, h, left, top, bottom = 400, 300, 60, 84, 50
    s = Svg(left + pw * len(builds) + 20, h, theme)
    s.text(left, 30, "Quality: major defects per build, graded blind", 18, weight="600")
    s.text(left, 52, "One rubric, one executable probe per defect, run on every build of both arms.", 13, "muted")
    top_n = max(int(r["major"]) for r in defects) + 1
    y = lambda v: top + (h - top - bottom) * (1 - v / top_n)
    for tick in range(0, top_n + 1, 2):
        s.line(left, y(tick), s.w - 20, y(tick))
        s.text(left - 10, y(tick) + 4, tick, 12, "muted", "end")
    for i, (rnd, task, skill_arm, title) in enumerate(builds):
        x0 = left + pw * i
        s.text(x0 + pw / 2, top - 10, title, 13, "fg", "middle", "600")
        for j, (arm, color, label) in enumerate((("base", "base", "no skill"), (skill_arm, "skill", "work-triage"))):
            vals = [int(r["major"]) for r in defects if r["task"] == task and r["arm"] == arm]
            bw = 22
            cx = x0 + pw * (0.28 + 0.44 * j)
            for k, v in enumerate(vals):
                bx = cx + (k - len(vals) / 2) * (bw + 4)
                s.rect(bx, y(v), bw, y(0) - y(v), color, 0.9)
                s.text(bx + bw / 2, y(v) - 5, v, 11, "muted", "middle")
            s.text(cx, h - bottom + 20, "%s · sum %d" % (label, sum(vals)), 12, "muted", "middle")
    s.save(path)


def small_chart(runs, theme, path):
    """Small tasks: median total per round for no skill, the skill, and (round 3) no skill at a medium head."""
    groups = [(1, "ABCD", "skill21", "round 1 · skill 2.1"), (2, "ABCD", "skill22", "round 2 · skill 2.2"),
              (3, "EFG", "skill23", "round 3 · skill 2.3 at a medium head")]
    w, h, left, top, bottom = 820, 330, 70, 96, 56
    s = Svg(w, h, theme)
    s.text(left, 30, "Small tasks: the skill saves nothing", 18, weight="600")
    s.text(left, 52, "Work that fits one session, median total cost per run. Lowering the head to Opus medium", 13,
           "muted")
    s.text(left, 70, "saved more than the skill did, so the skill now only says: do it alone.", 13, "muted")
    data = []
    for rnd, tasks, arm, label in groups:
        b = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "base"])
        if rnd == 2:
            b += usd([r for r in runs if r["round"] == "1" and r["task"] in "ABD" and r["arm"] == "base"])
        k = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm])
        m = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "basemed"])
        bars = [(statistics.median(b), "base"), (statistics.median(k), "skill")]
        if m:
            bars.append((statistics.median(m), "sonnet"))
        data.append((label, bars))
    top_usd = max(v for _, bars in data for v, _ in bars) * 1.25
    y = lambda v: top + (h - top - bottom) * (1 - v / top_usd)
    for tick in (0, 0.5, 1.0, 1.5):
        if tick <= top_usd:
            s.line(left, y(tick), w - 20, y(tick))
            s.text(left - 10, y(tick) + 4, "$%.2f" % tick, 12, "muted", "end")
    gw = (w - left - 40) / len(data)
    for i, (label, bars) in enumerate(data):
        x = left + 20 + gw * i
        bw = gw * 0.22
        for j, (v, color) in enumerate(bars):
            bx = x + gw * 0.5 + (j - len(bars) / 2) * (bw + 6)
            s.rect(bx, y(v), bw, y(0) - y(v), color, 0.9)
            s.text(bx + bw / 2, y(v) - 6, "$%.2f" % v, 12, color, "middle", "600")
        s.text(x + gw * 0.5, h - bottom + 22, label, 12, "fg", "middle", "600")
    x = left
    for name, color in (("no skill, Opus high", "base"), ("work-triage", "skill"), ("no skill, Opus medium", "sonnet")):
        s.rect(x, h - 22, 12, 12, color, 0.9)
        s.text(x + 18, h - 11, name, 11, "muted")
        x += 40 + 6.2 * len(name)
    s.save(path)


def main():
    data, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    runs = load(os.path.join(data, "runs.csv"))
    defects = load(os.path.join(data, "defects.csv")) if os.path.exists(os.path.join(data, "defects.csv")) else []
    builds = [b for b in (("5", "H", "skill25", "Build H · dataops · skill 2.5"),
                          ("6", "I", "skill26", "Build I · tasktrack · skill 2.6"))
              if pick(runs, round=b[0], task=b[1], arm=b[2])]
    # Round 3 changed the head level together with the skill; it is shown in the small-tasks chart with its
    # medium-head baseline instead of here.
    steps = [s for s in ((1, "ABCD", "skill21", "2.1", "small tasks"), (2, "ABCD", "skill22", "2.2", "small tasks"),
                         (5, "H", "skill25", "2.5", "large build H"), (6, "I", "skill26", "2.6", "large build I"))
             if [r for r in runs if r["round"] == str(s[0]) and r["arm"] == s[2]]]
    for theme in THEMES:
        strip_chart(runs, builds, theme, os.path.join(out, "cost-large-builds-%s.svg" % theme))
        journey_chart(runs, steps, theme, os.path.join(out, "journey-%s.svg" % theme))
        split_chart(runs, builds, theme, os.path.join(out, "cost-split-%s.svg" % theme))
        small_chart(runs, theme, os.path.join(out, "small-tasks-%s.svg" % theme))
        if defects:
            defect_chart(defects, builds, theme, os.path.join(out, "defects-%s.svg" % theme))
    print("charts ->", out)


if __name__ == "__main__":
    main()

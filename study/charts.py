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
    "light": {"fg": "#1f2328", "muted": "#59636e", "faint": "#818b98", "grid": "#d1d9e0", "card": "#f6f8fa",
              "base": "#8c959f", "skill": "#8250df", "sonnet": "#1a7f37", "codex": "#bf8700", "on": "#ffffff"},
    "dark": {"fg": "#f0f6fc", "muted": "#9198a1", "faint": "#6e7681", "grid": "#30363d", "card": "#151b23",
             "base": "#768390", "skill": "#ab7df8", "sonnet": "#3fb950", "codex": "#d29922", "on": "#0d1117"},
}
FONT = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
W = 880  # every chart has the same width, so they line up in the README


class Svg:
    def __init__(self, h, theme, title, subtitle):
        self.w, self.h, self.t, self.parts = W, h, THEMES[theme], []
        self.text(28, 38, title, 20, weight="650")
        self.text(28, 62, subtitle, 13.5, "muted")

    def c(self, name):
        return self.t.get(name, name)

    def text(self, x, y, s, size=13, color="fg", anchor="start", weight="400", mono=False):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;")
        fam = ' font-family="%s"' % MONO if mono else ""
        self.parts.append('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s" font-weight="%s"%s>%s</text>'
                          % (x, y, size, self.c(color), anchor, weight, fam, s))

    def line(self, x1, y1, x2, y2, color="grid", width=1.0, dash=None, cap="butt"):
        self.parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" '
                          'stroke-linecap="%s"%s/>' % (x1, y1, x2, y2, self.c(color), width, cap,
                                                      ' stroke-dasharray="%s"' % dash if dash else ""))

    def rect(self, x, y, w, h, color, opacity=1.0, rx=4, stroke=None):
        extra = ' stroke="%s" stroke-width="1"' % self.c(stroke) if stroke else ""
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" fill="%s" fill-opacity="%.2f"%s/>'
                          % (x, y, max(w, 0), max(h, 0), rx, self.c(color), opacity, extra))

    def card(self, x, y, w, h):
        self.rect(x, y, w, h, "card", 1.0, 10, "grid")

    def dot(self, x, y, color, r=7):
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="%s" fill="%s" stroke="%s" stroke-width="2"/>'
                          % (x, y, r, self.c(color), self.c("card")))

    def pill(self, x, y, s, color, anchor="middle", size=12.5):
        w = 7.4 * len(s) * size / 12.5 + 16
        x0 = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
        self.rect(x0, y - 15, w, 22, color, 1.0, 11)
        self.text(x0 + w / 2, y, s, size, "on", "middle", "650")

    def legend(self, x, y, items):
        for name, color in items:
            self.rect(x, y - 10, 12, 12, color, 1.0, 3)
            self.text(x + 18, y, name, 12, "muted")
            x += 34 + 6.6 * len(name)

    def note(self, s):
        self.text(28, self.h - 14, s, 11, "faint")

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


def base_for(runs, rnd, tasks):
    """Baseline runs (Opus high, no skill) for a round; round 2 reused round 1's runs for A, B and D."""
    b = [r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "base"]
    if rnd == 2:
        b += [r for r in runs if r["round"] == "1" and r["task"] in "ABD" and r["arm"] == "base"]
    return b


def pct(v):
    """Signed whole percent with a real minus sign."""
    return ("%+.0f %%" % (100 * v)).replace("-", "−")


def strip_chart(runs, builds, theme, path):
    """One card per large build: every run as a dot, medians as lines, the change between the medians."""
    s = Svg(470, theme, "Large builds: every run, with and without the skill",
            "Total cost of one complete build. Claude dollars plus Codex at API list prices.")
    gap, top, bottom = 20, 86, 40
    cw = (W - 56 - gap * (len(builds) - 1)) / len(builds)
    ymax = max(usd([r for r in runs if (r["round"], r["task"]) in {(b[0], b[1]) for b in builds}])) * 1.08
    plot_top, plot_bot = top + 78, 470 - bottom - 58
    y = lambda v: plot_bot - (plot_bot - plot_top) * v / ymax
    for i, (rnd, task, skill_arm, title, sub) in enumerate(builds):
        x0 = 28 + (cw + gap) * i
        s.card(x0, top, cw, 470 - top - bottom)
        s.text(x0 + 20, top + 30, title, 15, weight="650")
        s.text(x0 + 20, top + 50, sub, 12.5, "muted")
        for tick in range(0, int(ymax) + 1, 2):
            s.line(x0 + 54, y(tick), x0 + cw - 18, y(tick))
            s.text(x0 + 46, y(tick) + 4, "$%d" % tick, 11.5, "faint", "end")
        meds = {}
        for j, (arm, color, label) in enumerate((("base", "base", "no skill"), (skill_arm, "skill", "work-triage"))):
            vals = sorted(usd(pick(runs, round=rnd, task=task, arm=arm)))
            cx = x0 + 54 + (cw - 72) * (0.27 + 0.46 * j)
            meds[arm] = statistics.median(vals)
            s.line(cx - 64, y(meds[arm]), cx + 64, y(meds[arm]), color, 3, cap="round")
            for k, v in enumerate(vals):
                s.dot(cx + (k - (len(vals) - 1) / 2) * 19, y(v), color)
            s.text(cx, plot_bot + 26, label, 13, "fg", "middle", "600")
            s.text(cx, plot_bot + 44, "median $%.2f · n = %d" % (meds[arm], len(vals)), 12, "muted", "middle")
        change = meds[skill_arm] / meds["base"] - 1
        s.pill(x0 + cw - 20, top + 34, pct(change), "skill", "end", 15)
    s.note("Source: study/data/runs.csv, rounds 5 and 6. Baseline: Opus 5.5 high in omp, free to spawn or use Codex.")
    s.save(path)


def journey_chart(runs, steps, theme, path):
    """Median total cost of the skill relative to the no-skill baseline, version by version."""
    vals = []
    for rnd, tasks, arm, label, sub, group in steps:
        b = usd(base_for(runs, rnd, tasks))
        k = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm])
        vals.append((label, sub, group, statistics.median(k) / statistics.median(b) - 1))
    s = Svg(400, theme, "Version by version: from %s to %s" % (pct(vals[0][3]), pct(vals[-1][3])),
            "Median total cost of the skill against the same model without it, on the same tasks.")
    left, top, bottom = 84, 96, 92
    lo, hi = min(-0.5, min(v[3] for v in vals)) - 0.2, max(0.5, max(v[3] for v in vals) + 0.14)
    y = lambda v: top + (400 - top - bottom) * (hi - v) / (hi - lo)
    s.card(28, top - 18, W - 56, 400 - top - bottom + 78)
    for tick in (-0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0):
        if lo <= tick <= hi:
            s.line(left, y(tick), W - 46, y(tick), "muted" if tick == 0 else "grid", 1.4 if tick == 0 else 1)
            s.text(left - 10, y(tick) + 4, pct(tick) if tick else "no skill", 11.5, "faint", "end")
    bw = (W - left - 60) / len(vals)
    for i, (label, sub, group, v) in enumerate(vals):
        x = left + 8 + bw * i
        color = "skill" if v < 0 else "base"
        s.rect(x + bw * 0.22, min(y(v), y(0)), bw * 0.56, abs(y(v) - y(0)), color, 1.0, 5)
        s.text(x + bw / 2, (y(v) - 9) if v >= 0 else (y(v) + 20), pct(v), 15, color, "middle", "700")
        s.text(x + bw / 2, 400 - bottom + 26, "skill " + label, 13, "fg", "middle", "600")
        s.text(x + bw / 2, 400 - bottom + 44, sub, 12, "muted", "middle")
    s.note("Source: study/data/runs.csv. Round 3 changed the head level together with the skill and is shown with the small tasks.")
    s.save(path)


def split_chart(runs, builds, theme, path):
    """Mean cost per run split into head session, Opus subagents, Sonnet subagents and Codex."""
    rows_ = []
    for rnd, task, skill_arm, title, sub in builds:
        for arm, label in (("base", "no skill"), (skill_arm, "work-triage")):
            g = pick(runs, round=rnd, task=task, arm=arm)
            n = len(g)
            head = sum(usd(g, "parent_usd")) / n
            sonnet = sum(usd(g, "sonnet_usd")) / n
            opus_sub = sum(usd(g, "opus_usd")) / n - head
            codex = sum(usd(g, "codex_usd")) / n
            rows_.append((title.split(" · ")[0], label, (head, opus_sub, sonnet, codex)))
    h = 172 + 54 * len(rows_) + 16 * (len(builds) - 1)
    s = Svg(h, theme, "Where the money goes", "Mean cost per run, by who did the work.")
    parts = (("main session, Opus high", "base"), ("Opus subagents", "skill"), ("Sonnet workers", "sonnet"),
             ("Codex, list price", "codex"))
    s.card(28, 84, W - 56, h - 84 - 36)
    s.legend(52, 112, parts)
    left = 206
    scale = (W - left - 120) / max(sum(v) for _, _, v in rows_)
    yy = 132
    for i, (build, label, vals) in enumerate(rows_):
        if i and i % 2 == 0:
            yy += 16
        if i % 2 == 0:
            s.text(52, yy + 23, build, 13, "fg", weight="650")
        s.text(left - 14, yy + 23, label, 12.5, "muted", "end")
        x = left
        for (name, color), v in zip(parts, vals):
            if v * scale >= 1:
                s.rect(x, yy + 5, v * scale - 2, 28, color, 1.0, 4)
            if v * scale > 46:
                s.text(x + v * scale / 2 - 1, yy + 24, "$%.2f" % v, 11.5, "on", "middle", "650")
            x += v * scale
        s.text(x + 8, yy + 24, "$%.2f" % sum(vals), 14, "fg", "start", "700")
        yy += 54
    s.note("Source: study/data/runs.csv, rounds 5 and 6, five runs per bar.")
    s.save(path)


def defect_chart(defects, builds, theme, path):
    """Major defects per run after blind, uniform grading: one square per defect."""
    s = Svg(360, theme, "Quality: major defects per build, graded blind",
            "One rubric and one executable probe per defect, run on every build of both arms. One square is one defect.")
    gap, top, bottom = 20, 86, 40
    cw = (W - 56 - gap * (len(builds) - 1)) / len(builds)
    sq, base_y = 15, 360 - bottom - 62
    for i, (rnd, task, skill_arm, title, sub) in enumerate(builds):
        x0 = 28 + (cw + gap) * i
        s.card(x0, top, cw, 360 - top - bottom)
        s.text(x0 + 20, top + 30, title, 15, weight="650")
        for j, (arm, color, label) in enumerate((("base", "base", "no skill"), (skill_arm, "skill", "work-triage"))):
            vals = [int(r["major"]) for r in defects if r["task"] == task and r["arm"] == arm]
            cx = x0 + cw * (0.27 + 0.46 * j)
            for k, v in enumerate(vals):
                bx = cx + (k - len(vals) / 2) * (sq + 9)
                for n in range(v):
                    s.rect(bx, base_y - (n + 1) * (sq + 3), sq, sq, color, 1.0, 3)
                s.text(bx + sq / 2, base_y + 15, v, 11.5, "faint", "middle")
            s.line(cx - 70, base_y, cx + 70, base_y, "grid")
            s.text(cx, base_y + 38, label, 13, "fg", "middle", "600")
            s.text(cx, base_y + 55, "%d in 5 builds" % sum(vals), 12, "muted", "middle")
    s.note("Source: study/data/defects.csv (Python 3.12). Most kinds are strict readings of the spec that both arms share.")
    s.save(path)


def small_chart(runs, theme, path):
    """Small tasks: median total per round for no skill, the skill, and (round 3) no skill at a medium head."""
    groups = [(1, "ABCD", "skill21", "Round 1", "skill 2.1"), (2, "ABCD", "skill22", "Round 2", "skill 2.2"),
              (3, "EFG", "skill23", "Round 3", "skill 2.3, head at medium")]
    s = Svg(400, theme, "Small tasks: the skill saves nothing",
            "Work that fits one session, median total cost per run. Lowering the head to Opus medium saved more.")
    data = []
    for rnd, tasks, arm, label, sub in groups:
        b = usd(base_for(runs, rnd, tasks))
        k = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == arm])
        m = usd([r for r in runs if r["round"] == str(rnd) and r["task"] in tasks and r["arm"] == "basemed"])
        bars = [(statistics.median(b), "base"), (statistics.median(k), "skill")]
        if m:
            bars.append((statistics.median(m), "sonnet"))
        data.append((label, sub, bars))
    left, top, bottom = 84, 126, 92
    s.card(28, 84, W - 56, 400 - 84 - 36)
    s.legend(52, 112, (("no skill, Opus high", "base"), ("work-triage", "skill"), ("no skill, Opus medium", "sonnet")))
    top_usd = max(v for _, _, bars in data for v, _ in bars) * 1.22
    y = lambda v: 400 - bottom - (400 - top - bottom) * v / top_usd
    for tick in (0, 0.5, 1.0, 1.5):
        if tick <= top_usd:
            s.line(left, y(tick), W - 46, y(tick))
            s.text(left - 10, y(tick) + 4, "$%.2f" % tick, 11.5, "faint", "end")
    gw = (W - left - 60) / len(data)
    for i, (label, sub, bars) in enumerate(data):
        x = left + 8 + gw * i
        bw = 54
        for j, (v, color) in enumerate(bars):
            bx = x + gw * 0.5 + (j - len(bars) / 2) * (bw + 8)
            s.rect(bx, y(v), bw, y(0) - y(v), color, 1.0, 5)
            s.text(bx + bw / 2, y(v) - 7, "$%.2f" % v, 12.5, color, "middle", "650")
        s.text(x + gw * 0.5, 400 - bottom + 24, label, 13, "fg", "middle", "600")
        s.text(x + gw * 0.5, 400 - bottom + 42, sub, 12, "muted", "middle")
    s.note("Source: study/data/runs.csv, rounds 1 to 3, nine to twelve runs per bar.")
    s.save(path)


def routing_chart(theme, path):
    """Who gets which work in skill 2.7: the main session, the rows, Codex, and the ladder upward."""
    h = 700  # main card, six rows of 52, ladder card, source line
    s = Svg(h, theme, "Who gets what", "Work that fits one session stays there. Larger work is split like this.")
    s.card(28, 84, W - 56, 92)
    s.text(52, 116, "Main session", 15, weight="650")
    s.pill(52 + 118, 112, "Opus 5.5 · high", "skill", "start", 12)
    s.text(52, 146, "Plans, writes the shared contract, integrates, runs the whole suite once. Never lowered.", 13, "muted")
    s.line(W / 2, 176, W / 2, 196, "grid", 2)
    rows = (
        ("Spec'd modules, tests, docs", "wt-worker", "Sonnet 5.5 · medium", "sonnet", "measured on two builds"),
        ("Dense edge cases, design built in code", "wt-worker-hard", "Sonnet 5.5 · high", "sonnet",
         "builds and six creative briefs"),
        ("Copy, image and video prompts", "per call", "Opus 5.5 · medium", "base", "rule, not measured"),
        ("Security, secrets, an open interface", "floor", "Opus 5.5 · high", "skill", "never cheaper"),
        ("One review of the merged result", "wt-reviewer", "Opus 5.5 · high", "skill", "measured on two builds"),
        ("Codex, when you work with it", "model named", "sol: modules · terra: app checks", "codex",
         "a Codex review only on request"),
    )
    top, rh = 196, 52
    s.card(28, top, W - 56, rh * len(rows) + 16)
    for i, (work, who, model, color, note) in enumerate(rows):
        y = top + 34 + i * rh
        if i:
            s.line(48, y - 26, W - 48, y - 26, "grid", 1)
        s.text(52, y, work, 13.5, weight="600")
        s.text(52, y + 17, note, 11.5, "faint")
        s.text(470, y + 4, who, 12.5, "muted", mono=True)
        s.pill(W - 52, y, model, color, "end", 12)
    ly = top + rh * len(rows) + 16 + 24
    s.card(28, ly, W - 56, 104)
    s.text(52, ly + 30, "When a check fails twice, the work moves one step up", 14, weight="650")
    steps = ("wt-worker", "wt-worker-hard", "Opus high", "Opus xhigh", "Fable 5.2")
    sw = (W - 104) / len(steps)
    for i, name in enumerate(steps):
        x = 52 + sw * i
        s.rect(x, ly + 50, sw - 22, 34, "card", 1.0, 8, "grid")
        s.text(x + (sw - 22) / 2, ly + 72, name, 12.5, "fg", "middle", "600", mono=True)
        if i < len(steps) - 1:
            s.text(x + sw - 11, ly + 72, "→", 15, "faint", "middle")
    s.note("Source: skills/work-triage/SKILL.md, version 2.7.0. Security stops at Opus xhigh, then the user decides.")
    s.save(path)


def creative_chart(creative, theme, path):
    """Design built in code: usable outputs of 15 and cost per usable output, per model (two model judges)."""
    setups = (("sonnet-high", "Sonnet 5.5 · high", "sonnet"), ("opus-medium", "Opus 5.5 · medium", "base"),
              ("opus-high", "Opus 5.5 · high", "skill"), ("fable-high", "Fable 5.2 · high", "codex"))
    rows = [r for r in creative if r["brief"] != "copy"]
    h = 330
    s = Svg(h, theme, "Design built in code: when is a cheaper model enough?",
            "Five briefs, three runs each. Usable = both model judges would hand it to a client.")
    s.card(28, 84, W - 56, h - 84 - 40)
    s.text(52, 116, "usable outputs of 15", 12, "muted")
    s.text(W - 52, 116, "$ per usable output", 12, "muted", "end")
    for i, (key, label, color) in enumerate(setups):
        mine = [r for r in rows if r["setup"] == key]
        ok = [r for r in mine if r["use_opus"] in ("yes", "fix") and r["use_astra"] in ("yes", "fix")]
        per = sum(float(r["total_usd"]) for r in mine) / len(ok) if ok else 0
        y = 150 + i * 38
        s.text(52, y + 5, label, 13.5, weight="600")
        for k in range(len(mine)):
            s.rect(240 + k * 22, y - 9, 16, 16, color if k < len(ok) else "grid", 1.0 if k < len(ok) else 0.6, 3)
        s.text(240 + len(mine) * 22 + 10, y + 5, "%d" % len(ok), 13, color, "start", "650")
        s.text(W - 52, y + 5, "$%.2f" % per, 14, "fg", "end", "650", mono=True)
    s.note("Source: study/data/creative.csv. Judged by Opus 5.5 high and gpt-6-astra high, blind; no person judged.")
    s.save(path)


def main():
    data, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    runs = load(os.path.join(data, "runs.csv"))
    defects = load(os.path.join(data, "defects.csv")) if os.path.exists(os.path.join(data, "defects.csv")) else []
    creative = load(os.path.join(data, "creative.csv")) if os.path.exists(os.path.join(data, "creative.csv")) else []
    builds = [b for b in (("5", "H", "skill25", "Build H · dataops", "20 plug-in operations · skill 2.5"),
                          ("6", "I", "skill26", "Build I · tasktrack", "layered task tracker · skill 2.6"))
              if pick(runs, round=b[0], task=b[1], arm=b[2])]
    # Round 3 changed the head level together with the skill; it is shown in the small-tasks chart with its
    # medium-head baseline instead of in the journey.
    steps = [s for s in ((1, "ABCD", "skill21", "2.1", "small tasks", "small"),
                         (2, "ABCD", "skill22", "2.2", "small tasks", "small"),
                         (5, "H", "skill25", "2.5", "large build H", "large"),
                         (6, "I", "skill26", "2.6", "large build I", "large"))
             if [r for r in runs if r["round"] == str(s[0]) and r["arm"] == s[2]]]
    for theme in THEMES:
        strip_chart(runs, builds, theme, os.path.join(out, "cost-large-builds-%s.svg" % theme))
        journey_chart(runs, steps, theme, os.path.join(out, "journey-%s.svg" % theme))
        split_chart(runs, builds, theme, os.path.join(out, "cost-split-%s.svg" % theme))
        small_chart(runs, theme, os.path.join(out, "small-tasks-%s.svg" % theme))
        if defects:
            defect_chart(defects, builds, theme, os.path.join(out, "defects-%s.svg" % theme))
        routing_chart(theme, os.path.join(out, "routing-%s.svg" % theme))
        if creative:
            creative_chart(creative, theme, os.path.join(out, "creative-%s.svg" % theme))
    print("charts ->", out)


if __name__ == "__main__":
    main()

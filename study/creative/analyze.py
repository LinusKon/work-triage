#!/usr/bin/env python3
"""Part A analysis: analyze.py <runs folder> <key file> <ranks folder of the reference judge> [<other judge folder> ...] [--tasks a,b] [--arms a,b]

Prints, from the files only: objective checks and cost per arm and task, mean rank per arm and task from the
reference judge, the plan's bars (sign tests against sonnet-high, split against opus-high, opus-medium against
opus-high), and each other judge's agreement with the reference (Kendall's tau-b per screen, averaged).
Standard library only.
"""
import glob
import itertools
import json
import math
import os
import statistics
import sys

ARMS = ("sonnet-high", "opus-medium", "opus-high", "fable-high", "split")
TASKS = ("motion", "page", "scene3d", "copy")


def load_ranks(folder, key):
    """{screen id: {arm: rank}} for every saved screen that is in the key."""
    out = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        labels = key["screens"].get(d.get("id"))
        if labels:
            out[d["id"]] = {labels[lab]: float(r) for lab, r in d["ranks"].items() if lab in labels}
    return out


def binom_tail(k, n):
    """P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def tau_b(a, b):
    """Kendall's tau-b between two {item: rank} dicts over their shared items; None when undefined."""
    items = sorted(set(a) & set(b))
    conc = disc = ta = tb = 0
    for x, y in itertools.combinations(items, 2):
        da, db = a[x] - a[y], b[x] - b[y]
        if da == 0 and db == 0:
            continue
        if da == 0:
            ta += 1
        elif db == 0:
            tb += 1
        elif da * db > 0:
            conc += 1
        else:
            disc += 1
    den = math.sqrt((conc + disc + ta) * (conc + disc + tb))
    return (conc - disc) / den if den else None


def versus(ranks, a, b, screens=None):
    """(a better, b better, ties) over screens where both arms are ranked."""
    w = l = t = 0
    for sid, r in ranks.items():
        if screens is not None and sid not in screens:
            continue
        if a in r and b in r:
            if r[a] < r[b]:
                w += 1
            elif r[a] > r[b]:
                l += 1
            else:
                t += 1
    return w, l, t


def main():
    global TASKS, ARMS
    argv = sys.argv[1:]
    for opt in ("--tasks", "--arms"):
        if opt in argv:
            i = argv.index(opt)
            val = tuple(x for x in argv[i + 1].split(",") if x)
            del argv[i:i + 2]
            if opt == "--tasks":
                TASKS = val
            else:
                ARMS = val
    if len(argv) < 3:
        sys.exit(__doc__)
    runs, keyfile, ref_dir, others = argv[0], argv[1], argv[2], argv[3:]
    key = json.load(open(keyfile, encoding="utf-8"))
    ref = load_ranks(ref_dir, key)

    cost, wall, passed, total = {}, {}, {}, {}
    for d in sorted(glob.glob(os.path.join(runs, "*"))):
        name = os.path.basename(d)
        for task in TASKS:
            if "-%s-" % task in name:
                arm = name.split("-%s-" % task)[0]
                try:
                    r = json.load(open(os.path.join(d, "result.json")))
                except (OSError, ValueError):
                    r = {}
                try:
                    c = json.load(open(os.path.join(d, "render", "checks.json")))
                except (OSError, ValueError):
                    c = {"pass": False}
                cost.setdefault((arm, task), []).append(r.get("total_usd") or 0.0)
                wall.setdefault((arm, task), []).append(r.get("wall_s") or 0)
                total[(arm, task)] = total.get((arm, task), 0) + 1
                passed[(arm, task)] = passed.get((arm, task), 0) + (1 if c.get("pass") else 0)

    print("## Cost (median $ per run), objective checks passed, median minutes\n")
    print("| arm | " + " | ".join(TASKS) + " | all runs $ |")
    print("|---|" + "---|" * (len(TASKS) + 1))
    for arm in ARMS:
        cells = []
        for task in TASKS:
            v = cost.get((arm, task), [])
            cells.append("$%.2f · %d/%d · %.1f min" % (statistics.median(v), passed.get((arm, task), 0), total.get((arm, task), 0),
                                                        statistics.median(wall[(arm, task)]) / 60) if v else "-")
        print("| %s | %s | $%.2f |" % (arm, " | ".join(cells), sum(sum(cost.get((arm, t), [])) for t in TASKS)))
    print("\nTotal: $%.2f over %d runs" % (sum(sum(v) for v in cost.values()), sum(total.values())))

    print("\n## Mean rank from the reference judge (1 = best), %d of %d screens ranked\n" % (len(ref), sum(1 for sid in key["screens"] if sid.rsplit("-", 1)[0] in TASKS)))
    print("| arm | " + " | ".join(TASKS) + " | all |")
    print("|---|" + "---|" * (len(TASKS) + 1))
    for arm in ARMS:
        cells = []
        for task in TASKS:
            v = [r[arm] for sid, r in ref.items() if sid.startswith(task + "-") and arm in r]
            cells.append("%.2f" % statistics.mean(v) if v else "-")
        v = [r[arm] for r in ref.values() if arm in r]
        print("| %s | %s | %s |" % (arm, " | ".join(cells), "%.2f" % statistics.mean(v) if v else "-"))

    print("\n## Bars\n")
    for strong in ("fable-high", "opus-high"):
        if strong not in ARMS or "sonnet-high" not in ARMS:
            continue
        w, l, t = versus(ref, strong, "sonnet-high")
        tasks_better = 0
        for task in TASKS:
            a = [r[strong] for sid, r in ref.items() if sid.startswith(task + "-") and strong in r]
            b = [r["sonnet-high"] for sid, r in ref.items() if sid.startswith(task + "-") and "sonnet-high" in r]
            if a and b and statistics.mean(a) < statistics.mean(b):
                tasks_better += 1
        print("- %s against sonnet-high: better on %d, worse on %d, tied on %d screens; one-sided sign test p = %.4f; "
              "better mean rank in %d of %d tasks." % (strong, w, l, t, binom_tail(w, w + l), tasks_better, len(TASKS)))
    d = [r["split"] - r["opus-high"] for r in ref.values() if "split" in r and "opus-high" in r]
    if d and "split" in ARMS and "opus-high" in ARMS:
        sc = statistics.median([c for t in TASKS for c in cost.get(("split", t), [])] or [0])
        oc = statistics.median([c for t in TASKS for c in cost.get(("opus-high", t), [])] or [0])
        ssum = sum(sum(cost.get(("split", t), [])) for t in TASKS)
        osum = sum(sum(cost.get(("opus-high", t), [])) for t in TASKS)
        print("- split against opus-high: mean rank difference %+.2f (bar: at most +0.50); total cost $%.2f against $%.2f "
              "(%+.0f %%; bar: at least 20 %% less); medians $%.2f and $%.2f." % (statistics.mean(d), ssum, osum,
                                                                             (ssum / osum - 1) * 100 if osum else 0, sc, oc))
    w, l, t = versus(ref, "opus-high", "opus-medium")
    if "opus-high" in ARMS and "opus-medium" in ARMS:
        print("- opus-medium ranked worse than opus-high on %d of %d screens (the taste rule falls above 7)." % (w, w + l + t))

    for folder in others:
        other = load_ranks(folder, key)
        taus = [x for x in (tau_b(ref[s], other[s]) for s in ref if s in other) if x is not None]
        top = sum(1 for s in ref if s in other and min(ref[s], key=ref[s].get) == min(other[s], key=other[s].get))
        print("- judge %s: mean Kendall tau-b with the reference %.2f over %d screens (bar 0.60); same first place on %d."
              % (os.path.basename(os.path.normpath(folder)), statistics.mean(taus) if taus else float("nan"), len(taus), top))


if __name__ == "__main__":
    main()

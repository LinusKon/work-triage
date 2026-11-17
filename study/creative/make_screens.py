#!/usr/bin/env python3
"""Build the blind ranking screens: make_screens.py <runs folder> <screens folder> <key file> [--seed N] [--tasks a,b].

One screen per task and repetition. Each run's deliverable and renders are copied to `<screens>/<task>-<rep>/<label>/`
under a shuffled label A to E, so nothing a judge sees names the arm. The key (label to run) goes to <key file>,
which belongs outside the screens folder and is opened only for the analysis.
"""
import json
import os
import random
import shutil
import subprocess
import sys

TITLES = {"motion": "Title sequence for TIDEWATER", "page": "Landing page for Loam",
          "scene3d": "Lighthouse at dusk", "copy": "Launch copy for Loam",
          "sting": "Logo sting for Kiln", "pricing": "Pricing page for Relay"}
TASKS = tuple(TITLES)


def page_strip(render, dest):
    """The two first-viewport shots side by side, scaled to one height."""
    a, b = os.path.join(render, "w1440-fold.png"), os.path.join(render, "w390-fold.png")
    if not (os.path.isfile(a) and os.path.isfile(b)):
        return False
    return subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-i", b, "-filter_complex",
                           "[0]scale=-2:900[l];[1]scale=-2:900[r];[l][r]hstack=inputs=2", dest]).returncode == 0


def main():
    args = sys.argv[1:]
    seed = 20261117
    if "--seed" in args:
        i = args.index("--seed")
        seed = int(args[i + 1])
        del args[i:i + 2]
    tasks = TASKS
    if "--tasks" in args:
        i = args.index("--tasks")
        tasks = tuple(t for t in args[i + 1].split(",") if t)
        bad = [t for t in tasks if t not in TITLES]
        if bad:
            sys.exit("unknown tasks: %s" % bad)
        del args[i:i + 2]
    if len(args) != 3:
        sys.exit(__doc__)
    runs, screens, keyfile = (os.path.abspath(a) for a in args)
    groups = {}
    for name in sorted(os.listdir(runs)):
        for task in tasks:
            marker = "-%s-" % task
            if marker in name:
                arm, rep = name.split(marker)
                groups.setdefault((task, rep), []).append((arm, os.path.join(runs, name)))
    rng = random.Random(seed)
    key = {}
    for (task, rep), members in sorted(groups.items()):
        sid = "%s-%s" % (task, rep)
        rng.shuffle(members)
        base = os.path.join(screens, sid)
        if os.path.isdir(base):
            shutil.rmtree(base)
        items = []
        for label, (arm, run) in zip("ABCDEFGH", members):
            dest = os.path.join(base, label)
            shutil.copytree(os.path.join(run, "repo"), dest, ignore=shutil.ignore_patterns(".git", ".omp"))
            item = {"label": label, "kind": "text" if task == "copy" else "html",
                    "path": "%s/%s" % (label, "copy.md" if task == "copy" else "index.html")}
            render = os.path.join(run, "render")
            strip = os.path.join(base, "%s-strip.png" % label)
            if task in ("page", "pricing"):
                if page_strip(render, strip):
                    item["strip"] = os.path.basename(strip)
                full = os.path.join(render, "w1440.png")
                if os.path.isfile(full):  # the whole page, for the model judges (`<label>-full.png`)
                    shutil.copy(full, os.path.join(base, "%s-full.png" % label))
            elif task != "copy" and os.path.isfile(os.path.join(render, "strip.png")):
                shutil.copy(os.path.join(render, "strip.png"), strip)
                item["strip"] = os.path.basename(strip)
            items.append(item)
            key.setdefault(sid, {})[label] = arm
        with open(os.path.join(base, "screen.json"), "w", encoding="utf-8") as f:
            json.dump({"id": sid, "task": task, "brief_title": TITLES[task], "items": items}, f, indent=1)
    with open(keyfile, "w", encoding="utf-8") as f:
        json.dump({"seed": seed, "screens": key}, f, indent=1)
    print("%d screens -> %s (key: %s)" % (len(groups), screens, keyfile))


if __name__ == "__main__":
    main()

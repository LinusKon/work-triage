#!/usr/bin/env python3
"""Write one CSV row per study run from the local run folders: export_data.py <study dir> <out.csv>.

Rounds are told apart by folder (`runs-v1` … `runs`); costs are re-collected with collect.py so that every round
carries Codex at list prices. No paths, prompts or session content are written.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

VERSIONS = {"base": "", "basemed": "", "basespawn": "", "skill201": "2.0.1", "skill21": "2.1.0", "skill22": "2.2.0",
            "skill23": "2.3.0", "skill24": "2.4.0", "skill25": "2.5.0", "skill26": "2.6.0", "skill261": "2.6.1"}
HEAD = {"basemed": "medium", "skill23": "medium"}
FOLDERS = [("runs-v1", 1), ("runs-v2", 2), ("runs-v3", 3), ("runs-v45", 5), ("runs", 6)]
FIELDS = ["round", "task", "arm", "rep", "skill_version", "head_level", "total_usd", "claude_usd", "codex_usd",
          "parent_usd", "claude_tokens", "codex_tokens", "wall_s", "spawns", "codex_runs", "hidden_passed",
          "hidden_tests", "sonnet_usd", "opus_usd", "note"]


def rows(study):
    seen = set()
    for folder, rnd in FOLDERS:
        base = os.path.join(study, folder)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            run = os.path.join(base, name)
            if not os.path.isfile(os.path.join(run, "result.json")):
                continue
            r = collect.collect(run)
            note = ""
            if folder == "runs-v2" and (r["arm"], r["task"]) in {("base", "A"), ("base", "B"), ("base", "D")}:
                continue  # copies of round 1's base runs, reused as round 2's baseline
            if folder == "runs-v45":
                rnd_here = 4 if r["arm"] in ("basespawn", "skill24") else 5
                if name == "base-H-1":
                    note = "pilot run of round 4, counted as base run 1 of round 5 as declared"
            else:
                rnd_here = rnd
            if folder == "runs" and r["task"] == "H":
                note = "regression check on build H, no reviews"
            if r["arm"] == "skill261":
                note = "control run after the wording-only release 2.6.1, no reviews"
            key = (rnd_here, name)
            if key in seen:
                continue
            seen.add(key)
            by = {"sonnet": 0.0, "opus": 0.0}
            for s in r["parent"] + r["subagents"]:
                for fam in by:
                    if fam in (s["model"] or ""):
                        by[fam] += s["usd"]
            yield {
                "round": rnd_here, "task": r["task"], "arm": r["arm"], "rep": r["rep"],
                "skill_version": VERSIONS.get(r["arm"], ""), "head_level": HEAD.get(r["arm"], "high"),
                "total_usd": "%.4f" % r["total_usd"], "claude_usd": "%.4f" % r["claude_usd"],
                "codex_usd": "%.4f" % r["codex_usd"], "parent_usd": "%.4f" % r["parent_usd"],
                "claude_tokens": r["claude_tokens"], "codex_tokens": r["codex_tokens"], "wall_s": r["wall_s"],
                "spawns": r["spawns"], "codex_runs": r["codex_runs"], "hidden_passed": int(r["hidden"]["passed"]),
                "hidden_tests": r["hidden"]["ran"], "sonnet_usd": "%.4f" % by["sonnet"],
                "opus_usd": "%.4f" % by["opus"], "note": note,
            }


def main():
    study, out = sys.argv[1], sys.argv[2]
    data = sorted(rows(study), key=lambda r: (r["round"], r["task"], r["arm"], r["rep"]))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    print("%d runs -> %s" % (len(data), out))


if __name__ == "__main__":
    main()

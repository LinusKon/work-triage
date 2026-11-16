#!/usr/bin/env python3
"""Write defects.csv and defect-kinds.csv from the blind adjudications: export_defects.py <study dir> <out dir>.

Per large build the adjudication folder holds `defects.json` (one entry per distinct defect, graded blind by one
rubric) and `results-py39.jsonl` / `results-py312.jsonl` (the probes' verdicts per run). `major` in defects.csv is
the count on Python 3.12, where every probe can be decided; `major_py39` is the count on the machine's Python 3.9.6.
"""
import csv
import json
import os
import sys

BUILDS = [("5", "H", "reviews-v45/adjudication"), ("6", "I", "reviews/adjudication")]


def main():
    study, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    runs, kinds = [], []
    for rnd, task, folder in BUILDS:
        base = os.path.join(study, folder)
        if not os.path.exists(os.path.join(base, "defects.json")):
            continue
        defects = {d["id"]: d for d in json.load(open(os.path.join(base, "defects.json"), encoding="utf-8"))}
        res = {}
        for tag in ("py39", "py312"):
            path = os.path.join(base, "results-%s.jsonl" % tag)
            if os.path.exists(path):
                res[tag] = {json.loads(l)["id"]: json.loads(l)["r"] for l in open(path, encoding="utf-8")}

        def count(tag, run, pred):
            if tag not in res:
                return ""
            return sum(1 for i, v in res[tag][run].items() if v == "DEFECT" and pred(defects[i]))

        for run in sorted(res["py312"]):
            arm, _, rep = run.rsplit("-", 2)
            major = lambda d: d["severity"] == "MAJOR"
            firm = lambda d: d["severity"] == "MAJOR" and not d.get("strict_reading", False)
            runs.append({"round": rnd, "task": task, "arm": arm, "rep": rep,
                         "major": count("py312", run, major), "major_py39": count("py39", run, major),
                         "major_not_strict": count("py312", run, firm) if any("strict_reading" in d for d in
                                                                              defects.values()) else "",
                         "minor": count("py312", run, lambda d: d["severity"] == "MINOR")})
        for i, d in sorted(defects.items()):
            hit = lambda arm_is_base: sum(1 for run, r in res["py312"].items()
                                          if r[i] == "DEFECT" and run.startswith("base-") == arm_is_base)
            kinds.append({"task": task, "id": i, "severity": d["severity"].lower(),
                          "strict_reading": {True: "yes", False: "no"}.get(d.get("strict_reading"), ""),
                          "newer_python_only": "yes" if d.get("py_newer_only") else "no",
                          "runs_base": hit(True), "runs_skill": hit(False), "title": d["title"]})
    for name, rows in (("defects.csv", runs), ("defect-kinds.csv", kinds)):
        with open(os.path.join(out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print("%d runs, %d defect kinds -> %s" % (len(runs), len(kinds), out))


if __name__ == "__main__":
    main()

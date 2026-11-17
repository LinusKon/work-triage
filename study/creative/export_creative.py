#!/usr/bin/env python3
"""Write one CSV row per creative output: export_creative.py <out.csv> <root> [<root> ...]

A root holds runs/, key.json and judges/ (opus, astra, opus-use, astra-use). Columns: brief, setup, repetition,
cost, minutes, objective checks, each judge's blind rank (1 = best of five) and "would you hand it to a client".
No paths or session content are written.
"""
import csv
import glob
import json
import os
import re
import sys

FIELDS = ["brief", "setup", "rep", "total_usd", "minutes", "checks_passed", "rank_opus", "rank_astra", "use_opus",
          "use_astra"]


def main():
    out, roots = sys.argv[1], sys.argv[2:]
    rows = []
    for root in roots:
        key = json.load(open(os.path.join(root, "key.json"), encoding="utf-8"))["screens"]
        marks = {}
        for judge, field in (("opus", "rank_opus"), ("astra", "rank_astra"), ("opus-use", "use_opus"),
                             ("astra-use", "use_astra")):
            for path in glob.glob(os.path.join(root, "judges", judge, "*.json")):
                d = json.load(open(path, encoding="utf-8"))
                for label, value in (d.get("use") if judge.endswith("use") else d["ranks"]).items():
                    marks.setdefault((d["id"], key[d["id"]][label]), {})[field] = value
        for run in sorted(glob.glob(os.path.join(root, "runs", "*"))):
            m = re.fullmatch(r"(.+)-([a-z0-9]+)-(\d+)", os.path.basename(run))
            setup, brief, rep = m.groups()
            r = json.load(open(os.path.join(run, "result.json"), encoding="utf-8"))
            c = json.load(open(os.path.join(run, "render", "checks.json"), encoding="utf-8"))
            row = {"brief": brief, "setup": setup, "rep": rep, "total_usd": "%.4f" % r["total_usd"],
                   "minutes": "%.1f" % (r["wall_s"] / 60), "checks_passed": int(bool(c.get("pass")))}
            row.update(marks.get(("%s-%s" % (brief, rep), setup), {}))
            rows.append(row)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("%d outputs -> %s" % (len(rows), out))


if __name__ == "__main__":
    main()

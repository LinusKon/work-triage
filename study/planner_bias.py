#!/usr/bin/env python3
"""Does a planner reach higher for its own family's models than a planner from the other family does?

    planner_bias.py run <out folder> [--reps 3]     48 small calls: 2 planners x 2 target families x 4 fixtures x reps
    planner_bias.py report <out folder>

Planners: Opus 5.5 high (omp, no skill, no context files) and gpt-6-astra high (Codex). Each gets the same neutral
fact sheet and one fixture plan from tests/work-triage/fixtures and assigns every step one model and level from the
target family. Rungs and accepted ranges come from the fixtures' expected.json and score.py's RUNG table.
Standard library only. No keys reach the children.
"""
import concurrent.futures
import json
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "..", "tests", "work-triage", "fixtures")
sys.path.insert(0, os.path.join(HERE, "..", "tests", "work-triage"))
from score import RUNG  # noqa: E402

FIXTURES = ("mixed", "swarm", "floor", "chain")
PAIRS = {
    "claude": ["Sonnet 5.5:medium", "Sonnet 5.5:high", "Opus 5.5:low", "Opus 5.5:medium", "Opus 5.5:high",
               "Opus 5.5:xhigh", "Fable 5.2:medium", "Fable 5.2:high"],
    "codex": ["gpt-6-luna:high", "gpt-6.1-terra:medium", "gpt-6.1-sol:medium", "gpt-6.1-sol:high", "gpt-6-astra:high"],
}
SHEET = {
    "claude": """Models (vendor's own description, list price per million tokens in / out):
- Sonnet 5.5: "strongest at well-scoped everyday tasks". $2 / $10.
- Opus 5.5: "our strongest daily driver". $4 / $20.
- Fable 5.2: "the most ambitious, open-ended technical work". $8 / $40.
A higher thinking level costs more tokens on the same model.""",
    "codex": """Models (vendor's own description; cost rises from luna to astra, astra costs about five times sol):
- gpt-6-luna: "clear, repeatable tasks: extraction, classification, transformation".
- gpt-6.1-terra: "fast, efficient model for clear writing, visual understanding, and computer use".
- gpt-6.1-sol: "near-Astra performance for complex work at a lower cost than Astra".
- gpt-6-astra: "most capable model for complex work across code, apps, and research".
A higher reasoning level costs more tokens on the same model.""",
}


def prompt(family, fixture):
    task = open(os.path.join(FIX, fixture, "task.md"), encoding="utf-8").read().strip()
    return ("You are planning who does each step of the plan below. Give every numbered step exactly one model and "
            "level from the allowed list: the cheapest that will do that step well. For a step only the human user can "
            "do (approving, creating a key, pressing a button), answer \"user\".\n\n%s\n\nAllowed answers: %s, user.\n\n"
            "Answer with one JSON object and nothing else, mapping each step number to its answer, for example "
            "{\"1\": \"%s\", \"2\": \"user\"}.\n\nThe plan:\n\n%s\n"
            % (SHEET[family], ", ".join(PAIRS[family]), PAIRS[family][1], task))


def call(planner, family, fixture, rep, out):
    name = "%s-%s-%s-%d" % (planner, family, fixture, rep)
    dest = os.path.join(out, name + ".json")
    if os.path.isfile(dest):
        return name, "exists"
    env = {k: v for k, v in os.environ.items() if not re.search(r"_(KEY|TOKEN|SECRET)$", k)}
    p = prompt(family, fixture)
    work = os.path.join(out, "work", name)
    os.makedirs(work, exist_ok=True)
    if planner == "opus":
        r = subprocess.run(["omp", "-p", "--model", "anthropic/claude-opus-5-5", "--thinking=high", "--no-context-files",
                            "--no-skills", "--session-dir", os.path.join(work, "sessions"), p],
                           cwd=work, env=env, capture_output=True, text=True, timeout=900)
        text = r.stdout
    else:
        ans = os.path.join(work, "answer.txt")
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-c", "model_reasoning_effort=high", "-s", "read-only",
                        "--skip-git-repo-check", "-o", ans, "-"], cwd=work, env=env, input=p, capture_output=True,
                       text=True, timeout=900)
        text = open(ans, encoding="utf-8").read() if os.path.isfile(ans) else ""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = {str(k): str(v) for k, v in json.loads(m.group(0)).items()}
    except (AttributeError, ValueError):
        open(os.path.join(work, "bad.txt"), "w", encoding="utf-8").write(text)
        return name, "unparsed"
    json.dump(d, open(dest, "w", encoding="utf-8"), indent=1)
    return name, "ok"


def run(out, reps):
    os.makedirs(out, exist_ok=True)
    jobs = [(pl, fam, fx, r) for pl in ("opus", "astra") for fam in ("claude", "codex") for fx in FIXTURES
            for r in range(1, reps + 1)]
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for name, status in ex.map(lambda j: call(*j, out), jobs):
            if status != "ok":
                print(name, status)
    print("%d answers in %s" % (len([f for f in os.listdir(out) if f.endswith(".json")]), out))


def report(out):
    exp = {fx: json.load(open(os.path.join(FIX, fx, "expected.json"), encoding="utf-8"))["steps"] for fx in FIXTURES}
    rows = {}   # (planner, family) -> list of dicts per assigned step
    for f in sorted(os.listdir(out)):
        if not f.endswith(".json"):
            continue
        planner, family, fixture, _ = f[:-5].split("-", 3)[0], None, None, None
        m = re.match(r"(opus|astra)-(claude|codex)-(\w+)-(\d+)\.json", f)
        planner, family, fixture = m.group(1), m.group(2), m.group(3)
        ans = json.load(open(os.path.join(out, f), encoding="utf-8"))
        for step, spec in exp[fixture].items():
            a = ans.get(step)
            if a is None:
                continue
            fam_pairs = [p for p in spec["accepted"] if p in PAIRS[family]]
            rec = {"fixture": fixture, "step": step, "answer": a, "rung": RUNG.get(a), "floor": bool(spec.get("floor")),
                   "user_step": spec["accepted"] == ["user"],
                   "lo": min((RUNG[p] for p in fam_pairs), default=None), "hi": max((RUNG[p] for p in fam_pairs), default=None)}
            rows.setdefault((planner, family), []).append(rec)
    print("| planner | assigns | steps with a model | mean rung | above the accepted range | below it | below on a floor step | "
          "said user on a model step |")
    print("|---|---|---|---|---|---|---|---|")
    for (planner, family), recs in sorted(rows.items()):
        model = [r for r in recs if r["rung"] is not None]
        ranged = [r for r in model if r["hi"] is not None]
        above = sum(1 for r in ranged if r["rung"] > r["hi"])
        below = sum(1 for r in ranged if r["rung"] < r["lo"])
        below_floor = sum(1 for r in ranged if r["rung"] < r["lo"] and r["floor"])
        user_wrong = sum(1 for r in recs if r["answer"] == "user" and not r["user_step"] and r["hi"] is not None)
        print("| %s | %s models | %d | %.2f | %d of %d (%.0f %%) | %d | %d | %d |" % (
            planner, family, len(model), statistics.mean(r["rung"] for r in model), above, len(ranged),
            100 * above / len(ranged) if ranged else 0, below, below_floor, user_wrong))
    print("\nRungs: Sonnet medium 1; Sonnet high, Opus low, sol medium, luna high, terra medium 2; Opus medium, sol high 3; "
          "Opus high, astra high 4; Opus xhigh 5; Fable medium 6; Fable high 7. The accepted range per step is the "
          "fixture's, restricted to the target family; steps with no accepted pair in that family are left out of the "
          "range columns.")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        run(sys.argv[2], int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 3)
    elif len(sys.argv) == 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        sys.exit(__doc__)

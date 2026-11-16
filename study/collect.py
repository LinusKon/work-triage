#!/usr/bin/env python3
"""Collect one study run into a JSON line, or summarise many: collect.py <run dir> | --table <runs dir> | --selftest."""
import glob
import json
import os
import re
import statistics
import sys

CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")


def session_files(sessions_dir):
    """Parent session files sit in sessions_dir; subagent files in a folder named after the parent file."""
    parents = sorted(glob.glob(os.path.join(sessions_dir, "*.jsonl")))
    subs = sorted(f for f in glob.glob(os.path.join(sessions_dir, "*", "*.jsonl"))
                  if os.path.basename(f) != "changes.jsonl")
    return parents, subs


def usage(path):
    tokens = usd = 0.0
    model = level = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "message":
                u = (e.get("message") or {}).get("usage") or {}
                tokens += u.get("totalTokens") or 0
                usd += (u.get("cost") or {}).get("total") or 0
            elif e.get("type") == "model_change" and model is None:
                model = e.get("model")
            elif e.get("type") == "thinking_level_change" and level is None:
                level = e.get("thinkingLevel")
    return {"tokens": int(tokens), "usd": round(usd, 4), "model": model, "level": level}


def spawns(path):
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '"toolCall"' not in line:
                continue
            e = json.loads(line)
            for c in (e.get("message") or {}).get("content") or []:
                if c.get("type") == "toolCall" and c.get("name") == "task":
                    count += len((c.get("arguments") or {}).get("tasks") or [])
    return count


# OpenAI standard API list prices per 1M tokens, short context (input, cached input, output),
# https://developers.openai.com/api/docs/pricing, read 2026-11-16. Codex on a ChatGPT plan is not billed this way;
# the figure makes Codex work comparable with Claude dollars.
CODEX_PRICES = {
    "gpt-6-astra": (10.0, 1.0, 50.0), "gpt-6.1-sol": (2.0, 0.10, 10.0),
    "gpt-6.1-terra": (1.0, 0.05, 5.0), "gpt-6-luna": (0.10, 0.01, 0.50),
}


def codex_usage(repo, start, end):
    """Per Codex rollout whose cwd is the run repo: model, level, final token counts, list-price dollars."""
    out = []
    real = os.path.realpath(repo)
    for path in glob.glob(os.path.join(CODEX_SESSIONS, "*", "*", "*", "rollout-*.jsonl")):
        mtime = os.path.getmtime(path)
        if mtime < start - 60 or mtime > end + 600:
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        cwd = re.search(r'"cwd":"([^"]*)"', text)
        if not cwd or not os.path.realpath(cwd.group(1)).startswith(real):
            continue
        totals = re.findall(r'"total_token_usage":(\{[^}]*\})', text)
        u = json.loads(totals[-1]) if totals else {}
        model = re.search(r'"model":"([^"]*)"', text)
        level = re.search(r'"effort":"([^"]*)"', text)
        model = model.group(1) if model else None
        inp, cached, outp = u.get("input_tokens", 0), u.get("cached_input_tokens", 0), u.get("output_tokens", 0)
        price = CODEX_PRICES.get(model)
        usd = ((inp - cached) * price[0] + cached * price[1] + outp * price[2]) / 1e6 if price else None
        out.append({"model": model, "level": level.group(1) if level else None, "tokens": u.get("total_tokens", 0),
                    "input": inp, "cached": cached, "output": outp, "usd": round(usd, 4) if usd is not None else None})
    return out


def hidden(path):
    if not os.path.exists(path):
        return {"ran": 0, "failed": None, "passed": False}
    text = open(path, encoding="utf-8", errors="replace").read()
    ran = re.search(r"^Ran (\d+) tests?", text, re.M)
    ran = int(ran.group(1)) if ran else 0
    bad = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", text))
    ok = bool(re.search(r"^OK\b", text, re.M)) and ran > 0
    return {"ran": ran, "failed": bad if ran else None, "passed": ok}


def read(path, default=None):
    try:
        return open(path, encoding="utf-8").read().strip()
    except OSError:
        return default


def collect(run_dir):
    name = os.path.basename(os.path.normpath(run_dir))
    arm, task, rep = name.rsplit("-", 2)
    parents, subs = session_files(os.path.join(run_dir, "sessions"))
    parent = [usage(p) for p in parents]
    sub = [dict(usage(s), name=os.path.basename(s)[:-6]) for s in subs]
    p_usd = sum(p["usd"] for p in parent)
    total = p_usd + sum(s["usd"] for s in sub)
    start, end = int(read(os.path.join(run_dir, "start"), 0)), int(read(os.path.join(run_dir, "end"), 0))
    repo = read(os.path.join(run_dir, "repo.txt"), "")
    codex = codex_usage(repo, start, end) if repo else []
    c_usd = sum(c["usd"] or 0 for c in codex)
    return {
        "id": name, "arm": arm, "task": task, "rep": int(rep), "exit": read(os.path.join(run_dir, "exit")),
        "wall_s": end - start,
        "claude_tokens": sum(p["tokens"] for p in parent) + sum(s["tokens"] for s in sub),
        "claude_usd": round(total, 4), "parent_usd": round(p_usd, 4),
        "parent_share": round(p_usd / total, 3) if total else None,
        "parent": parent, "subagents": sub, "spawns": sum(spawns(p) for p in parents),
        "codex_runs": len(codex), "codex_tokens": sum(c["tokens"] for c in codex), "codex": codex,
        "codex_usd": round(c_usd, 4), "total_usd": round(total + c_usd, 4),
        "hidden": hidden(os.path.join(run_dir, "hidden.txt")),
    }


def table(runs_dir):
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(runs_dir, "*", "result.json")))]
    print("| arm | task | runs | hidden pass | median $ | mean $ | median parent share | median wall s | spawns | codex runs |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    keys = sorted({(r["arm"], r["task"]) for r in rows})
    for arm, task in keys:
        g = [r for r in rows if r["arm"] == arm and r["task"] == task]
        usd = [r["claude_usd"] for r in g]
        share = [r["parent_share"] for r in g if r["parent_share"] is not None]
        print("| %s | %s | %d | %d/%d | %.2f | %.2f | %s | %d | %d | %d |" % (
            arm, task, len(g), sum(r["hidden"]["passed"] for r in g), len(g), statistics.median(usd),
            statistics.mean(usd), "%.2f" % statistics.median(share) if share else "—",
            statistics.median(r["wall_s"] for r in g), sum(r["spawns"] for r in g), sum(r["codex_runs"] for r in g)))
    for arm in sorted({r["arm"] for r in rows}):
        usd = [r["claude_usd"] for r in rows if r["arm"] == arm]
        print("\n%s: %d runs, median $%.2f, total $%.2f" % (arm, len(usd), statistics.median(usd), sum(usd)))
    print("\nCost by model and level (parent sessions and subagents):\n")
    print("| arm | model · level | runs using it | $ | share of arm $ | tokens |")
    print("|---|---|---|---|---|---|")
    for arm in sorted({r["arm"] for r in rows}):
        split, used, total = {}, {}, 0.0
        for r in (x for x in rows if x["arm"] == arm):
            seen = set()
            for s in r["parent"] + r["subagents"]:
                key = "%s · %s" % ((s["model"] or "?").split("/")[-1], s["level"] or "?")
                cur = split.setdefault(key, [0.0, 0])
                cur[0] += s["usd"]
                cur[1] += s["tokens"]
                seen.add(key)
                total += s["usd"]
            for key in seen:
                used[key] = used.get(key, 0) + 1
        for key, (usd, tok) in sorted(split.items(), key=lambda kv: -kv[1][0]):
            print("| %s | %s | %d | %.2f | %.0f %% | %.2fM |" % (arm, key, used[key], usd, 100 * usd / total, tok / 1e6))


def selftest():
    # Three early runs whose costs were counted by hand; checked only where their session files exist
    # (set STUDY_SELFTEST_SESSIONS to the folder that holds L1b/, M2/ and M5/).
    base = os.environ.get("STUDY_SELFTEST_SESSIONS",
                          os.path.expanduser("~/work-triage-2-tests/2026-11-16/sessions"))
    want = {"L1b": (2.3757, 2), "M2": (0.4993, 0), "M5": (2.8452, 6)}
    fails = 0
    for name, (usd, n_sub) in want.items():
        if not os.path.isdir(os.path.join(base, name)):
            print("skip %s: session files not present on this machine" % name)
            continue
        parents, subs = session_files(os.path.join(base, name))
        total = sum(usage(p)["usd"] for p in parents + subs)
        ok = abs(total - usd) < 0.01 and len(subs) == n_sub
        fails += not ok
        print("%s %s: $%.4f (want $%.4f), %d subagent files (want %d)" % ("ok " if ok else "BAD", name, total, usd, len(subs), n_sub))
    sample = "Ran 5 tests in 0.1s\n\nFAILED (failures=2, errors=1)\n"
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(sample)
    r = hidden(f.name)
    os.unlink(f.name)
    ok = r == {"ran": 5, "failed": 3, "passed": False}
    fails += not ok
    print("%s hidden parse: %s" % ("ok " if ok else "BAD", r))
    ok = abs(perm_p([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]) - 1 / 252) < 1e-12 and perm_p([1, 9], [2, 3]) > 0.5
    fails += not ok
    print("%s permutation test" % ("ok " if ok else "BAD"))
    print("SELFTEST %s" % ("PASS" if not fails else "FAIL"))
    return 1 if fails else 0


def rank_sum(low, high):
    """Sum of the ranks of `low` in the pooled sample (mid-ranks for ties)."""
    pooled = sorted(low + high)
    rank = {}
    for v in set(pooled):
        idx = [i + 1 for i, x in enumerate(pooled) if x == v]
        rank[v] = sum(idx) / len(idx)
    return sum(rank[v] for v in low)


def perm_p(low, high):
    """Exact one-sided permutation p of the rank-sum test: P(rank sum of `low` this small or smaller)."""
    import itertools
    pooled = low + high
    observed = rank_sum(low, high)
    hits = total = 0
    for combo in itertools.combinations(range(len(pooled)), len(low)):
        chosen = [pooled[i] for i in combo]
        rest = [pooled[i] for i in range(len(pooled)) if i not in combo]
        total += 1
        hits += rank_sum(chosen, rest) <= observed + 1e-9
    return hits / total


def compare(runs_dir, task, base_arm, skill_arm):
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(runs_dir, "*", "result.json")))]
    out = {}
    for arm in (base_arm, skill_arm):
        g = [r for r in rows if r["arm"] == arm and r["task"] == task]
        out[arm] = g
        usd = sorted(r["total_usd"] for r in g)
        print("%s: n=%d total$ %s median %.2f | claude median %.2f | hidden pass %d/%d | wall median %ds" % (
            arm, len(g), " ".join("%.2f" % u for u in usd), statistics.median(usd),
            statistics.median(r["claude_usd"] for r in g), sum(r["hidden"]["passed"] for r in g), len(g),
            statistics.median(r["wall_s"] for r in g)))
    b = [r["total_usd"] for r in out[base_arm]]
    s = [r["total_usd"] for r in out[skill_arm]]
    change = statistics.median(s) / statistics.median(b) - 1
    print("median change %+.1f %%, exact one-sided rank-sum p = %.4f" % (100 * change, perm_p(s, b)))


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    if len(sys.argv) == 3 and sys.argv[1] == "--table":
        table(sys.argv[2])
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "--compare":
        compare(*sys.argv[2:])
        return 0
    if len(sys.argv) == 2:
        print(json.dumps(collect(sys.argv[1])))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

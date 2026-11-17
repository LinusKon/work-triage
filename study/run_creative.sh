#!/usr/bin/env bash
# One run of the creative study: run_creative.sh <arm> <task> <rep> [--dry]
#   arms:  sonnet-high | opus-medium | opus-high | fable-high | split
#   tasks: motion | page | scene3d | copy   (briefs in study/creative/tasks/)
# Every run gets a fresh repository in <root>/runs/<arm>-<task>-<rep>/repo, no skill and no context files.
# After the session: render, objective checks, cost. Root: $WT_CREATIVE (default ~/work-triage-study/creative).
set -euo pipefail
arm="${1:?arm}"; task="${2:?task}"; rep="${3:?rep}"; dry="${4:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${WT_CREATIVE:-$HOME/work-triage-study/creative}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
id="$arm-$task-$rep"; out="$ROOT/runs/$id"; repo="$out/repo"

alone='Work alone: do not spawn subagents and do not call other models.'
case "$arm" in
    sonnet-high) model=anthropic/claude-sonnet-5-5; level=high;   how="$alone" ;;
    opus-medium) model=anthropic/claude-opus-5-5;   level=medium; how="$alone" ;;
    opus-high)   model=anthropic/claude-opus-5-5;   level=high;   how="$alone" ;;
    fable-high)  model=anthropic/claude-fable-5-2;  level=high;   how="$alone" ;;
    split|fable-directs)
        level=high
        if [ "$arm" = split ]; then model=anthropic/claude-opus-5-5; else model=anthropic/claude-fable-5-2; fi
        how='You are the director, not the maker. (1) Write the direction and a short acceptance list to `/tmp/'"$id"'-direction.md` (outside the repository). (2) Spawn exactly one subagent with `model: "anthropic/claude-sonnet-5-5:high"` that builds the deliverable from the brief and your direction. (3) When it returns, look at the result yourself, then send it one critique (`write agent://<name>`) and let it revise once. You never edit the deliverable yourself and you spawn nothing else.' ;;
    *) echo "unknown arm: $arm" >&2; exit 2 ;;
esac
brief="$HERE/creative/tasks/$task.md"
[ -f "$brief" ] || { echo "unknown task: $task" >&2; exit 2; }

prompt="$(printf '%s\n\n%s\n\nTo look at a result you may render it with headless Chrome: `"%s" --headless --allow-file-access-from-files --screenshot=/tmp/shot.png --window-size=1920,1080 "file://$PWD/index.html?t=4"`. The result is judged from renders made this way and by people looking at it.\n\n' \
    'Do the work in this brief in this repository.' "$how" "$CHROME"; cat "$brief")"
cmd=(omp -p --model "$model" --thinking="$level" --no-context-files --no-skills --session-dir "$out/sessions")
if [ "$dry" = "--dry" ]; then
    printf '%s  [%s]\n' "${cmd[*]}" "$id"; exit 0
fi
[ -e "$out" ] && { echo "exists: $out (no reruns)" >&2; exit 3; }
mkdir -p "$repo" "$out/render"
printf '%s\n' "$prompt" > "$out/prompt.txt"
[ -d "$HERE/creative/$task.seed" ] && cp -R "$HERE/creative/$task.seed/." "$repo/"
(cd "$repo" && git init -q && git add -A && git commit -q --allow-empty -m init)

# Children never see API keys: every variable ending in _KEY, _TOKEN or _SECRET is removed from their environment.
strip=$(compgen -e | grep -E '_(KEY|TOKEN|SECRET)$' | sed 's/^/-u /' | tr '\n' ' ' || true)
date -u +%s > "$out/start"
set +e
# shellcheck disable=SC2086
(cd "$repo" && env $strip "${cmd[@]}" "$prompt") > "$out/answer.md" 2> "$out/err.txt"
echo $? > "$out/exit"
date -u +%s > "$out/end"
if [ "$task" != copy ]; then
    (cd "$HERE/creative" && timeout 300 node render.mjs "$task" "$repo" "$out/render") > "$out/render.txt" 2>&1
fi
(cd "$HERE/creative" && python3 checks.py "$task" "$repo" "$out/render") > "$out/checks.txt" 2>&1
set -e
python3 "$HERE/collect.py" "$out" > "$out/result.json" || true
python3 - "$out" <<'EOF'
import json, os, sys
out = sys.argv[1]
r = json.load(open(os.path.join(out, "result.json"))) if os.path.getsize(os.path.join(out, "result.json")) else {}
try:
    c = json.load(open(os.path.join(out, "render", "checks.json")))
except Exception:
    c = {"pass": None, "checks": {}}
failed = [k for k, v in c.get("checks", {}).items() if not v.get("ok")]
print("\t".join(str(x) for x in (os.path.basename(out), r.get("exit"), r.get("total_usd"), r.get("wall_s"),
                                 c.get("pass"), ",".join(failed) or "-")))
EOF

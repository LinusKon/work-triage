#!/usr/bin/env bash
# One study run: run_study.sh <arm> <task> <rep>
#   arm:  skill21 | skill201 | base
#   task: A | B | C | D (spec in study/tasks/<task>.md)
# Writes $STUDY/runs/<arm>-<task>-<rep>/ with prompt.txt, answer.md, err.txt, repo.txt, times, hidden.txt and
# the omp session files, then prints one JSON line from collect.py. No retries.
set -euo pipefail

arm=$1 task=$2 rep=$3
STUDY=${STUDY:-$HOME/work-triage-study}
HERE=$(cd "$(dirname "$0")" && pwd)
id="$arm-$task-$rep"
out="$STUDY/runs/$id"
[ -e "$out" ] && { echo "exists: $out" >&2; exit 1; }
mkdir -p "$out"

level=high
case "$arm" in
    skill261) skill="$STUDY/skills/2.6.1/work-triage" ;;
    skill26)  skill="$STUDY/skills/2.6.0/work-triage" ;;
    skill25)  skill="$STUDY/skills/2.5.0/work-triage" ;;
    skill24)  skill="$STUDY/skills/2.4.0/work-triage" ;;
    skill23)  skill="$STUDY/skills/2.3.0/work-triage"; level=medium ;;
    skill22)  skill="$STUDY/skills/2.2.0/work-triage" ;;
    skill21)  skill="$STUDY/skills/2.1.0/work-triage" ;;
    skill201) skill="$STUDY/skills/2.0.1/work-triage" ;;
    base)     skill="" ;;
    basemed)  skill=""; level=medium ;;
    basespawn) skill=""; extra='Distribute the work across subagents with the task tool: the operations are written by subagents, not by you.' ;;
    *) echo "unknown arm: $arm" >&2; exit 2 ;;
esac
spec="$HERE/tasks/$task.md"
[ -f "$spec" ] || { echo "unknown task: $task" >&2; exit 2; }

{
    [ -n "$skill" ] && printf 'Read the work-triage skill at `%s/SKILL.md` and follow it.\n\n' "$skill"
    printf 'Plan and run this in this repository. Subagents (the task tool) and the Codex CLI (`codex exec`, logged in) are available.\n\n'
    [ -n "${extra:-}" ] && printf '%s\n\n' "$extra"
    cat "$spec"
} > "$out/prompt.txt"

repo=$(mktemp -d "/tmp/wts-$id.XXXX")
if [ -d "$HERE/tasks/$task.seed" ]; then
    cp -R "$HERE/tasks/$task.seed/." "$repo/"
    (cd "$repo" && git init -q && git add -A && git commit -q -m init)
else
    (cd "$repo" && git init -q && git commit -q --allow-empty -m init)
fi
echo "$repo" > "$out/repo.txt"

# Children never see API keys: every variable ending in _KEY, _TOKEN or _SECRET is removed from their environment.
strip=$(compgen -e | grep -E '_(KEY|TOKEN|SECRET)$' | sed 's/^/-u /' | tr '\n' ' ')
date -u +%s > "$out/start"
set +e
# shellcheck disable=SC2086
(cd "$repo" && env $strip omp -p --model anthropic/claude-opus-5-5 --thinking="$level" \
    --no-context-files --no-skills --session-dir "$out/sessions" "$(cat "$out/prompt.txt")") \
    > "$out/answer.md" 2> "$out/err.txt"
echo $? > "$out/exit"
date -u +%s > "$out/end"
(cd "$repo" && timeout 300 python3 "$STUDY/hidden/test_hidden_$task.py") > "$out/hidden.txt" 2>&1
set -e

python3 "$HERE/collect.py" "$out" | tee "$out/result.json"

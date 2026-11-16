#!/usr/bin/env bash
# Blind review of one study run: blind_review.sh <run id>
# Copies the run repo without git history, plans, run logs and Codex files to a neutral name, has a fresh
# Opus 5.5 high session (no context files, no skills) review it against the task spec, and stores the review
# under $STUDY/reviews/<blind id>.md. The map from blind id to run id stays in $STUDY/reviews/map.tsv.
set -euo pipefail

id=$1
STUDY=${STUDY:-$HOME/work-triage-study}
HERE=$(cd "$(dirname "$0")" && pwd)
run="$STUDY/runs/$id"
task=${id#*-}; task=${task%-*}
mkdir -p "$STUDY/reviews"
blind="r$(od -An -N4 -tx4 /dev/urandom | tr -d ' ')"
printf '%s\t%s\n' "$blind" "$id" >> "$STUDY/reviews/map.tsv"

copy=$(mktemp -d "/tmp/$blind.XXXX")
rsync -a --exclude .git --exclude .omp --exclude 'docs/plan*.md' --exclude 'docs/run-log.md' --exclude 'docs/codex/' \
    --exclude '__pycache__' "$(cat "$run/repo.txt")/" "$copy/"

{
    printf 'Review the deliverable in this folder against the specification below. Do not edit any file.\n'
    printf 'You may read everything and run commands (its tests, small scripts in /tmp).\n'
    printf 'List each finding with: severity (major or minor), file and line, evidence (a command with its output,\n'
    printf 'or a quote), and the spec sentence it violates if any. Major: a spec violation a user would hit, a\n'
    printf 'security weakness, or a missing deliverable. Minor: everything else worth fixing. Only confirmed findings.\n'
    printf 'This folder is a snapshot: git history, plans, run logs and Codex files were removed on purpose; their\n'
    printf 'absence is not a finding, and nothing outside the specification is required.\n'
    printf 'End with exactly one line: COUNTS major=<n> minor=<n>\n\n--- SPECIFICATION ---\n'
    cat "$HERE/tasks/$task.md"
} > "$STUDY/reviews/$blind.prompt.txt"

strip=$(compgen -e | grep -E '_(KEY|TOKEN|SECRET)$' | sed 's/^/-u /' | tr '\n' ' ')
# shellcheck disable=SC2086
(cd "$copy" && env $strip omp -p --model anthropic/claude-opus-5-5 --thinking=high --no-context-files \
    --no-skills --session-dir "$STUDY/reviews/sessions/$blind" "$(cat "$STUDY/reviews/$blind.prompt.txt")") \
    > "$STUDY/reviews/$blind.md" 2> "$STUDY/reviews/$blind.err" || true
grep -E '^COUNTS ' "$STUDY/reviews/$blind.md" | tail -1 | sed "s/^/$blind /"

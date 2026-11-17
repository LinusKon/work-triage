#!/usr/bin/env bash
# One blind "would you use it" judgment of one screen: judge_use.sh <opus|astra> <screen id>
# Stand-in for the human mark while that is missing; writes <root>/judges/<judge>-use/<id>.json.
set -euo pipefail
judge="${1:?judge}"; sid="${2:?screen id}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${WT_CREATIVE:-$HOME/work-triage-study/creative}"
dir="${WT_SCREENS:-$ROOT/screens}/$sid"; out="${WT_JUDGES:-$ROOT/judges}/$judge-use"; task="${sid%-*}"
mkdir -p "$out/raw"
[ -e "$out/$sid.json" ] && { echo "exists: $sid"; exit 0; }
case "$task" in
  motion)  shown='For each option one contact sheet `<label>-strip.png`: ten frames in reading order at t = 0.5, 1, 2.5, 4, 5, 6.5, 8, 8.5, 9.5 and 10 seconds.' ;;
  sting)   shown='For each option one contact sheet `<label>-strip.png`: seven frames in reading order at t = 0.5, 1.5, 2.5, 3.5, 4.5, 5.5 and 6 seconds.' ;;
  scene3d) shown='For each option one contact sheet `<label>-strip.png`: four frames in reading order at t = 0, 3, 6 and 9 seconds.' ;;
  page|pricing) shown='For each option `<label>-strip.png` (the first screen at 1440 and at 390 pixels width, side by side) and `<label>-full.png` (the whole page at 1440).' ;;
  copy)    shown='For each option the text file `<label>/copy.md`.' ;;
esac
prompt="$out/raw/$sid.prompt.txt"
{
  printf 'You are a creative director deciding which of five answers to the same brief, labelled A to E, you would hand to a paying client. You do not know who made them and must not try to find out: look only at the files named below, in this folder.\n\n%s\n\n' "$shown"
  printf 'Judge each answer on its own, not against the others. For each one answer:\n- "yes": you would deliver it as it is;\n- "fix": you would deliver it after small fixes that take minutes (a spacing, a word, a colour);\n- "no": it breaks a requirement of the brief, or it needs real rework, or it looks or reads like a draft.\nBe as strict as a client would be. It is fine if none or all pass.\n\n'
  printf 'Answer with one JSON object and nothing else: {"id": "%s", "use": {"A": "yes", "B": "fix", "C": "no", "D": "no", "E": "yes"}, "notes": {"A": "one sentence", "B": "...", "C": "...", "D": "...", "E": "..."}}\n\nThe brief:\n\n' "$sid"
  cat "$HERE/tasks/$task.md"
} > "$prompt"
strip=$(compgen -e | grep -E '_(KEY|TOKEN|SECRET)$' | sed 's/^/-u /' | tr '\n' ' ' || true)
cd "$dir"
if [ "$judge" = opus ]; then
  # shellcheck disable=SC2086
  env $strip omp -p --model anthropic/claude-opus-5-5 --thinking=high --no-context-files --no-skills \
      --session-dir "$out/raw/$sid.sessions" "$(cat "$prompt")" > "$out/raw/$sid.answer.txt" 2> "$out/raw/$sid.err.txt"
else
  imgs=()
  if [ "$task" != copy ]; then for f in ?-strip.png ?-full.png; do [ -f "$f" ] && imgs+=(-i "$f"); done; fi
  env $strip codex exec -m gpt-6-astra -c model_reasoning_effort=high -s read-only --skip-git-repo-check \
      -o "$out/raw/$sid.answer.txt" ${imgs[@]+"${imgs[@]}"} - < "$prompt" > "$out/raw/$sid.log.txt" 2>&1
fi
python3 - "$out/raw/$sid.answer.txt" "$out/$sid.json" "$sid" <<'PY'
import json, sys
text = open(sys.argv[1], encoding="utf-8").read()
d = json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
assert d["id"] == sys.argv[3] and sorted(d["use"]) == list("ABCDE") and all(v in ("yes", "fix", "no") for v in d["use"].values())
json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
print("ok", sys.argv[3], d["use"])
PY

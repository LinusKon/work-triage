# Codex implementation

Rows come here when the triage sets `Run as` to `Codex` for implementation: bounded or bulk code to a spec
with a check that stands alone (tests, a selftest, a typecheck): `gpt-6.1-sol` `medium`, `high` with edge
cases (routing: `spawn.md`, "2. Decide: model and level"). A failed check: first failure, same model one level
up (`medium` → `high`); second failure, `gpt-6-astra` `high`. The cell "fails twice → gpt-6-astra high" is
the short form of that path.
Never here: security, secrets, production, paid runs, gates; signed-in web; taste, prompts for image and
video models, plans and designs; `gpt-6-luna` on security or edge-case work.

Codex never commits, pushes, deploys or edits global config. The parent scopes the row, reads the diff and
runs the check; Codex's report is a claim, not proof.

## Run a row

The primary way is the skill's script. Call it by absolute path, `<skill-dir>/scripts/codex_row.sh`, where
`<skill-dir>` is the folder SKILL.md was loaded from (`skills/work-triage` in the public repository; in omp,
`omp skill list --json` prints its `path`):

```
codex_row.sh <implement|review|check> --model <codex-model> --level <low|medium|high|xhigh>
             --prompt <file> --out <file> [--cd <dir>] [--base <branch> | --uncommitted] [--dry-run]
```

- `implement` runs `codex exec` with sandbox `workspace-write`, the prompt from `--prompt`, and writes
  Codex's final message to `--out`. `--cd` sets Codex's working root; the default is the current directory.
- `--model` and `--level` are required (exit 2 without them): never rely on Codex's configured default,
  which is usually the most expensive choice (`gpt-6-astra` `high`).
- The script removes every variable ending in `_KEY`, `_TOKEN` or `_SECRET` from Codex's environment,
  except `OPENAI_API_KEY` and `CODEX_API_KEY`, which a Codex CLI not signed in with `codex login` needs.
  Its exit code is Codex's; the last line of output is the `--out` path.
- `--dry-run` prints the command and exits 0: use it to confirm model and level before a long run.

What the script runs for `implement`, and the raw command when the script is not available:

```bash
env -u <KEY_NAME> codex exec -m gpt-6.1-sol -c model_reasoning_effort="medium" \
  -s workspace-write -o "$OUT" - < "$PROMPT"
```

Add `--skip-git-repo-check` only when running outside a git repository on purpose.

## Long runs, by harness

- **omp:** start the script as an `async` bash job with `timeout: 3600`. The result arrives by itself, so
  there is no `resume` step. Start every Codex row of a wave in the same turn as the wave's `tasks[]` batch.
- **Claude Code:** run it in the foreground with a long Bash timeout (600000 ms). If it times out, continue
  with `env -u <KEY_NAME> codex exec resume --last -o "$OUT"` from the same directory (resume picks the
  newest session of the current directory; `--all` disables that filter); repeat until `$OUT` exists.
  Never background it and end the turn there: Claude Code does not wake an agent for an untracked job, so
  the run stalls. Two runs in one directory make `--last` ambiguous: resume by session id instead.

## Prompt

Codex sees nothing but the prompt file. A default shape:

```
Implement: <one-sentence goal>.

Context:
- Files in scope: <paths>
- Requirements: <bullets>
- Out of scope / do not touch: <bullets>
- Check: <the command that proves it works>

Constraints:
- Edit only files in scope. Do not commit, push, or change git state.
- Match the surrounding code style.
- After editing, state what you changed and the check's output.
```

## Before and after

1. Pin the state with `git status --short`, so Codex's edits stand apart from changes already there.
2. After the run, read `git diff --stat` and the diff of the owned files, then run the row's check
   yourself. This is the acceptance before rows that build on it start; it is not a review row. Report what
   changed and the check's real output; a failed check is reported as failed.
3. Reviews come at the join, after the consumers, and cover the merged result (`verify.md`).

## Parallel Codex rows

Codex rows follow the ownership rule of every row (`schedule.md`): rows that touch the same file are merged
or ordered, never run in parallel, whatever the worktree.

If `codex` is missing or will not start, report the error; the row then runs on Claude at the rung `spawn.md`
gives it.

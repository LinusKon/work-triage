# Codex review

A Codex review or second opinion runs only when the user asks for one: `gpt-6-astra` `high` is the most
expensive model. By default a build gets one review, by `wt-reviewer` at the join (`SKILL.md` section 2); a
Codex review the user asked for comes in addition to it. Reviewer prompt, severity rules and fix rounds:
`verify.md`.

Never here: security and secrets rows. They get one `wt-reviewer` review (Opus 5.5 `high`, `xhigh` only on
escalation) and stay out of every Codex review's scope: name the rows a Codex review covers and leave those
out. A row whose check stands alone needs no review of its own; accepting it (reading output and check) is not a
review.

Codex's findings are evidence, not authority: the parent (the main session the user talks to) checks each one
against the code before it counts.

## Run a review

The primary way is `<skill-dir>/scripts/codex_row.sh review` (where the script lives, its interface and the
harness rules for long runs: `codex-implementation.md`, "Run a row" and "Long runs, by harness"):

```
codex_row.sh review --model gpt-6-astra --level high --prompt <file> --out <file>
                    [--base <branch> | --uncommitted] [--cd <dir>]
```

- The prompt file carries the spec to review against, the rows in scope and the reviewer prompt from
  `verify.md`.
- `--base <branch>` asks for the branch diff against that base (`git diff <branch>...HEAD`); `--uncommitted`
  or no scope flag asks for staged, unstaged and untracked changes.
- The script removes API keys and tokens from Codex's environment.

What the script runs: always `codex exec` with sandbox `read-only`, never `codex exec review`. It puts a
header before the prompt file ("Review only; do not edit files or change git state", then the scope as
text) and pipes both to Codex, so Codex reads the diff itself. What `--dry-run` prints for `--uncommitted`,
wrapped for reading:

```bash
{ printf %s 'Review only; do not edit files or change git state. Review staged, unstaged, and
untracked changes in the working tree. Use the following specification and review instructions:

'; cat -- "$PROMPT"; } | env -u <KEY_NAME> codex exec -m gpt-6-astra \
  -c model_reasoning_effort="high" -s read-only -o "$OUT" -
```

Raw alternative: `codex exec review` takes `-m`, `-o`, a prompt (`-` reads stdin) and the scope flags
`--uncommitted`, `--base <branch>`, `--commit <sha>`; the top-level `codex review` has no `-m` and no `-o`.
Unverified (the help of `codex-cli 0.166.0` is silent): that a custom prompt combines with a scope flag (an
earlier run rejected it), and that it cannot write, since it has no `-s` option. Check `git status --short`
after such a run.

## Outside a git repository

`codex exec` refuses to run outside a git repository, and the script passes no `--skip-git-repo-check`. For
a folder of skills, docs or prompts, copy the files into a scratch folder and run the raw
`codex exec -s read-only --skip-git-repo-check -C <folder>` with the same model, level, `-o` and prompt.
Name in the prompt the files to read, what they are for and the requirements.

## Reporting back

Before relaying a finding, read the cited code or diff and decide whether it is real. Report confirmed
issues apart from Codex suggestions you did not verify. If Codex finds nothing, say so and name the review
target it inspected.

If `codex` is missing or the run fails, report the error to the user; the `wt-reviewer` review at the join stands.

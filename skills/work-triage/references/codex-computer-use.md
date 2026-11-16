# Codex computer use

Codex is optional: a local app check goes to Codex only when the user works with Codex or asks for it;
otherwise the parent (the main session the user talks to) checks the app with its own tools. A Codex check
covers real UI interaction, screenshots, simulator, browser or device state, or a runtime check outside the
parent's context, with no login. Model `gpt-6.1-terra` `medium`. There is no calibration data for terra yet,
so the parent always looks at the captured evidence itself.

Never here:

- Ordinary code reading, typechecks, lints or tests the parent can run directly.
- Signed-in websites: they stay with the user's own signed-in browser session, the only one with the
  login.
- Security, secrets, production, paid runs and gates, as for every Codex row (`codex-implementation.md`).

Launching apps, simulators or browsers to verify the work needs no question. Ask the user first only if
the run could disrupt their environment beyond that: closing their apps, changing system settings, acting
on real accounts or data.

Codex drives a browser or the machine through its `browser`, `chrome`, `computer-use` and
`unified-computer-use` plugins; they must be enabled in Codex's `config.toml`.

## Run a check

The primary way is `<skill-dir>/scripts/codex_row.sh check` (where the script lives, its interface and the
harness rules for long runs:
`codex-implementation.md`, "Run a row" and "Long runs, by harness"):

```
codex_row.sh check --model gpt-6.1-terra --level medium --prompt <file> --out <file> [--cd <dir>]
```

`check` runs with sandbox `workspace-write`: launch the app, drive the browser, write screenshots into
the workspace. The script removes API keys and tokens from Codex's environment. `codex exec` is
non-interactive, so it does not stop for approvals.

What the script runs, and the raw command when the script is not available or the check needs more:

```bash
env -u <KEY_NAME> codex exec -m gpt-6.1-terra -c model_reasoning_effort="medium" \
  -s workspace-write -o "$OUT" - < "$PROMPT"
```

Use `-s danger-full-access` in the raw command only when the run must reach outside the workspace
(a system browser profile, ports or paths elsewhere); try `workspace-write` first.

## Workflow

1. Decide what "verified" means: the flow to exercise and what a pass looks like (a screenshot, a UI
   state, a console line, an HTTP response).
2. Make a scratch folder for the prompt, the report and the screenshots.
3. Write a self-contained prompt: how to launch or reach the app, what to do, which evidence to capture
   and where to save it.
4. Run the check, then read the report and open every screenshot before relaying the result.

## Prompt

```
Verify: <the flow or behavior to confirm>.

Steps:
- Launch / open: <how to start the app or URL>
- Do: <the interaction to perform>
- Capture: save a screenshot to <scratch folder>/<name>.png and report the observed state.

Report whether it passed, what you saw, and the path to each screenshot. Do not change
code or system settings.
```

Write the real scratch folder path into the prompt.

## Reporting back

Look at the screenshots and captured evidence yourself before saying it passed. Separate what Codex
observed from what it inferred. If the flow failed, report the observed state, not a guess.

If `codex` is missing or the run fails, report the error and verify the flow with the parent's own tools.

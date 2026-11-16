# Running a triaged plan in omp

Verified against omp 18.20.3 on 2026-11-16. omp (oh-my-pi) also runs inside the Tern app, which adds no
agent terms of its own. Read this before the first spawn; the rules themselves are in `SKILL.md` and `spawn.md`.

## Terms

| omp | Claude Code | Source |
|---|---|---|
| subagent; its `name` is its id | subagent | `omp://tools/task.md` |
| agent type (`agent`: `task`, `scout`, `reviewer`, `security-reviewer`, `sonic`) | `subagent_type` | `omp://tools/task.md` |
| `task` tool; one call spawns a `tasks[]` batch with a shared `context` | Agent tool; several calls in one message | `omp://tools/task.md` |
| parent (the top session is `Main`) | main conversation | `omp://tools/task.md` |
| per-call `model`, model selector `provider/model-id:level` | per-invocation `model` alias | `omp://task-agent-discovery.md` |
| thinking level | effort level | `omp://models.md` |
| allow-list `task.perCallModelAllow` | none | `omp://task-agent-discovery.md` |
| idle / parked agent, revived by `write agent://<id>` | resumed subagent | `omp://tools/task.md` |

## Spawning a wave

One wave is one `task` tool call (`omp://tools/task.md`): the shared `context` first (with
`task.speculativeLaunch` each item starts as soon as its JSON closes), then one `tasks[]` item per row.
- `context`: the contracts the parent settled before the wave (terms, interfaces, file names, formats).
  Children do not inherit the conversation; they get the workspace, skills, rules and `local://`.
- `name`: CamelCase, at most 32 characters, unique; it becomes the agent's id for messages.
- `agent`: on each item, never at the top level; omit it for the default `task` type.
- `model`: the row's model selector, always with a level (next section).
- `task`: self-contained: the row's `Owns`, the change, the tools and sources to use, the acceptance check,
  and the output as a path plus a short summary. It ends with a stop condition: the smallest change that
  passes the acceptance check, run that check, stop when it passes. Never "be certain", "be thorough" or
  "compare several approaches": raise the level instead. No builds, linters or test suites on shared state:
  the integration owner runs them once after the wave.
- `solutionSpace`: required; how open the row is. It is the only input of the `auto` level classifier.

```json
{ "name": "ReadmeExamples", "model": "anthropic/claude-opus-5-5:medium",
  "task": "# Target\nREADME.md, section 'Export formats' only.\n# Change\nOne example per format, using docs/interface.md.\n# Acceptance\nEvery example runs as written; run them, stop when they pass.\n# Output\nWrite README.md; reply with its path and a two-line summary.",
  "solutionSpace": "wording and example choice open; the interface is fixed" }
```

## Model selector

- Write `provider/model-id:level`, e.g. `anthropic/claude-sonnet-5-5:medium`. It is matched literally: no
  alias, glob or partial id. The level is clamped to what the model supports and to `task.maxEffort`
  (`omp://task-agent-discovery.md`).
- Without `model` the row runs on the parent's model and level (the `task` role falls back to the session):
  a forgotten selector runs a Sonnet row on the orchestrator. The task tool marks this model `(default)`.
- A per-call model gets no retry fallback, context promotion or prewalk: it fails rather than switch models.
- Never use the item field `effort`: it is relative (`lo`/`med`/`hi` map to the model's lowest, middle and
  highest level, so `hi` is `max` before the cap) and overrides the agent's selector
  (`omp://task-agent-discovery.md`). `task.enableEffort: false`, the default, removes it
  (`omp://tools/task.md`).

## Preflight

These are the user's settings: check them; ask before writing any. They gate subagent rows that pass `model`;
Codex rows do not pass this gate. Check with `omp config get <key>` (`omp://settings.md`); the task tool's
description lists the models approved now. Sources for 1-4: `omp://task-agent-discovery.md`.
1. `task.perCallModel` is `on` (default `off`; only operator layers raise it, a project only lowers it).
2. Each model of the wave is granted by one of: a chat role's `modelRoles` value naming its exact id in an
   operator layer (global config, `--config` files; never project settings; a glob grants nothing); the
   frontmatter `model` of the bundled or user-level agent type the row selects; the parent's live model.
3. If `task.perCallModelAllow` is set, it narrows the grants: each model must also be on it, as
   `provider/model-id` without `:level`. Unset, it narrows nothing.
4. `task.maxEffort` is at or above the wave's highest level (`xhigh` suffices); else the spawn fails.
5. Limits (`omp://tools/task.md`): `task.maxConcurrency` (default 32; a wave of at most 15 rows fits);
   `task.maxRecursionDepth` (default 2: a child at the cap loses the `task` tool, so rows never spawn waves);
   `task.softRequestBudget` (default 200 per agent; past it a wrap-up notice, at 1.5x a stop).

## Checking the level that ran

After the first spawn of a wave, compare the requested selector with what ran, and log what ran:
- Tool result: `resolvedModel`, `resolvedThinkingLevel`, `resolvedModelIsFallback` (`omp://tools/task.md`).
- Session file `<Name>.jsonl` in the folder beside the parent's own session file (same name without `.jsonl`;
  with `--session-dir D`: `D/<session>/<Name>.jsonl`; `find <the parent's session dir> -name '<Name>.jsonl'`):
  `model_change.model`; `thinking_level_change.thinkingLevel` and `configured`;
  `session_init` with `resolvedModel`, `perCallModelIdentity`, `perCallThinkingLevel` (`omp://session.md`).
  Verified on omp 18.20.3 (2026-11-16).

## The parent's own level

Set at start by `defaultThinkingLevel` or `--thinking` (`omp://settings.md`, `omp://cli-reference.md`). Only
the user changes it: `Shift+Tab` cycles the level (`omp://keybindings.md`), or `/effort` (omp's docs describe
`/effort` only for a focused subagent, `omp://agent-hub.md`). No tool lets an agent raise its own level, so
escalation (`spawn.md`, "Orchestrator") is one `anthropic/claude-fable-5-2:high` subagent with the question
and the artefact paths, or a request to the user. Fresh orchestrator session (`omp://cli-reference.md`):

```sh
omp --model "anthropic/claude-fable-5-2" --thinking=medium "Read <handoff file> and continue there."
```

## Waiting and follow-ups

- Results arrive by themselves (`omp://tools/wait.md`); call `wait` only when nothing else can be done.
  Output over 11,500 characters arrives as a preview, the full text at `agent://<id>` (`omp://tools/task.md`).
- The planned fix round goes to the author: `write agent://<id>` reaches an idle agent and revives a parked
  one (parked after `task.agentIdleTtlMs`); it keeps its context (`omp://tools/task.md`).
- Other new work is a fresh, narrow row with its own triage line: a revived agent carries its whole context
  into every request. `read proc://<id>` inspects an agent or job; `write proc://<id>/kill` cancels it.

## Codex rows

A Codex row runs `<skill>/scripts/codex_row.sh implement --model gpt-6.1-sol --level medium --prompt <file>
--out <file>` (or `review`, `check`), `<skill>` being the absolute path of the folder SKILL.md was loaded from
(`omp skill list --json`). Prompts and models: `codex-implementation.md`, `codex-review.md`, `codex-computer-use.md`.
- Start it with the bash tool as `async: true` (needs `async.enabled`, default on, `omp://settings.md`) and
  `timeout: 3600` (`omp://tools/bash.md`): it returns at once and the result arrives by itself, so there is
  no `resume` step. Start a wave's Codex rows in the same turn as its `tasks[]` batch; ownership rules are
  the same as for subagent rows.
- An `openai-codex/…` per-call model is not used: it would run in omp's loop without Codex's sandbox and
  computer-use plugins (inferred), its quality there is unmeasured, and `providers.openai-codex.daybreak`
  (default on) lets OpenAI use session content for training (`omp://settings.md`).

## Installing the skill for omp

omp ignores `~/.claude/skills` by default: foreign user-level roots are opt-in (`omp://skills.md`). One of:
- `enabledProviders: [claude]`: also loads Claude Code's user plugins and `~/.claude/CLAUDE.md` as a context
  file (`omp://settings.md`). Same-named skills from `~/.agents/skills` stay reachable as `agents/<name>`.
- A link to the skill's folder under `~/.agents/skills/`.
- `skills.customDirectories: [<folder that holds work-triage/>]`: scanning is non-recursive
  (`*/SKILL.md`); a custom-directory skill outranks a provider skill of the same name.

Check: `omp skill list --json` lists `work-triage` and its path (`omp://skills.md`). To test a working copy,
put `skills.customDirectories` in an overlay file and set `PI_CONFIG_FILES=<overlay>`; overlays outrank
project and global settings (`omp://settings.md`). On omp 18.20.3 a `--config` flag placed before a
subcommand such as `skill list` did not apply in a test; the variable did. With `enabledProviders: [claude]`
set, an installed copy appears beside the working copy as `claude/work-triage`, so the overlay also sets
`disabledProviders: [claude]`.

# Running a triaged plan in Claude Code

Mechanics verified 2026-11-13 against Claude Code 2.1.323 and its docs (`model-config`, `sub-agents`,
`skills`, `prompt-caching`). Prices, levels and sources: [facts.md](facts.md). Claude Code's "effort level"
is what the skill calls the level. The skill's frontmatter sets no `effort`, so the session's own level
applies while triaging. In omp read [harness-omp.md](harness-omp.md) instead.

## What Claude can and cannot switch

- Claude cannot type `/model` or `/effort`; those are the user's commands. Claude can choose a subagent's
  model and level, and a skill's frontmatter `effort` applies for the turn that loads it.
- So a row on the session's model at a different level runs either as a subagent with that model and
  level, or the user types `/effort <level>` at the row boundary (picker plus `s` keeps it to this
  session; a typed level becomes the saved default). Never log a row at a level nobody set.
- `ultrathink` typed by the user in the terminal can raise one turn to `xhigh`; inside a subagent prompt
  it is only a hint.
- In a swarm run, the session that drafted the plan may not match the orchestrator row. If it does,
  continue. If not, write plan and triage to `docs/plan.md` and give the user the command for the
  execution session:
  `claude --model <model> --effort <level> "Read docs/plan.md and start with row 1."`
  A fresh session costs less than switching a long conversation: a model switch re-reads the whole
  history uncached, and moving down from Fable drops its thinking.

## Mechanics (2.1.323)

| Where | How |
|---|---|
| Agent tool call (a subagent per row) | `model`: alias only (`sonnet`, `opus`, `fable`); `effort`: `low`…`max` (needs 2.1.292+) |
| Subagent definition `.claude/agents/<name>.md` | frontmatter `model:` (alias, full ID or `inherit`) and `effort:` |
| Skill or command frontmatter | `model:` / `effort:` apply for the rest of that turn only |
| Main session | `/model <x>` and `/effort <x>` typed with a value are saved as the new default; open the picker and press `s` for this session only. `max` is session-only unless set through `CLAUDE_CODE_EFFORT_LEVEL` |
| New terminal or script | `claude --model <x> --effort <y>`; headless: `claude -p --model <x> --effort <y> --output-format json`, actual model in `modelUsage` |
| Settings | `modelSettings.<model-id>.effortLevel` (`low`…`xhigh`); a top-level `effortLevel` in user settings is ignored for Opus 5.5 and later |
| Check what runs | `/tasks` shows model and level per subagent; `/effort status` the session level |

Level precedence, strongest first: `CLAUDE_CODE_EFFORT_LEVEL` env var > Agent-tool `effort` > subagent or
skill frontmatter > level picked in the session > `--effort` > settings > model default.

Subagent model precedence: Agent-tool `model` > definition `model:` > `CLAUDE_CODE_SUBAGENT_MODEL` > main
session model. A subagent on a different model than the session does not get the session's level ("On
another model, that level doesn't apply"), so always pass `effort`.

In Claude Code an alias of the parent's family runs the parent's version (`opus` under a parent on Opus 4.8
runs Opus 4.8); after a safety fallback, read the version in `/tasks` before the next wave [INFERENCE:
it combines the alias rule with "the main session stays on the fallback model"].

`opusplan` (Opus in plan mode, Sonnet for execution) still exists, cannot use Fable, and costs a cache miss
per toggle; Anthropic's Nov 2026 guidance says measure it before making it a default because it puts code
edits on Sonnet.

## Rows on another model: subagents

- Agent tool with `model: "sonnet" | "opus" | "fable"` and `effort: "<level>"`. Always pass both. Without
  `model` the subagent falls back to its definition, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the session
  model.
- The brief is self-contained: goal, files, scope (what not to touch), the check, the report format
  (a path plus a short summary), the tools and sources to use, and for secrets work the no-values rule. A
  vague delegation duplicates work or leaves gaps. It ends with a stop condition: the smallest change that
  passes the acceptance check, run that check, stop when it passes. Never "be certain", "be thorough" or
  "compare several approaches": raise the level instead ("max certainty" wording cost 4.13x output tokens
  on Sonnet 5 in Claude Code, "think hard" only 1.25–1.30x; one preregistered study).
- Subagents start with an empty cache. Batch tiny rows with their neighbours, or run them inline on the
  orchestrator.
- Subagents inherit the session's MCP tools, paid ones included, but cannot ask the user anything. Paid
  calls, saves in a web dashboard and other gated actions run in the main session.
- Whether a browser integration reaches a subagent is not established: signed-in browser work runs in the
  main session.

## Safety fallback

Fable 5.2 and Opus 5.5 re-run cyber-flagged requests on Opus 4.8 and biology-flagged ones on Opus 5;
Sonnet 5.5 re-runs cyber on Sonnet 5 and refuses biology.

- With `switchModelsOnFlag: false` in the user's settings, the main session pauses and asks, a flagged
  subagent fails with "Agent terminated early due to an API error", and a flagged `claude -p` run ends
  with a refusal.
- Without it, a flagged subagent silently re-runs on the fallback model and only its report comes back;
  the main session switches with a transcript notice and stays on the fallback model.
- On a fallback, that error or that refusal: never re-run the row on a lower model or with a reworded
  prompt that hides the topic. Tell the user which row and why, and mark it "not run on the triaged
  model". If the main session itself fell back, stop before the next row and offer a fresh session from
  `docs/plan.md`.

## Scripts and background runs

- `claude -p --model sonnet --effort low --output-format json "…"`; `modelUsage` in the result shows the
  model that actually ran.
- Fable rows never run as `claude -p` without the user's OK: there a Fable request that bills usage
  credits is charged without asking. In background sessions and agent-team teammates the credit prompt
  waits five minutes, then ends the turn without sending the request, so a Fable row there stalls unless
  the user is at the terminal.

## Settings that break routing

- `CLAUDE_CODE_EFFORT_LEVEL` set globally overrides every per-row level, subagents included.
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` makes Claude Code ignore the `model` Claude passes.
- A top-level `effortLevel` in user settings is ignored for Opus 5.5 and later; per-model defaults live
  in `modelSettings.<model-id>.effortLevel`.

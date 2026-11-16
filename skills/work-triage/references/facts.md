# Facts behind the triage (verified 2026-11-13)

Everything here is from Anthropic's own pages, fetched 2026-11-13 with Claude Code 2.1.323, except the
marked independent cross-check. Models and prices change: re-check the pages at the bottom before
trusting a number that is more than a few weeks old. Claude Code mechanics are in
[harness-claude-code.md](harness-claude-code.md), omp's in [harness-omp.md](harness-omp.md).

## The three models

| | Sonnet 5.5 | Opus 5.5 | Fable 5.2 |
|---|---|---|---|
| Claude Code alias / full ID | `sonnet` / `claude-sonnet-5-5` | `opus` / `claude-opus-5-5` | `fable` / `claude-fable-5-2` |
| Anthropic's positioning | "strongest at well-scoped everyday tasks" | "our strongest daily driver"; the default and recommended start | "the most ambitious, open-ended technical work"; Claude Code docs: Fable models "investigate before acting, and verify their work more often than smaller models" |
| Price in / out per MTok | $2 / $10 | $4 / $20 | $8 / $40 |
| Cache read per MTok | $0.10 | $0.20 | $0.20 |
| Context / max output | 1M / 128K | 1M / 128K | 1M / 128K |
| Latency | fast | moderate | moderate |
| Effort levels | low, medium, high, xhigh, max | same | same |
| Default effort in Claude Code | `medium` | `medium` | `medium` |
| Default effort on the API | `high` | `medium` | `high` |
| Thinking | adaptive, on by default | adaptive, always on | adaptive, always on |

Effort levels are calibrated per model: `high` on Sonnet is not the same amount of work as `high` on Opus.

## What effort does

- Effort controls how much work Claude does per turn: thinking, but also how many files it reads, how much
  it tests and verifies, and how far it goes before checking back. Lower effort asks for context sooner.
- Higher effort fixes failures from missed edge cases; it does not fix a wrong approach (Terminal-Bench 3.0
  failure analysis, "Spending your effort"). A wrong approach needs a stronger model or a better spec.
- Anthropic's level guide for Claude Code: `low` quick exchanges you review each time (sketch, rename);
  `medium` day-to-day work with a clear scope; `high` verification matters or edge cases are likely
  (bug in an existing codebase); `xhigh` "deeper reasoning at higher token spend"; `max` hard problems
  Claude works through alone, "may show diminishing returns and is prone to overthinking". The API
  effort page adds: `xhigh` for long-running agentic and coding tasks over ~30 minutes.
- Fable 5.2: "A turn can end before the work is done … more often at `low` and `medium` effort."
  The API guide says start Fable at `high`; most of its gain is already there.
- Sonnet 5.5 at `xhigh`/`max` may start its own extra review rounds (more time and tokens).

## Measured trade-offs (Anthropic-internal, "directional, not guarantees")

| Measurement | Result |
|---|---|
| Opus 5.5 on a SWE-bench Pro subset | `low` 87.4 % / $0.11 · `medium` 92.8 % / $0.21 · `high` 95.3 % / $0.29 · `xhigh` 96.7 % / $0.74 per task |
| Opus 5.5 `low` vs Sonnet 5.5 default | about the same share solved, Opus ~7 % more per solved task (one coding benchmark; on defect search Opus `low` scored 0.489 against Sonnet's 0.760) |
| Sonnet 5.5 `medium` vs its `high` | ~7 points lower on SWE-bench Pro; 62.7 % vs 77.8 % on an internal agentic-coding benchmark |
| Opus 5.5 `xhigh` vs Fable 5.2 `high` (SWE-bench Pro) | equal (96.5 % vs 96.3 %), Opus at a little over half the cost |
| FrontierCode 2.0 (frontier-hard) | Fable 5.2 `high` ≈ Opus 5.5 `max` for about half the cost per task |
| Defect search | Opus 5.5 `low` 34 points below `medium`; Fable 5.2 `low` only 4.3 below `high` |
| DeepResearch Bench II, default effort | Fable 5.2 cost 4.3× Sonnet 5.5 for no measurable gain, 2.9× Opus 5.5 for 1.9 points less |
| Checkable tasks | Opus 5.5, computed from recorded runs: `low`, then `high` on failures, $0.17 vs $0.29 per task at 96.4–97.5 % vs 94.8–95.8 %, triggered by the benchmark's hidden tests; with weaker checks the saving shrinks, and each failure doubles wall-clock time |
| Lead + workers on ~22M tokens of code | Opus 5.5 lead over Sonnet 5.5 workers ≈ same score, about a third cheaper than Opus alone, only on work larger than one context; within one context the lead's model alone at a lower level came out ahead (earlier models); Haiku 5.5 workers: −32 % cost, −4.2 points, "an alternative to lowering effort, not better" |

Reading: Fable pays where the task is frontier-hard or long; where Opus already saturates the task,
Fable mostly costs more. Sonnet holds up on scoped, checkable work and falls off on long agentic loops
and judgment.

What follows for the triage. On the Artificial Analysis Intelligence Index v4.3.2 (a general index, not a
coding benchmark) Sonnet 5.5 `xhigh` scored 52 at $2.74 per task (about $2.01 after the October
cache-price cut) against Opus 5.5 `high` 54 at $1.82; v5.0.1 keeps the score order (50 vs 51.8), cost not
re-checked; Terminal-Bench 4.0 at `max` points the same way ($35.95 vs $22.05 per solved task). Re-check
at each price or index change. So Sonnet above `high` is dominated by Opus `high`. From Anthropic: Opus
`low` lost 34 points against `medium` on the defect search (search and judgment suffer at `low`), and
Opus's system card shows its FrontierCode v1.1 score dipping above `medium` and mostly recovering at
`max`, because the grader penalises out-of-scope edits (bigger diffs). Test writing is not reserved for
Opus: only tests that are the sole check of a security row share that row's floor. No published evidence
exists on plan review by model, so the skill keeps plan and design reviews and the review at the join on
Opus 5.5 `high` (`wt-reviewer`).

## Limits, fallbacks, costs that are easy to miss

- **Usage plans.** On Max/Ultra/premium seats Fable may use at most 50 % of the weekly limit and drains it
  faster than other models; on Pro/Team standard Fable bills usage credits. In `claude -p` runs a Fable
  request that bills credits is charged without asking.
- **Safety fallbacks.** Fable 5.2 and Opus 5.5 re-run cybersecurity-flagged requests on Opus 4.8 and
  biology-flagged ones on Opus 5; Fable's safeguards "block most cybersecurity-related tasks". Sonnet 5.5
  re-runs cyber on Sonnet 5 and refuses biology. After a fallback the main session stays on the fallback
  model. In a subagent, "Switch automatically" (or no choice yet) silently re-runs the request on the
  fallback model and only the report comes back; "Ask each time" (`switchModelsOnFlag: false`) makes the
  subagent fail with "Agent terminated early due to an API error". Opus fell back on 10 % of
  Terminal-Bench 4.0 trials in Anthropic's own run, so this is not rare on security-adjacent work.
- **Switching models** costs the whole prompt cache (the first turn on the new model re-reads the full
  history uncached). Moving down a tier also loses the earlier thinking: a model never reads thinking
  blocks of a model above it, and anything after Fable 5.2 loses Fable's reasoning.
- **Changing effort** keeps the cache on these three models with an API key or subscription (not on
  Bedrock, Agent Platform, a gateway, HIPAA setups or with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`).
- **Cache lifetime while a parent waits.** On an API key, a parent that waits on a wave for more than
  5 minutes rewrites its whole context on the next turn (150k on Opus 5.5 ≈ $0.75). A subscription's main
  conversation keeps its cache for 1 hour; subagents get 5 minutes either way.
- **Subagents** start with an empty cache (5-minute TTL). A step of 1–2 turns stays with whoever holds its
  context; a step that inline would re-read a large context over 3 or more turns, or carry much read
  material through the rest of the run, goes to a subagent, provided the child needs no more than about 3x
  the inline work.
- **Multi-agent cost.** A multi-agent run costs several times one agent: native subagent concurrency used
  1.41–3.31x the tokens of sequential mode on the same coding tasks; Anthropic's 3–10x is "in our testing";
  its 15x is against chat, about 3.75x one agent, on research tasks.

## Codex (codex-cli 0.166.0, verified 2026-11-13)

OpenAI's model guide for Codex (https://developers.openai.com/codex/models) and the local Codex models
cache:

| Model | OpenAI's positioning | Default effort | Levels |
|---|---|---|---|
| `gpt-6-astra` | "most capable model for complex work across code, apps, and research"; "hardest end-to-end work" | `low` ("Start with Light for Astra") | low … max, ultra |
| `gpt-6.1-sol` | "Near-Astra performance for complex work at a lower cost than Astra"; "repeated, long-running work"; the recommended Codex model on paid plans | `medium` | low … max, ultra |
| `gpt-6.1-terra` | "fast, efficient model for clear writing, visual understanding, and computer use" | `low` | low … max, ultra |
| `gpt-6-luna` | "clear, repeatable tasks … extraction, classification, transformation" | `medium` ("Start with High for Luna") | low … max |

- `max` gives one task more reasoning time; `ultra` splits work across Codex subagents. "Most tasks do
  not need Max or Ultra."
- The user's Codex config (`~/.codex/config.toml`) may set `gpt-6-astra` at `high` as the default; then a
  Codex call without `-m` and `-c model_reasoning_effort=…` runs on the most expensive setting.
- Codex usage counts against the ChatGPT plan, not Claude's limits. `codex review` has no `-m`; use
  `-c model="…"`.
- Re-check: https://developers.openai.com/codex/models, `codex exec --help`.

## Re-check

- Models and prices: https://platform.claude.com/docs/en/about-claude/models/overview and each model's
  overview page (`/docs/en/models/<model>/overview`)
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort
- Cost measurements: https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence
- Model choice: https://claude.dev/blog/which-claude-model-should-you-build-with/ (2026-11-09)
- Effort in practice: https://claude.dev/blog/spending-your-effort/ and
  https://claude.com/resources/articles/claude-model-and-effort-level-in-claude-code
- Claude Code: https://code.claude.com/docs/en/model-config, `/sub-agents`, `/skills`, `/prompt-caching`
- Plans: https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
- Local: `claude --version`, `claude --help | grep -E 'effort|model'`

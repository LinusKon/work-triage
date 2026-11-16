# Calibration on the author's own tasks (2026-11-13)

Benchmark: tasks, runner and raw results (`results/runs.jsonl`, `results/codex.jsonl`) are kept with the
skill's source repository. 271 runs, $94.88 of Claude usage (list price as reported
by `claude -p`), Codex runs on the ChatGPT plan. Each run: a fresh copy of a small Python project,
`claude -p` or `codex exec` with file and python tools only, then hidden tests the agent never saw.

## The tasks

- **T1–T8, spec'd:** rename across ~20 files with traps, a rate limiter from a spec, a bug the report
  blames on the wrong module, HMAC webhook verification with replay protection, a root cause across three
  modules (cache keys, shared mutable cache objects), a CSV contract with many edge cases, a scheduler
  with exact cycle reporting and 200k-task inputs, and the triage itself (this skill on three test plans,
  graded by fixed rules).
- **T9–T13, hard:** a support-ticket bug hunt where the ticket's suspect is real but not the main cause
  (time zones plus a mis-keyed cache), thread races in a job queue under stress, undo/redo designed from
  a vague request, an O(n²) merge made fast with byte-identical Unicode semantics, and a 15-module API
  migration with three documented behaviour changes and no tests given.

## Results

| Config | Runs | All hidden tests passed | Mean cost per run | Mean time |
|---|---|---|---|---|
| Sonnet 5.5 `low` | 45 | 42 (93 %) | $0.11 | 42 s |
| Sonnet 5.5 `medium` | 45 | 43 (96 %) | $0.13 | 50 s |
| Sonnet 5.5 `high` | 23 | 23 | $0.19 | 75 s |
| Opus 5.5 `low` | 45 | 45 | $0.25 | 60 s |
| Opus 5.5 `medium` | 45 | 45 | $0.35 | 91 s |
| Opus 5.5 `high` | 23 | 23 | $0.41 | 116 s |
| Opus 5.5 `xhigh` | 13 | 13 | $0.96 | 288 s |
| Fable 5.2 `medium` | 13 | 13 | $0.86 | 119 s |
| Fable 5.2 `high` | 13 | 13 | $1.49 | 234 s |
| Codex `gpt-6-luna` `high` | 36 | 27 (75 %) | ChatGPT plan | 108 s |
| Codex `gpt-6.1-sol` `medium` | 36 | 36 | ChatGPT plan | 107 s |
| Codex `gpt-6-astra` `high` | 12 | 12 | ChatGPT plan | 160 s |

Every config ran every task at least once; the cheap ones ran 3–6 times, so the means mix tasks in
slightly different proportions. Per task the order is the same: Opus `high` cost 1.4–2.4× Opus `low`
(3.3× on the triage task).

Where the cheap settings failed:
- **Sonnet `low` and `medium` on T5** (root cause across three modules): 4 of 6 runs each. All four
  misses were the same edge case: the cache handed callers its own mutable object, so one caller could
  change what the next one got. Sonnet `high` and Opus `low`, `medium`, `high` passed all 6 runs each
  (Opus `xhigh` and Fable: 1 run each, passed).
- **Sonnet `low` on T12**: once left the slow algorithm in place (the timing tests failed).
- **gpt-6-luna**: missed edge cases in the security task (T4, 2 of 3 runs), the cache task (T5, 3 of 3),
  the CSV contract (T6, 3 of 3) and the design task (T11, 1 of 3).
- The triage task (T8) passed on every setting down to Sonnet `low` after two grader fixes; Opus `low`
  and `medium` and Sonnet `medium` 3 of 3 each.

## What the skill takes from it

1. For a bounded coding step (one repo, one session, a goal that can be checked), more than Sonnet `high`
   or Opus `low` bought nothing on these tasks, including the hard ones. Opus `high` cost 1.6× Opus `low`,
   Opus `xhigh` 3.8×, Fable `high` 6× for the same result, and took 2–5× as long.
2. Sonnet `medium` is right where the step chooses no approach; once the step has to find a cause or
   choose a design, Sonnet `high` (or Opus `low` inline) is the cheapest setting that did not miss.
3. `xhigh` and Fable are escalations, not defaults: no task here needed them.
4. Codex: `gpt-6.1-sol` `medium` is the bulk lane (36 of 36). `gpt-6-luna` only for transforms with an
   obvious result and a check that stands alone, never for security or edge-case work. `gpt-6-astra`
   `high` passed everything but was the slowest; keep it for second opinions and as the escalation.
5. Judge a triage against two fixed plans on the same tasks: every row on Opus 5.5 `medium` (always-mid)
   and every row on Opus 5.5 `high` (best single). It earns its place only by beating always-mid on cost
   at the same pass rate.
6. Spawning has its own price (2026-11-16, one run each, Opus 5.5 `high` parent, a six-step stdlib Python plan:
   interface, three small modules, a CLI, a README): the parent alone, in order, cost $0.50 in 2 minutes (35 own
   tests passing); the 2.0.1 triage with three Codex rows, a Sonnet row and an Opus review cost $2.38 Claude plus
   81k Codex tokens in 11 minutes, $1.98 of it in the parent; every row as an Opus `medium` subagent cost $2.85.
   Briefs, waits and reading results cost more than the rows saved, hence "size first" in SKILL.md section 1.
   One task, one run per setup, own tests only: a direction, not a measurement of quality.
7. Skill against no skill (2026-11-16, 28 runs on four tasks with hidden acceptance tests and blind reviews,
   `study/results.md` in the source repository): every run passed its hidden tests. 2.1.0 cost a median $1.19
   against $0.67 without the skill; it was cheaper only where the base session split small work into
   subagents (task D, −36 %). Costs came from reading the skill, separate `xhigh` and `high` floor reviews, and
   output tokens; 2.2.0 answers with a lean core, one floor review and the "work economically" rules.
8. Rounds 2 and 3 (2026-11-16, 51 more runs, three of the seven tasks held out): with equal hidden-test results,
   2.2.0 cost −10 % in total and +6 % in the median against no skill at Opus `high`; 2.3.0 at Opus `medium` cost
   −14 % in the median against no skill at `high` and +37 % against no skill at `medium`. Lowering the session to
   `medium` alone saved 37 % but drew major review findings in 2 of 9 runs (float overflow in a mean, symlink
   races), against 0 of 9 at `high`. One Sonnet worker for a whole small task cost $0.12–0.30, less than the
   parent's overhead around it. Hence 2.4.0: the head stays at `high`, small work is never delegated, and the
   hardening pass names those defect kinds. Large builds with many workers are not measured yet.

## What it does not show

- Single-session tasks of up to ~20 files with a checkable goal. No multi-hour unattended runs, no work
  across several services, no product or taste judgment, no production systems. The floors for those
  stay as the published evidence sets them (facts.md).
- Hidden tests find what they test. A security floor guards against what nobody wrote a test for, so
  the security floors stay even though Sonnet `medium` passed T4.
- Small samples: 3–6 runs per cell for the cheap settings, 1 for the expensive ones. A 1-in-3 miss rate
  would often not show in one run.

Re-run after a model release: `python3 run.py --configs <…> --reps 3 --budget-usd <cap>` in the
calibration folder, then `python3 analyze.py`.

# The calibration benchmark and the study

Two bodies of evidence stand behind this skill. The **calibration benchmark** (2026-11-13) ran single settings of
model and level on small tasks, one session per run, to find the cheapest setting that passes. The **study**
(2026-11-16, 95 runs in six rounds) ran sessions with the skill against sessions without it on tasks of its own;
its numbers are in items 6 to 8 below. Both judge a run by hidden acceptance tests: tests the agent never saw.

Calibration benchmark: 271 runs, $94.88 of Claude usage (list price as reported by `claude -p`), Codex runs on
the ChatGPT plan. Each run: a fresh copy of a small Python project, `claude -p` or `codex exec` with file and
python tools only, then hidden tests the agent never saw.

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

## What the skill takes from them

1. For a bounded coding step (one repo, one session, a goal that can be checked), more than Sonnet `high`
   or Opus `low` bought nothing on these tasks, including the hard ones. Opus `high` cost 1.6× Opus `low`,
   Opus `xhigh` 3.8×, Fable `high` 6× for the same result, and took 2–5× as long.
2. Sonnet `medium` is right where the step chooses no approach; once the step has to find a cause or
   choose a design, Sonnet `high` (or Opus `low` inline) is the cheapest setting that did not miss.
3. `xhigh` and Fable are escalations, not defaults: no task here needed them.
4. Codex: `gpt-6.1-sol` `medium` is the bulk lane (36 of 36). `gpt-6-luna` only for transforms with an
   obvious result and a check that stands alone, never for security or edge-case work. `gpt-6-astra`
   `high` passed everything but was the slowest; keep it for second opinions the user asks for.
5. Judge a triage against two fixed plans on the same tasks: every row on Opus 5.5 `medium` (always-mid)
   and every row on Opus 5.5 `high` (best single). It earns its place only by beating always-mid on cost
   at the same pass rate.
6. **Study, small tasks** (hidden acceptance tests, blind reviews; medians per run, total cost unless marked).
   Round 1 (skill 2.1): $1.38 against $0.67 without the skill ($1.19 against $0.67 in Claude dollars only).
   Costs came from reading the skill, separate `xhigh` and `high` floor reviews, and output tokens. Round 2
   (skill 2.2, a lean core, one floor review and the "work economically" rules): $0.78 against $0.74.
7. **Study, the level of the parent** (the main session the user talks to). Round 3 (skill 2.3 with the parent at
   `medium`, new small tasks): $0.50 against $0.77 for no skill at `high` and $0.37 for no skill at `medium`.
   Lowering the level alone cut total cost by 52 % (37 % in Claude dollars). Sessions at `medium` drew major
   review findings in 2 of 9 runs (3 findings, among them float overflow in a mean and symlink races; two were
   security, both in one run); sessions at `high` in 0 of 9. Hence 2.4: the parent stays at `high`, small work
   is not delegated, and the hardening pass names those defect kinds.
8. **Study, large builds.** Round 5 (skill 2.5, build H): median $4.11 against $6.06, −32.2 % (exact one-sided
   rank-sum p = 0.0079), hidden test 5/5 and 5/5, major defects after blind grading 15 against 14. Round 6
   (skill 2.6, build I): median $4.58 against $7.76, −41.1 %, p = 0.0079, hidden test 5/5 and 5/5, major defects
   17 against 27 (Python 3.12). Hence section 2 of SKILL.md: a parent at `high`, few batched workers, one review.
   Both ran in omp 18.21.0. Round 7 measured build I again in omp 18.22.0, which by itself runs subagents at lower
   levels: $4.25 against $5.91 (−28.0 %, p = 0.0159) with Codex named in the prompt, $4.28 against $6.43 (−33.5 %,
   p = 0.0040) with none, hidden test 5/5 everywhere, no defects graded. The saving belongs to a harness version;
   measure again after an update.
9. **Study, design built in code** (2026-11-17; six briefs: title sequence, landing page, 3D scene, logo sting,
   pricing page, and launch copy; three runs per setup; outputs ranked blind and marked "would you hand it to a
   client" by two model judges, Opus 5.5 `high` and `gpt-6-astra` `high`; no person judged). Usable on the five
   design briefs (both judges yes or fix), of 15 outputs: Sonnet `high` 13, Opus `medium` 8, Opus `high` 14,
   Fable `high` 15. Median cost per run by brief: Sonnet `high` $0.12 to $0.62, Opus `medium` $0.37 to $1.72, Opus
   `high` $0.61 to $2.72, Fable `high` $2.53 to $12.79. Mean rank over all 18 screens (1 = best of five): Fable
   1.33 and 1.94 (Opus judge, astra judge), Opus `high` 2.83 and 2.33, Sonnet `high` 3.67 and 3.78, Opus `medium`
   4.44 and 4.17. The second round fixed its bars in advance: "Sonnet `high` first" held (6 of 6 usable), "never
   Opus `medium`" held, "Opus `high` is needed to be right the first time" did not (Sonnet was as often usable),
   "Fable directs, Sonnet builds" did not (62 % of Fable's cost against a bar of 60 %, and one judge ranked it a
   full place behind). The two judges agree only moderately (Kendall tau-b 0.65 and 0.37), and the copy brief
   could not be read: one judge rejected most copy of every setup for claims beyond the fact sheet.

## What the calibration benchmark does not show

- Single-session tasks of up to ~20 files with a checkable goal. No multi-hour unattended runs, no work
  across several services, no product or taste judgment, no production systems. The floors for those
  stay as the published evidence sets them (facts.md).
- Hidden tests find what they test. A security floor guards against what nobody wrote a test for, so
  the security floors stay even though Sonnet `medium` passed T4.
- Small samples: 3–6 runs per cell for the cheap settings, 1 for the expensive ones. A 1-in-3 miss rate
  would often not show in one run.

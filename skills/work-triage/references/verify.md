# Verify: reviews and fix rounds

Detail behind `spawn.md` section "4. Verify: reviews and fix rounds". Waves and joins: `references/schedule.md`;
chains: `references/sequential.md`; running a Codex review: `references/codex-review.md`. The parent (the main
session the user talks to) plans the reviews and decides what gets fixed.

## Order of checks

1. **Automatic check first** (tests, build, typecheck, a selftest, a diff against a known output), because a
   near-perfect verifier is the strongest signal an agent gets and costs no model call.
2. **Model review second**, only for what the check cannot see (spec fit, design, a merge of several rows),
   because a review with nothing to compare against does not converge.
3. **The user last**, at gates and before anything irreversible, paid or outward, because a late fix costs most there.

## Where reviews go

| Review point | Who | Rounds |
|---|---|---|
| Leaf row with a check that stands alone | no review; the parent reads the check output | — |
| Join: the merged result of several rows | one `wt-reviewer` review against the contract and the hardening list, after the consumers | one fix round |
| Security or secrets rows | one `wt-reviewer` review scoped to those files and their tests, instead of the join review for them; `xhigh` only when it finds a major issue or no test covers the risky path | one fix round |
| Other floor row (interface, migration or irreversible prepare) | covered by the one review before its gate (the join review where there is one) | — |
| Before anything irreversible, paid or outward | a prepare row, then the gate (`Run as` `user`) | — |

- **Reading a row is not a review.** Before rows start that build on a row, the parent accepts it: it reads the
  output and the check. That costs no review row, because one wrong assumption there would send every later row
  the wrong way and a reading catches it; "reviewed at 8" in a `Check` cell means the later join review.
- A row that starts after several rows of one wave (read `Starts after`) is a **join**. Review the merged result
  there, once, after the consumers, because the merge is the first point where rows whose own checks passed can
  still fail together. Shared state was the largest failure class of coding-agent teams (33.2 %, CAID in the
  Evidence table below), and one check at the join sees all of it.
- **No other review by default.** No final review before the gate and no cross-family review are added, because
  the join review already sees the merged result. A Codex review runs only when the user asks for one.
- The plan header states the count (`Reviews: 1, at 8. Fix rounds: 1.`), because reviews added per step become
  the default and most of them find nothing. A review row has "review" among the first two words of its `Row`
  cell ("Review …", "Join review …", "Security review …"), so the count can be checked.

## Who reviews

- **Always a fresh context** (a `wt-reviewer` subagent that never saw the author's conversation), given the spec
  and the artefact, not the author's summary, because a reviewer who reads the author's reasoning is swayed by it.
- **The join review** is `wt-reviewer` (Opus 5.5 `high`). The reviewer need not match the author's rung: the fresh
  context finds the misses. A Codex review or second opinion (`gpt-6-astra` `high`, `scripts/codex_row.sh review`)
  happens only when the user asks for one, because it is the most expensive model and the evidence for
  cross-family review is indirect.
- **Security and secrets rows** are never in a Codex review's scope (list the rows or paths it skips), because
  their floor keeps them with Claude: one `wt-reviewer` review, `xhigh` only on the conditions above.
- **One perspective per review:** the join review checks the merged result against the contract, the security
  review only the floor files and their tests, because directed reviews of small diffs find more than broad ones.

## Reviewer prompt (template)

```text
Review <row numbers, or "the merged result of rows N-M"> against the spec below.
Spec: <path to the spec, interface or contract, or the row's acceptance criteria>
Artefacts: <file paths, or the diff: base branch or commit range>
Checks already run: <command and output, or "none">
Report only gaps that affect correctness; skip style, naming and refactors.
Per finding: severity (blocker / major / minor), file:line, what breaks, and evidence (a command and
its output, or the line that contradicts the spec). No finding without evidence.
If nothing is blocker or major, say so in one line.
```

"Correctness only" and the evidence demand exist because a reviewer asked to find problems always finds
something, and fixing every finding adds layers nobody asked for.

## Fix rounds

- **The parent decides what gets fixed**, not the reviewer, because it holds the spec, the scope and the user's
  intent: it drops out-of-scope, style and unproven findings; a blocker it cannot judge goes to the user.
- **One fix round is planned** per review point (in a chain, per link), and the header's `Fix rounds` counts
  exactly that, because the first round carries most of the gain.
- **A failing check after the fix round follows the failure ladder** in `spawn.md` ("During the run"), not more
  critique rounds: back to the author once, then a small fix by the parent or the row one rung up. A second round
  driven by model critique alone made results worse in published measurements (math and QA, 2023–24 models; no
  study of coding fix rounds).
- **After two failed rounds on one row the parent stops and tells the user** (what failed, what was tried, the
  evidence), because a third round without new information repeats the second.

## What "done" contains

Every row's report holds the check it ran (command, exit code, the relevant output, or "no check exists"), the
artefact paths or diff within its owned files, and what is not done or departs from the spec. "Tests pass" alone
is not done, because agents end turns with items still open; the parent re-runs or spot-checks the check when it
accepts the row.

## What a join review looks for

| Failure | Sign at the join | Prevented by |
|---|---|---|
| Duplicated work | two rows built the same helper or covered the same case | owned files per row before launch |
| Conflicting edits | different names, types or conventions for one thing; merge conflicts | one writer per file; full test suite after the merge |
| Unverified done | a claimed pass the parent cannot reproduce | re-running the row's check at the join |
| Error carried into the next wave | later rows built on a wrong assumption or broken interface | the parent accepting the upstream row before the next wave |
| Lossy hand-off | the summary says what the artefact does not | the reviewer reads artefacts, not summaries |

## What not to review

- **Leaf rows with a check that stands alone**: the check covers the risk and a review there mostly finds nothing.
- **Links of a chain**: their check is each link's end state (plus the user's approval where a link is paid),
  because the next link inspects the output anyway and a sequence gains nothing from a swarm review.
- **Tiny steps and trivial plans**, because coordination costs more than a single agent's miss.

## Evidence

| Source | What it supports |
|---|---|
| Kim et al. (Google/MIT), https://arxiv.org/abs/2512.08296 | independent agents wasted 17.2x, centrally coordinated ones 4.4x extra trace-level work on coordination failures; the task-level error effect was ≈1.1–1.3x; every multi-agent variant lost on SWE-bench Verified (−2.1 to −14.9 %); a post-merge review was not tested |
| Concurrent-agent failure taxonomy, https://arxiv.org/html/2610.10263v1; CAID, https://arxiv.org/html/2603.21489v2 | shared state was the largest failure class (33.2 %); a manager review per merge round raised pass rate 55.1→60.2 % at +64 % runtime (one study) |
| MAST taxonomy, https://arxiv.org/abs/2503.13657 | final-stage low-level checks alone are inadequate; premature termination and missing verification are common |
| Boehm and Basili, https://www.cs.umd.edu/~basili/publications/journals/J81.pdf | defects cluster; late fixes cost more; directed reviews find more (transfer to model swarms untested) |
| Cisco case study, https://static1.smartbear.co/support/media/resources/cc/book/code-review-cisco-case-study.pdf | 61% of reviews found no defect (vendor-run, observational) |
| Anthropic, https://www.anthropic.com/research/building-effective-agents | ground truth per step, gates, stopping conditions |
| Anthropic, https://www.anthropic.com/research/multi-agent-research-system | end-state checkpoints, artefacts as files, compounding errors |
| Anthropic, https://www.anthropic.com/research/building-c-compiler | the verifier must be nearly perfect; a CI gate stopped regressions |
| Claude Code docs, https://code.claude.com/docs/en/best-practices | fresh-context review, review against a spec, skip style, show the command run |
| Self-Refine https://arxiv.org/abs/2303.17651, CRITIC https://arxiv.org/abs/2305.11738, Huang et al. https://arxiv.org/abs/2310.01798, Kamoi et al. https://arxiv.org/abs/2406.01297 | gains sit in round one; without external feedback later rounds stall or degrade |
| Panickssery et al., https://arxiv.org/abs/2404.13076; CriticGPT, https://arxiv.org/abs/2407.00215 | model judges prefer their own output; trained critics find bugs and hallucinate some |
| Cognition, https://cognition.com/blog/multi-agents-working | separate coder and reviewer contexts, Claude and GPT together (opinion; figures without a control) |
| Codex docs, https://learn.chatgpt.com/docs/agent-configuration/subagents | reviewers split by focus, `high` reasoning for reviewers |

Untested: no study compares a fresh-context same-model review with a cross-family one, and no source gives a
review's token cost relative to the work it reviews; the first runs log it.

# Verify: reviews and fix rounds

Detail behind `spawn.md` section "4. Verify: reviews and fix rounds". Waves and joins: `references/schedule.md`;
chains: `references/sequential.md`; running a Codex review: `references/codex-review.md`.

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
| Join: the merged result of several rows | one fresh-context review against the spec, after the consumers | one fix round |
| Security or secrets row | one review covering both, Opus 5.5 `high`, scoped to the floor files and their tests; `xhigh` only as escalation | one fix round |
| Other floor row (interface, migration or irreversible prepare) | covered by the join or final review before its gate; may be cross-family | — |
| Final integration | cross-family (below); it replaces the same-family review | one fix round |
| Before anything irreversible, paid or outward | a prepare row, then the gate (`Run as` `user`) | — |

- **Acceptance is not review.** Before rows start that build on a row, the parent accepts it: reads the output
  and the check. That costs no review row, because one wrong assumption there would send every later row the
  wrong way and a reading catches it; "reviewed at 10" in a `Check` cell means the later join review.
- A row that starts after several rows of one wave (read `Starts after`) is a **join**: review the merged result there, once,
  after the consumers, because the merge is the first point where rows whose own checks passed can still fail together (shared
  state was the largest failure class of coding-agent teams, 33.2 %) and one check there sees all of it (Evidence: CAID).
- A **final review** is planned when the change has two or more writing rows and ends in a gate (a push, a PR, a run on real data): it is the
  last review row before that gate, because that is the last cheap point to catch an integration fault.
- The plan header states the count (`Reviews: 2, at 10 and 11. Fix rounds: 1.`), because reviews added per step
  become the default and most of them find nothing. A review row has "review" among the first two words of its
  `Row` cell ("Review …", "Final review …", "Join review …", "Security review …"), so the count can be checked.

## Who reviews

- **Always a fresh context** (a subagent or Codex run that never saw the author's conversation), given the spec
  and the artefact, not the author's summary, because a reviewer who reads the author's reasoning is swayed by it.
- **Join and final reviews**: Opus 5.5 `high` or `gpt-6-astra` `high`. The final review is cross-family: Claude's
  work → `gpt-6-astra` `high` (`scripts/codex_row.sh review`); Codex's work → Opus 5.5 `high`; mixed work → the
  family that wrote less of it. Only there, because the evidence for cross-family review is indirect and it
  costs a second harness. The reviewer need not match the author's rung: the fresh context finds the misses.
- **Security and secrets rows** are never in a Codex review's scope, the final one included (list the rows or
  paths it skips), because their floor keeps them with Claude: one Opus 5.5 `high` review, `xhigh` on escalation.
- **One perspective per reviewer** on critical rows (security, tests, spec fit) and small slices, because directed
  reviews of small diffs find more than broad ones.

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
- **A second only while a mechanical check still fails**, because a second round driven by model critique alone made
  results worse in published measurements (math and QA, 2023–24 models; no study of coding fix rounds). A row's own
  failed check escalates by `spawn.md`'s ladder ("During the run"; `fails twice → gpt-6-astra high`), not by more rounds.
- **After two rounds the parent stops and reports to the user** (what failed, what was tried, the evidence),
  because a third round without new information repeats the second.

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

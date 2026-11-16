# Spawning rows: table, rungs, schedule, reviews

Read this only when the work is orchestrated (SKILL.md sections 1 and 2). Solo plans need none of it.

## Terms

| Term | Meaning |
|---|---|
| omp's words | used as omp defines them: subagent, agent type, `tasks[]` batch, per-call `model`, model selector (`provider/model-id:level`), thinking level (Claude Code: effort level), allow-list, parent, integration owner |
| row | one outcome with one check, one executor, one set of owned files or outputs |
| level | the thinking level a row runs at; for Codex rows its reasoning effort |
| coupled | two rows that touch the same file or component, where one needs the other's result, design or API, that share a rename, or where one refines the other |
| wave | rows with no unfinished dependency, spawned as one `tasks[]` batch |
| chain | the path of artefact dependencies: link n needs the artefact of link n-1; a link may also have further predecessors (a tool it uses) and successors (a check of its result) |
| join | the point where the outputs of several rows are merged or a later wave starts to build on them |
| swarm run | a plan without a chain the parent must run (paid or gated links) that has a wave of six or more rows, or three or more waves of two or more rows each |
| floor | the lowest model and level a row may get because of what it touches |
| gate | an approval only the user gives |
| interface | what other code or people depend on: routes and payloads, config keys, schemas, file formats, CLI flags, exported signatures, prompts other tools consume. Deciding one is a floor; carrying a decided change to its call sites is not |
| a check that stands alone | an automatic check that fails if the row is wrong in the way that matters (a test that fails on the old code, a type check plus a grep count), named in the brief before the row runs; tests the row writes for itself count only once the parent has read them; a row's own claim never counts; "it runs" is not one |
| tiny step | a few tool calls on files already in context |
| unattended | a row that works more than ~30 minutes with no check and nobody reading its output; a subagent whose report the parent reads is not |

## 1. Cut the work into rows

- One outcome, one check (a test, a build, a file to inspect, a number that matches); keep the plan's step numbers.
  `#` is always a whole number: merged steps keep the lowest number, rows split off or added take the next free
  numbers after the plan's last step (never `8a`, `2b` or `1–5`), so a scorer and `Starts after` can read them.
- Merge tiny steps that share context; split off the part that needs a floor ("write the migration" / "run it").
- A bounded single-issue change (one bug, one feature in one area) is one row for one agent, not a wave of writers;
  split into parallel rows only where the pieces are independent and each is large (repository-scale modules,
  breadth-first research), and expect mixed gains even there.
- A gated action becomes three rows: prepare, the `user` gate, run and verify (paid chain links: SKILL.md floors).

## 2. Decide: model and level

**Model = how capable:** raise it for judgment, an approach nobody wrote down, an unfamiliar domain; full context, a
real attempt, still wrong means it "didn't know". **Level = how thorough:** files read, tests run, time before
checking back; it fixes missed edge cases, never a wrong approach; a skipped file or test means it "didn't try".

Signals, in this order: (1) floor; (2) a check that stands alone; (3) does the row choose an approach, or are what,
where and how to check written down; (4) taste or judgment across parts of the system; (5) blast radius and
reversibility; (6) how much it must read; (7) how many later rows build on it. There is no default model: a row that
earns a spawn (SKILL.md section 1) gets the **lowest rung whose conditions it meets**, after floors, in the table's
order: Codex first for code, then the Claude rungs, cheapest first ([calibration.md](calibration.md) has the
measured runs). Rows that earn no spawn stay in the parent.

| Rung | The row |
|---|---|
| Codex `gpt-6.1-sol` `medium` (`high` with dense edge cases) | bounded implementation in one repo, a check that stands alone, no floor, no taste; a bug in existing code with a test counts. **First choice** for a spawned code row: a Claude row here names why (Codex unavailable, a floor) |
| Sonnet 5.5 `medium` | chooses no approach; a mistake is cheap to spot; reversible; no floor, no taste: search, log reading, transforms with a count or schema check, web research with links, moving text |
| Sonnet 5.5 `high`, or Opus 5.5 `low` | bounded coding with a check when Codex is out; Opus `low` only as a `parent` row |
| Opus 5.5 `medium` | judgment or taste: concepts, copy, UI polish, prompts for image and video models, documents from more sources than the parent checks |
| Opus 5.5 `high` | the session's default; floors (SKILL.md section 3); judgment with no check; a row three or more later rows build on, with no check |
| Opus 5.5 `xhigh` | edge-case-dense work no check covers (parsers, sanitisers, concurrency, billing, migration scripts on real data); a security review that escalated. Never a first attempt where a check exists |
| Fable 5.2 (`high` alone, `medium` steered) | only under SKILL.md section 2's condition: Opus `xhigh` failed with full context on cross-system architecture or root cause, or frontier-hard work beyond one context. Never security: its safeguards block most cyber tasks |

Doubt goes into `Escalate if`, not into the rung. Rows a floor binds to the parent (production, paid runs, gated
scripts, the links of a chain) run at the parent's model and level; that is not lifting. Every other row that differs
from the parent runs as a subagent or Codex row. Never Sonnet above `high`; `max` is not planned.

**Codex scope.** Besides the first rung: `gpt-6.1-sol` failed at `medium` and `high`, or the user names Codex →
`gpt-6-astra` `high`; cross-family review or second opinion → `gpt-6-astra` `high`; local app checks without login
(browser, simulator, screenshots) → `gpt-6.1-terra` `medium`; `gpt-6-luna` `high` only when the user names it, never
on security or edge cases. Pass model and level explicitly; the CLI's default is the most expensive. Never Codex:
security, secrets, production, paid runs, gates; signed-in web; taste, image and video prompts, plans and designs.
Codex never commits, pushes, deploys or edits global config; mechanics: `codex-*.md` here and `scripts/codex_row.sh`.

## 3. Schedule: waves and chains

1. **Couple.** Rows coupled through a shared file, component, rename or refinement merge into one row; rows coupled
   through a result, design or API get `Starts after`. Coupling through an interface alone ends once the parent has
   written the contract, so such rows may share a wave.
2. **Contracts first:** the parent writes what rows share (terms, interfaces, names, formats) into the `context`.
3. **Waves:** every row whose `Starts after` is done, as one `tasks[]` batch of at most 15 rows; Codex rows start in
   the same turn. A row never spawns a wave of its own.
4. **Ownership:** every row has `Owns`; one writer per file. Rows in a wave with other writers skip builds, linters
   and test suites that touch shared state; the integration owner runs them once after the wave.
5. **Preflight** before a wave: each model has a role entry and is on the allow-list.
6. **Level check** after the first spawn of the run and of each new model, and 7. **rows added mid-run**: During the run.
8. **Follow-ups:** the planned fix round goes to the author, which keeps its context; other new work is a fresh row.
9. **Chains** are detected here and run as Chains says. Details: [schedule.md](schedule.md).

## 4. Verify: reviews and fix rounds

| Review point | Who | Rounds |
|---|---|---|
| Leaf row with a check that stands alone | no review; the parent reads the check output | — |
| Join that a later wave builds on | one review of the merged result against the spec, Opus 5.5 `high` or `gpt-6-astra` `high` | one fix round |
| Other floor rows (interface, migration or irreversible prepare) | the join or final review before their gate covers them, cross-family allowed; none of their own | — |
| Security or secrets row | one review by Opus 5.5 `high` covering both, scoped to the floor files and their tests (SKILL.md section 4); `xhigh` only as escalation; never in a Codex review's scope, the final one included | one fix round |
| Final integration | cross-family: Claude's work → `gpt-6-astra` `high`, Codex's work → Opus `high`; replaces the same-family review | one fix round |
| Before anything irreversible, paid or outward | a prepare row, then the gate | — |

Order: an automatic check, then a fresh-context model review for what it cannot cover, then the user. Before rows
that build on a row start, the parent accepts it (reads its output and check): no review row; "reviewed at 10" in a
`Check` cell names the later join review. Reviews and fix rounds are stated up front, only at these points. "Done"
means evidence: the command and its output, or the artefact path. Reviewer prompt: [verify.md](verify.md).

## Orchestrator

- **Swarm run:** the parent stays at its model and level (Opus 5.5 `high` by default): plans, triages, writes the
  contracts rows share (interface decisions too), integrates, decides at joins, runs floor-bound parent rows; no
  implementation, research or writing. The saving comes from the workers' rungs and from batching small rows into
  few workers (SKILL.md section 2). Fable in Opus's place as orchestrator cost 19 % more for about the same score
  (Anthropic's model-choice guidance).
- **Not a swarm run,** a plan on a chain the parent runs included: the session keeps its model and level and asks
  for no switch. The size of the plan, not its shape, picks the form (The plan table).
- **One model per run:** a switch re-reads the context; for another model, hand over a handoff and the start
  command, written out under the header line: `omp --model anthropic/claude-opus-5-5 --thinking=high` (Claude
  Code: `claude --model …`) in the project folder, with a first message that names the handoff file.
- **Escalate one step, never two,** when a wave's merged result fails its check after the fix round, rows or
  reviews contradict each other on a contract, a wave's result invalidates the dependency plan, or a floor decision
  spans systems with no check: spawn one `anthropic/claude-opus-5-5:high` subagent with the question and artefact
  paths (`xhigh` when the question spans systems; Fable only under SKILL.md section 2's condition), or ask the user
  to raise the session. No agent raises its own level. Log the parent's and the workers' share of each run's cost.

## Chains

A chain (Terms) runs one link at a time, never split into a wave. Paid or gated links: the parent keeps its model and
runs them, and side waves never make a swarm run. Each link's check is its end state, judged by the gate the plan
names (paid links: SKILL.md floors); fix rounds count per link gate. Beside the current link, as subagent or Codex
rows: tools with a selftest, research, checks of done links, inputs not needing the current artefact ([sequential.md](sequential.md)).

## The plan table

```markdown
## Work triage

Orchestrator: Opus 5.5 · high (swarm run). Reviews: 2, at 10 and 11. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Decide the plugin interface | Opus 5.5 | high | subagent | — | `docs/interface.md` | reviewed at 10 | — |
| 2 | CSV plugin to the interface | gpt-6.1-sol | medium | Codex | 1 | `plugins/csv.py`, its test | its tests | fails twice → gpt-6-astra high |
| 12 | Push and open the PR | — | — | user | 11 | — | — | — |
```

- Goes into the plan, in its language. `#`: whole numbers (section 1). `Starts after`: `—` or a comma list of `#`;
  a row whose `Check` needs another row's output lists that row. `Owns`: files or outputs, `—` for gates and
  read-only rows. Review rows: "review" in the first two words of `Row`.
- `Orchestrator:` names the model and level the session runs at now (`Opus 5.5 · medium`); never a level the
  session should be raised to, never "session level". `parent` rows write that
  same model and level, from `low`, `medium`, `high`, `xhigh`. A floor above the session's level makes the row a
  subagent at the floor (production, paid runs and gates excepted: those stay in the parent; ask the user to raise
  the session or hand over).
- `Run as`: `subagent`, `Codex`, `parent` (names the parent's model and level), `user` (`—` for model and level).
- In omp every row carries a per-call `model` with its level (`anthropic/claude-opus-5-5:high`), never `effort`:
  that field is relative (`hi` is the model's highest level), and a row without `model` runs on the parent's model
  and level. A noted approval is a record; a new session asks again.
- Up to five rows: one line, exactly `Triage: <#> <Model>·<level> (<Run as>) · … · <gates>`, the line starting
  with `Triage:` (no bold, no bullet). Each entry is number, model, level and runner only (a solo plan adds
  `, solo` to its parent entry): no row text, no reasons, no checks, no "floors: none". Gates name only actions the
  plan has (`gate before push` only with a push). A note on a declined or changed request goes in one sentence
  above the line; nothing follows it. More rows: the table. A solo plan of any length uses the one line.
  `Triage: 1 Opus 5.5·low (parent) · 2 gpt-6.1-sol·medium (Codex) · gate before push.`

## During the run

1. **Didn't try** (skipped files, tests not run, stopped early, "done" without check output, a one-layer fix; a
   check's first failure): same model, level +1 (`gpt-6.1-sol` `medium` → `high`); Sonnet `high`: next rung.
2. **Didn't know** (full context, a real attempt, still wrong; a check's second failure): next rung on Sonnet `medium`
   → Sonnet `high` or Opus `low` → Opus `medium` → `high` → `xhigh` → Fable (section 2); Codex: `gpt-6.1-sol` →
   `gpt-6-astra` `high`, or Claude at the matching rung. Security stops at Opus `xhigh`, then the user.
3. Re-triage upward at once when a row touches more than planned, sources disagree or a floor appears; rows added
   during the run get a triage line first.
4. **Fix rounds:** a second only when a mechanical check still fails; after two, stop and report to the user.
5. **Log the level that ran,** read from the subagent's file after the first spawn of the run and of each new model,
   never the planned one: row, planned rung, actual rung, first check passed (y/n), trigger, result.
6. **Escalation changes who runs a row, never what it may do:** a repeated paid call, push, deploy, save or delete
   needs a new approval from the user. Step down only between verified rows, never inside a floor row.

## Self-check

- Size first: the work is larger than one session (SKILL.md section 1); every spawn names its `model`; small rows are batched.
- Every row has model and level (`user` rows `—`), `Run as`, `Starts after`, `Owns`, `Check`; omp: `model`, never `effort`.
- Every `#` and `Starts after` entry is a whole number; the header names the level the session runs at now; a
  model other than the session's comes with the written-out start command.
- Every floor is met and named in its row's `Check`; every gate is a `user` row or, for a paid chain link, written
  in full in its `Check`.
- Every spawned row with a check that stands alone that is not a Codex row names why in `Check` or `Escalate if`.
- Rows above Opus 5.5 `medium` meet a SKILL.md floor or a signal of section 2; Fable rows name section 2's
  condition; no Sonnet above `high`, no `max`; parent rows are solo rows or floor-bound rows.
- Every wave has one writer per file; no chain row shares a wave with its predecessor; no needless `Starts after`.
- Reviews and fix rounds are counted in the header line and sit only at section 4's review points, also when the
  user asks for more "to be safe" (name the review points instead).
- One-line form: the line matches the shape above, word for word in its parts.

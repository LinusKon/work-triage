# Spawning rows: table, rungs, schedule, reviews

Read this when the work is orchestrated (SKILL.md sections 1 and 2). A solo plan needs only its one-line form
(The plan table).

## Terms

| Term | Meaning |
|---|---|
| parent | the parent (the main session the user talks to); it plans, spawns, integrates and runs the rows a floor binds to it |
| omp's words | used as omp defines them: subagent, agent type, `tasks[]` batch, per-call `model`, model selector (`provider/model-id:level`), thinking level (Claude Code: effort level), allow-list |
| row | one outcome with one check, one executor, one set of owned files or outputs; one line of the plan table |
| level | the thinking level a row runs at; for Codex rows its reasoning effort |
| rung | one step on section 2's ladder of model and level, from `wt-worker` (Sonnet 5.5 `medium`) up to Fable 5.2 |
| floor | the lowest model and level a row may get because of what it touches (SKILL.md section 3) |
| gate | an approval only the user gives: push, PR, merge, deploy, paid calls, key changes, anything irreversible |
| coupled | two rows that touch the same file or component, where one needs the other's result, design or API, that share a rename, or where one refines the other |
| wave | rows with no unfinished dependency, spawned together as one `tasks[]` batch |
| join | the point where the outputs of several rows are merged or a later wave starts to build on them |
| leaf row | a row no later row builds on |
| integration owner | whoever runs builds, linters and the full suite once after a wave: the parent unless the plan names a row |
| chain | the path of artefact dependencies: link n needs the artefact of link n-1; a link may also have further predecessors (a tool it uses) and successors (a check of its result) |
| swarm run | a plan without a chain the parent must run (paid or gated links) that has a wave of six or more rows, or three or more waves of two or more rows each |
| interface | what other code or people depend on: routes and payloads, config keys, schemas, file formats, CLI flags, exported signatures, prompts other tools consume. Deciding one is a floor; carrying a decided change to its call sites is not |
| a check that stands alone | an automatic check that fails if the row is wrong in the way that matters (a test that fails on the old code, a type check plus a grep count), named in the brief before the row runs; tests the row writes for itself count only once the parent has read them; a row's own claim never counts; "it runs" is not one |
| tiny step | a few tool calls on files already in context |

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

**Model = how capable:** raise it for judgment, an approach nobody wrote down, an unfamiliar domain, or a row that
had full context, made a real attempt and was still wrong. **Level = how thorough:** files read, tests run, time
before checking back; it fixes missed edge cases, never a wrong approach.

Signals, in this order: (1) floor; (2) a check that stands alone; (3) does the row choose an approach, or are what,
where and how to check written down; (4) taste or judgment across parts of the system; (5) blast radius and
reversibility; (6) how much it must read; (7) how many later rows build on it. A row that earns a spawn (SKILL.md
section 1) gets the **lowest rung whose conditions it meets**, after floors, cheapest first
([calibration.md](calibration.md) has the measured runs). Rows that earn no spawn stay in the parent.

| Rung | The row |
|---|---|
| `wt-worker` (Sonnet 5.5 `medium`) | what, where and how to check are written down; it chooses no approach; a mistake shows in a test or is cheap to spot; no floor, no taste: modules, CLIs, tests and docs to a spec, a bug with a failing test, search, log reading, transforms with a count or schema check, web research with links |
| `wt-worker-hard` (Sonnet 5.5 `high`) | the same, dense with edge cases (parsers, number formats, rounding, time, concurrency) or with an approach to choose inside the spec; design built in code (pages, motion, 3D scenes) |
| Opus 5.5 `medium`, by per-call `model` | taste in words: concepts, copy, prompts for image and video models, documents from more sources than the parent checks. Never design built in code (SKILL.md section 2, item 3) |
| Opus 5.5 `high` | the parent's default; floors (security, secrets, an interface still to decide; SKILL.md section 3); judgment with no check; a row three or more later rows build on, with no check; the review, as `wt-reviewer` |
| Opus 5.5 `xhigh` | edge-case-dense work no check covers (parsers, sanitisers, concurrency, billing, migration scripts on real data); a review that found a major issue or a risky path no test covers. Never a first attempt where a check exists |
| Fable 5.2 (`high` alone, `medium` when the parent steers it) | only under SKILL.md section 2's condition: Opus `xhigh` failed with full context on cross-system architecture or root cause, frontier-hard work beyond one context, or design when the user asks for the best possible result. Never security: its safeguards block most cyber tasks |

Doubt about a row does not raise its rung; write what would raise it into `Escalate if`. Rows a floor binds to the
parent (production, paid runs, gated scripts, the links of a chain) run at the parent's model and level, which does
not count as a higher rung. Every other row that differs from the parent runs as a subagent or Codex row. Never
Sonnet above `high`; `max` is not planned.

**Codex rows are optional.** When the user works with Codex or asks for it, a row for `wt-worker` goes to
`gpt-6.1-sol` `medium` and a row for `wt-worker-hard` to `gpt-6.1-sol` `high`; in the study both routes cost the
same. A Codex review or second opinion (`gpt-6-astra` `high`) happens only when the user asks for one, because it
is the most expensive model. Local app checks without login (browser, simulator, screenshots) go to
`gpt-6.1-terra` `medium`; `gpt-6-luna` `high` only when the user names it, never on security or edge cases. Pass
model and level explicitly; the CLI's default is the most expensive. Never Codex: security, secrets, production,
paid runs, gates; signed-in web; taste, image and video prompts, plans and designs. Codex never commits, pushes,
deploys or edits global config; mechanics: `codex-*.md` here and `scripts/codex_row.sh`.

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
6. **Level check:** after the first spawn of the run and of each new model, read the level that ran (During the
   run, item 3).
7. **Rows added mid-run** get a triage line before their spawn (During the run, item 2).
8. **Follow-ups:** the planned fix round goes to the author, which keeps its context; other new work is a fresh row.
9. **Chains** are detected here and run as Chains says. Details: [schedule.md](schedule.md).

## 4. Verify: reviews and fix rounds

| Review point | Who | Rounds |
|---|---|---|
| Leaf row with a check that stands alone | no review; the parent reads the check output | — |
| Join: the merged result of several rows | one `wt-reviewer` review against the contract and the hardening list, not file by file | one fix round |
| Other floor rows (interface, migration or irreversible prepare) | the one review before their gate covers them (the join review where there is one); none of their own | — |
| Security or secrets rows | one `wt-reviewer` review scoped to those files and their tests, instead of the join review for them (SKILL.md section 4); `xhigh` only when it finds a major issue or no test covers the risky path; never Codex | one fix round |
| Before anything irreversible, paid or outward | a prepare row, then the gate | — |

No final or cross-family review is added by default; a Codex review runs only when the user asks for one. Order:
an automatic check, then a fresh-context model review for what it cannot cover, then the user. Before rows that
build on a row start, the parent accepts it (reads its output and check): no review row; "reviewed at 4" in a
`Check` cell names the later join review. Reviews and fix rounds are stated up front, only at these points.
"Done" means evidence: the command and its output, or the artefact path. Reviewer prompt: [verify.md](verify.md).

## The parent's role

- **Swarm run:** the parent keeps its model and level (Opus 5.5 `high` by default). It plans, triages, writes the
  contracts rows share (interface decisions too), integrates, decides at joins and runs floor-bound parent rows. It
  does no implementation, research or writing of its own. The saving comes from the workers' rungs and from
  batching small rows into few workers (SKILL.md section 2).
- **Not a swarm run,** including a plan on a chain the parent runs: the parent keeps its model and level and asks
  for no switch. The number of rows decides whether the plan is one line or a table (The plan table).
- **One model per run:** a switch re-reads the context. For another model, hand over a handoff and the start
  command, written out under the header line: `omp --model anthropic/claude-opus-5-5 --thinking=high` (Claude
  Code: `claude --model …`) in the project folder, with a first message that names the handoff file.
- **Escalate one step, never two,** when a wave's merged result fails its check after the fix round, rows or
  reviews contradict each other on a contract, a wave's result invalidates the dependency plan, or a floor decision
  spans systems with no check: spawn one `anthropic/claude-opus-5-5:high` subagent with the question and artefact
  paths (`xhigh` when the question spans systems; Fable only under SKILL.md section 2's condition), or ask the user
  whether to raise the parent's level. No agent raises its own level. Log the parent's and the workers' share of
  each run's cost.

## Chains

A chain (Terms) runs one link at a time, never split into a wave. Paid or gated links: the parent keeps its model
and runs them, and side waves never make a swarm run. Each link's check is its end state, judged by the gate the
plan names (paid links: SKILL.md floors); fix rounds count per link gate. Beside the current link, as subagent or
Codex rows: tools with a selftest, research, checks of done links, inputs not needing the current artefact
([sequential.md](sequential.md)).

## The plan table

```markdown
## Work triage

Orchestrator: Opus 5.5 · high (orchestrated build, rows shortened). Reviews: 1, at 4. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Write the contract and the shared helpers | Opus 5.5 | high | parent | — | `docs/contract.md`, `src/core/` | helper tests pass; reviewed at 4 | — |
| 2 | CSV and QIF parsers to the contract (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `src/parsers/csv.py`, `src/parsers/qif.py`, its tests | its tests | fails again → parent fix or `wt-worker-hard` |
| 3 | MT940 parser: dates, amounts, rounding (`wt-worker-hard`) | Sonnet 5.5 | high | subagent | 1 | `src/parsers/mt940.py`, its tests | its tests | fails again → parent fix or Opus 5.5 high |
| 4 | Review the merged result against the contract and the hardening list (`wt-reviewer`) | Opus 5.5 | high | subagent | 2, 3 | — | findings with severity | major issue or untested risky path → Opus 5.5 xhigh |
| 5 | Push and open the PR | — | — | user | 4 | — | — | — |
```

- Goes into the plan, in its language. `#`: whole numbers (section 1). `Starts after`: `—` or a comma list of `#`;
  a row whose `Check` needs another row's output lists that row. `Owns`: files or outputs, `—` for gates and
  read-only rows. Review rows: "review" in the first two words of `Row`.
- `Orchestrator:` names the model and level the parent runs at now (`Opus 5.5 · high`). Write the level itself:
  never a level the parent should be raised to, never the words "session level". `parent` rows write that same
  model and level. A floor above the parent's level makes the row a subagent at the floor (production, paid runs
  and gates excepted: those stay in the parent; ask the user to raise the parent's level or hand over).
- `Run as`: `subagent`, `Codex`, `parent` (names the parent's model and level), `user` (`—` for model and level).
- In omp every spawn names an agent (`wt-worker`, `wt-worker-hard`, `wt-reviewer`) or a per-call `model` with its
  level (`anthropic/claude-opus-5-5:medium`), never `effort`: that field is relative (`hi` is the model's highest
  level), and a spawn with neither runs on the parent's model and level. A row for a `wt-*` agent writes the
  agent's model and level and names the agent in `Row`. A noted approval is a record; a new session asks again.
- Up to five rows: one line, exactly `Triage: <#> <Model>·<level> (<Run as>) · … · <gates>`, the line starting
  with `Triage:` (no bold, no bullet). Each entry is number, model, level and runner only (a solo plan adds
  `, solo` to its parent entry): no row text, no reasons, no checks, no "floors: none". Gates name only actions the
  plan has (`gate before push` only with a push). A note on a declined or changed request goes in one sentence
  above the line; nothing follows it. More rows: the table. A solo plan of any length uses the one line.
  `Triage: 1 Opus 5.5·high (parent), solo.`
  `Triage: 1 Opus 5.5·high (parent) · 2 Sonnet 5.5·medium (subagent) · gate before push.`

## During the run

1. **A failing row** goes back to its author once, by message, so it keeps its context. If it fails again, the
   parent fixes it when the fix is small; otherwise the row moves one rung up: `wt-worker` → `wt-worker-hard` →
   Opus 5.5 `high` (Codex rows: `gpt-6.1-sol` `medium` → `high` → Opus 5.5 `high`). After two failed rounds on
   one row the parent stops and tells the user. Security stops at Opus `xhigh`, then the user. Fable only under
   SKILL.md section 2's condition.
2. Re-triage upward at once when a row touches more than planned, sources disagree or a floor appears; rows added
   during the run get a triage line first.
3. **Log the level that ran,** read from the subagent's file after the first spawn of the run and of each new model,
   never the planned one: row, planned rung, actual rung, first check passed (y/n), trigger, result.
4. **Escalation changes who runs a row, never what it may do:** a repeated paid call, push, deploy, save or delete
   needs a new approval from the user. Step down only between verified rows, never inside a floor row.

## Self-check

- Size first: the work is larger than one session (SKILL.md section 1); every spawn names an agent or a `model`;
  small rows are batched.
- Every row has model and level (`user` rows `—`), `Run as`, `Starts after`, `Owns`, `Check`; omp: an agent or
  `model`, never `effort`.
- Every `#` and `Starts after` entry is a whole number; the header names the level the parent runs at now; a
  model other than the parent's comes with the written-out start command.
- Every floor is met and named in its row's `Check`; every gate is a `user` row or, for a paid chain link, written
  in full in its `Check`.
- Rows above Opus 5.5 `medium` meet a SKILL.md floor or a signal of section 2; Fable rows name section 2's
  condition; no Sonnet above `high`, no `max`; parent rows are solo rows, the contract or floor-bound rows.
- Codex rows only when the user works with Codex or asks for it; one review at the join, none added at the end.
- Every wave has one writer per file; no chain row shares a wave with its predecessor; no needless `Starts after`.
- Reviews and fix rounds are counted in the header line and sit only at section 4's review points, also when the
  user asks for more "to be safe" (name the review points instead).
- One-line form: the line matches the shape above, word for word in its parts.

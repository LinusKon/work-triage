# Schedule: waves and chains

Detail behind `spawn.md` section "3. Schedule: waves and chains". The words row, wave, join, chain and floor
mean what `spawn.md` `## Terms` says. The parent (the main session the user talks to) builds the schedule.
Harness steps (spawn fields, settings, where the level that ran is recorded) are in `harness-omp.md` and
`harness-claude-code.md`; this file names the step and links there.

## 1. The coupling test

For each pair of rows ask four questions. One yes makes the pair coupled.

| Question | Example | Then |
|---|---|---|
| Do they touch the same file or component? | Two rows both edit `config.py`. | merge or order |
| Does one need the other's result, design or API? | The client calls an endpoint another row builds. | order |
| Does a rename in one touch the other? | One row renames `prefs` to `settings`; another edits code that imports `prefs`. | merge |
| Does one refine the other? | "Write the README section" and "tighten its wording". | merge |

When unsure, treat the pair as coupled: a missed split only costs time, a wrong split puts two writers on
one file. Coupling is transitive: if A is coupled to B and B to C, all three are handled together.

## 2. Merge or order

- **Coupled through a file, a component, a rename or a refinement: merge** into one row, or order them when
  they must stay separate. Two writers on one file overwrite each other or leave conflicting patches for the
  integration owner (whoever runs builds and the full suite after a wave: the parent unless the plan names a
  row). Separate worktrees do not change this: same-file rows never run in parallel.
- **Coupled through a result: order.** The later row gets the earlier one's `#` in `Starts after`.
- An interface coupling disappears once the contract is written: rows built against it run side by side (3).

## 3. Settle shared contracts first

Whatever several rows of a wave share (terms, interfaces, file names, formats, the plan table itself) is
written before the wave, by the parent or by an earlier row, and goes into the batch's shared context, not
into each task. Rows that guess a shared contract each guess differently, and the join pays for it.

## 4. Build waves from `Starts after`

- A row's wave is one more than the highest wave among its `Starts after` rows; a row with `—` is in wave 1.
- A bounded single-issue change (one bug, one feature in one area) is one row for one agent, not a wave.
- A wave is every row whose `Starts after` rows are all done and accepted. Spawn it as one batch.
- **Acceptance before consumers start:** the parent reads each finished row's output and check before rows
  that build on it start. Acceptance is not a review row and costs no review; the join review comes after the
  consumers and covers the merged result (`verify.md`).
- Add a dependency only where the row needs that output. Each extra one pushes the row into a later wave.
- A gate row (`Run as` `user`) sits in the wave like any other row; the rows after it wait for the user.

## 5. Limits

- **At most 15 rows per wave.** That fits the harness's concurrency defaults with room to spare
  (`harness-omp.md`) and keeps the join small enough to review. A larger wave splits by component into two
  waves.
- **No nested swarms.** A row may not spawn a wave of its own. The harness allows only shallow recursion,
  and a nested wave runs outside the plan's ownership, levels and reviews.

## 6. Ownership

- Every row has an `Owns` cell: the files or outputs it alone writes; `—` for gates and read-only rows.
- One writer per file. Rows that need the same file are coupled (section 1): merge them or order them.
- Rows skip builds, linters, formatters and test suites that touch shared state. The integration owner runs
  them once after the wave. A row runs only its own check.
- Note: rows of one wave that write in separate worktrees branch from the same commit; the integration owner
  merges them with a dry run and runs the full suite, and the next wave branches from the merged head.

## 7. Preflight before the first spawn

Before the first spawn of each wave, confirm that every model and level in the wave can be spawned as
written. A model the harness has not granted fails the spawn or falls back silently, and the wave stalls
or runs on the wrong model. The steps per harness: `harness-omp.md`, `harness-claude-code.md`.

## 8. Read the level that ran

After the first spawn of the run, and the first spawn of each new model, read the model and level that
actually ran from the subagent's record and compare it with the plan. Log what ran, never what was
planned. A mismatch is fixed in the spawn before the rest of the wave goes out. Where the record is:
the harness files.

## 9. Rows added during the run

New work found mid-run gets a triage line before its spawn: model, level, `Starts after`, `Owns`, check.
An untriaged spawn inherits the parent's model and level, usually far above what the row needs. Its `Owns`
may not overlap a row that is still running. Number it after the last `#`.

## 10. Follow-ups

- **The planned fix round goes to the author**, by message to the existing subagent: it keeps its context
  and its reading of the task. Caps and the reviewer's prompt: `verify.md`.
- **Any other new work is a fresh, narrow row** (section 9). A revived long-running subagent pays for its
  whole context on every turn and brings assumptions from the old task.

## 11. Chains in the graph

A chain is the path of artefact dependencies in `Starts after`: link n needs the artefact of link n-1, so the
links run one per wave and are never split. A link may have further predecessors (a tool or script it uses)
and further successors (a check of its result); those do not break the chain. Rows that do not need the
current artefact (tools with a selftest, research, drafts for the next link) run beside it as waves of their
own. A chain the parent must run (paid or gated links) wins over the swarm count: the plan follows the
sequential profile, and the side rows never make it a swarm run. How to run a chain: `sequential.md`.

## 12. Worked example

Plan: add a settings page to a web app. The draft had eleven steps; "rename the `prefs` module to
`settings`" touched the endpoint's files, so it merged into row 3 (rename coupling). Row 1 writes the
contract; the parent accepts it, and it goes into the shared context of wave 2.

Dependencies: 3 ← 1 · 4 ← 1 · 5 ← 1 · 6 ← 1, 2 · 7 ← 1 · 8 ← 3, 4 · 9 ← 3, 4, 5, 6 · 10 ← 4.

| # | Row | Starts after | Owns | Wave |
|---|---|---|---|---|
| 1 | Decide the settings data model and API contract | — | `docs/settings-contract.md` | 1 |
| 2 | List every stored settings key in the code (read-only) | — | `notes/settings-keys.md` | 1 |
| 3 | Rename `prefs` to `settings`; build the endpoint to the contract, with tests | 1 | `api/settings/`, its tests | 2 |
| 4 | Settings form to the contract | 1 | `web/settings/form.tsx` | 2 |
| 5 | Client SDK types to the contract | 1 | `sdk/types/settings.ts` | 2 |
| 6 | Migration of stored settings, with dry run | 1, 2 | `migrations/settings_001.py` | 2 |
| 7 | User docs page | 1 | `docs/user/settings.md` | 2 |
| 8 | Wire the form to the endpoint, end-to-end test | 3, 4 | `web/settings/api.ts`, `e2e/settings.spec.ts` | 3 |
| 9 | Review rows 3-6 against the contract | 3, 4, 5, 6 | — | 3 |
| 10 | Screenshots for the docs page | 4 | `docs/user/img/settings-*.png` | 3 |

Checked by hand: rows 1 and 2 have no dependency (wave 1); rows 3-7 depend only on wave-1 rows (wave 2);
rows 8, 9 and 10 each depend on at least one wave-2 row and on nothing later (wave 3). No file is owned twice
in any wave. Row 10 waits only for the form (row 4), not for the whole of wave 2. After wave 3 the
integration owner runs the full test suite once.

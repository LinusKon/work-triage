# Work-triage 2.0 fixtures

These offline fixtures check model allocation, dependency scheduling, floors and
review budgets. They evaluate a plan, not the quality of its eventual work.
Use the table and one-line formats in the skill's “The plan table” section.

From this directory (`tests/work-triage/`, Python 3.9+, standard library only):

```sh
python3 score.py swarm reference/swarm.md
python3 score.py --lint reference/mixed.md
python3 score.py --selftest
```

`fixtures/<name>/task.md` is the session prompt; keep `expected.json` hidden from
that session. Score its saved answer with `<name> <answer.md>`. Names are `swarm`,
`chain`, `mixed`, `trivial`, and `floor`. `reference/` holds accepted answers;
`wrong/` holds deliberate counterexamples with their reasons in comments.
`live/` holds five real skill outputs. Selftest checks their expected passing
scores, the counterexample reasons, zero-point references and parser/scorer edges.
Exit 0 means pass; exit 1 means rejection; CLI usage errors exit 2.

`expected.json` (schema version 2) records accepted `model:level` pairs or
`parent`/`user`, floor flags, kinds and minimum pairs, `never` family/runner
exclusions, `read_only` exceptions, Codex preference, required/optional/forbidden dependencies,
chain membership and predecessor, orchestrator choice, review points/count and
fix-round count. A null orchestrator means no required switch. `parent` may also use an accepted model/level pair without an explicit
parent listing; other allocations receive the usual points or floor failures.
Its Model and Level must match the declared orchestrator. Parent-bound work retains that allocation, but still meets its
floor and family exclusions. Production verification (mixed row 9 and floor
row 7) accepts only `parent`. Opus `low` requires `parent`.

Lint checks canonical columns, models, levels and runners, unique step numbers,
existing dependencies, cycles, empty ownership and overlapping ownership in a wave.
Waves are one plus the latest dependency wave; rows without dependencies start
in wave 1. Write literal owned paths separated by commas; backticks are optional
for each entry. Unquoted entries starting with `its ` (such as `its test` or
`its page`) belong to that row alone and never collide with another row.
All other entries count, including unquoted names beside quoted paths and
backtick-quoted names starting with `its `. A directory collides with paths inside it; lexical aliases such as `./`
are normalized. Two rows of the same wave cannot own the same entry. Rows in
different waves may reuse a path. Use `—` for none; an empty cell or comma entry
fails lint. In a full table, a writing row cannot use `—`; user rows, review
rows and fixture rows marked `read_only` may do so. One-line entries omit Owns.

Scoring fails for a missed floor, a gate delegated away from the user, a broken
chain, a missing required dependency (direct or transitive), ownership collisions, unaccepted/excess
reviews or excess fix rounds. Keep the
fixture's step numbers and required review rows. Declare review counts/points
and fix rounds above full tables, as in the references. Counts use the first
number after `Reviews:` or `Fix rounds:` and accept trailing wording. Floor checks preserve
model-family restrictions; a more expensive family cannot bypass a floor.
Security and secrets work and their reviews forbid Codex, Sonnet and Fable;
video prompts forbid Codex. Interface and migration preparation may be covered
by a Codex join/final review; security and secrets get one Opus review (`high`,
`xhigh` only as escalation) outside the Codex review's scope.

The trivial fixture measures over-planning: after syntax/lint checks, it fails
only for more than two rows (either form) or a review row. It ignores the
orchestrator declaration and does not score the session's allocation or budgets.
The two numbered reference steps are a suggested grouping.

An unaccepted allocation above the accepted range costs one point per rung.
Below the range, a floor or review row fails; another row costs two points.
An unlisted pair within the range also costs two points. A listed parent
allocation is exempt from rung penalties, but never from its floor or exclusions.
`gpt-6-luna` `high` remains rung 2 and requires explicit fixture acceptance;
it is not an automatic alternative for a transform. Transforms with count or
schema checks use Sonnet `medium` (mixed row 4).

The rung distances in `RUNG` are:

| Rung | Model and level |
|---|---|
| 1 | Sonnet 5.5 `medium` |
| 2 | Sonnet 5.5 `high`, Opus 5.5 `low`, gpt-6.1-sol `medium`, gpt-6-luna `high`, gpt-6.1-terra `medium` |
| 3 | Opus 5.5 `medium`, gpt-6.1-sol `high` |
| 4 | Opus 5.5 `high`, gpt-6-astra `high` |
| 5 | Opus 5.5 `xhigh` |
| 6 | Fable 5.2 `medium` |
| 7 | Fable 5.2 `high` |

Other penalty points are one per unnecessary
dependency that delays a row, and one per unexplained non-Codex allocation of a
`codex_first` row. A reason for bypassing Codex goes in Check or Escalate if,
marked `Reason:` or `not Codex:` followed by text (for example,
`Reason: Codex unavailable`). A test name or generic “requires/because” text
alone is not an explanation. Dependencies that do not delay
a row cost nothing. Optional dependencies are accepted; forbidden dependencies
are unnecessary waits, scored transitively by the same delay rule. A permitted
intermediary cannot hide a forbidden wait; independent permitted prerequisites
can still make it redundant. Reviews are rows whose
Row cell contains the word `review` among its first two words (case insensitive),
including `Review …`, `Final review …`, `Join review …` and `Security review …`;
they remain ordinary dependency graph nodes. A final review below its accepted
range fails. One-line forms read every `<n> <model>·<level> (<runner>)` allocation and
ignore other text; a line with no allocation is malformed.

The pass bar is **at most 3 penalty points and no failures**, per fixture.
`--lint` checks structure only; it does not compare against a fixture or apply
its budgets. The scorer implements the stated allocation rubric, not semantic
validation of free-text checks, approval wording or output completeness.

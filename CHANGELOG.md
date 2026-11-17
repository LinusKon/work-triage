# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A share card at the top of the README (`study/charts/share-card-*.svg`, `share-card.png`), drawn from
  `study/data/runs.csv` by `study/share_card.py`.

## [2.6.1] - 2026-11-16

### Changed

- Wording and consistency only: the references follow `SKILL.md` (Codex optional, one review at the join, no Fable
  orchestrator, one failure ladder), terms are defined where first used, the charts are redrawn.

### Added

- `THIRD_PARTY_NOTICES.md` for the Codex references adapted from psdwizzard/claude-setup (MIT).

## [2.6.0] - 2026-11-16

### Changed

- "Exactly the spec, not stricter": workers accept everything the spec's wording accepts; the reviewer looks for
  unrequested restrictions.
- Leaner orchestration: agents copied with one command, briefs point at numbered parts of a spec file.

## [2.5.0] - 2026-11-16

### Added

- omp agent definitions `wt-worker`, `wt-worker-hard` and `wt-reviewer` in `skills/work-triage/agents/`: workers
  and the reviewer carry their model, level and rules, so briefs stay short and no spawn inherits the parent's
  model by accident.

## [2.4.0] - 2026-11-16

### Changed

- Size first: work that fits one session runs solo. Larger builds are orchestrated: contract first, few batched
  workers, an explicit model and level on every spawn, short briefs, one review at the join.
- The main session keeps Opus 5.5 `high`; savings come from the workers.
- A hardening pass before done: value extremes, paths and races, error paths.

## [2.3.0] - 2026-11-16

### Changed

- Sessions run at Opus 5.5 `medium`; `high` is the escalation after a failed check and the floor only for
  architecture across systems, irreversible preparation, production writes and the security review.
- A clear test for work Sonnet can do; such work goes to one Sonnet subagent that also returns the spec check, and
  the main session runs the suite and spot-checks instead of re-reading the code.
- Fable 5.2 only after Opus `xhigh` failed with full context across systems, or for frontier-hard work beyond one
  context; the swarm orchestrator is Opus 5.5 `medium`.

## [2.2.0] - 2026-11-16

### Changed

- Lean core: `SKILL.md` keeps the solo-or-spawn decision, floors, gates, token discipline and a spec check;
  rungs, the plan table, waves, reviews and escalation moved to `references/spawn.md`, read only when a row spawns.
- Security and secrets work gets one Opus `high` review scoped to the floor files; `xhigh` only as escalation.

## [2.1.0] - 2026-11-16

### Changed

- Solo first: the main session runs the plan itself and spawns only rows that earn it (a floor, work far larger
  than its brief, or parallel rows that save wall time).

## [2.0.1] - 2026-11-16

### Fixed

- Row numbers are whole numbers; split or added rows take the next free numbers.
- The orchestrator header names the level the session runs at now; a model switch comes with the start command.
- The one-line form has an exact shape: number, model, level and runner per entry, nothing after the line.

## [2.0.0] - 2026-11-16

First public version.

### Added

- Cuts a plan into rows and gives each row a model and a level: the lowest rung whose conditions the row
  meets, after floors. No default model.
- Floors for interfaces, secrets, security and irreversible steps; only a floor raises a row before it runs.
  Doubt goes into the `Escalate if` cell, not into the rung.
- Sends bounded implementation rows with a check that stands alone to Codex first, through
  `skills/work-triage/scripts/codex_row.sh`, which strips key, token and secret variables from Codex's
  environment.
- Schedules rows into waves and chains from their `Starts after` cells, with one writer per file and the
  shared contracts settled before the first wave.
- Places reviews only where they pay: at joins, at security and secrets rows, and at the final
  integration (cross-family), with at most two fix rounds.
- Keeps irreversible, paid and outward steps as gates the user runs.
- Writes one plan table in a fixed format, or a single line for small plans.
- Ships fixtures and a standard-library scorer (`tests/work-triage/score.py`) that grades a triage against
  accepted answers.

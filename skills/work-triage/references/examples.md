# Worked triages

Five plans that show the judgment behind a table; they are not templates. Rules: `SKILL.md` and `spawn.md`.
Examples 1, 2, 3 and 5 assume work larger than one session (SKILL.md section 1). At the size described, example 1
runs solo unless each rule is large work on its own; it is kept to show the mechanics of a swarm table.

## 1. Swarm run: six lint rules for a Markdown linter

Task: add six rules to a small Markdown linter through a rule interface; each rule gets its own file and tests.
A users' guide explains how to turn them on.

Orchestrator: Opus 5.5 · high (swarm run). Reviews: 2, at 9 and 10. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Decide the rule interface and the fixture format | Opus 5.5 | high | subagent | — | `docs/rule-api.md`, `rules/base.py` | the parent accepts it before 2-8; reviewed at 9 | rules cannot express a case → Opus 5.5 xhigh |
| 2 | Rule: heading order | gpt-6.1-sol | medium | Codex | 1 | `rules/heading_order.py`, its test | its tests | fails twice → gpt-6-astra high |
| 3 | Rule: trailing whitespace | gpt-6.1-sol | medium | Codex | 1 | `rules/trailing_space.py`, its test | its tests | fails twice → gpt-6-astra high |
| 4 | Rule: line length, code blocks exempt | gpt-6.1-sol | medium | Codex | 1 | `rules/line_length.py`, its test | its tests | fails twice → gpt-6-astra high |
| 5 | Rule: duplicate link definitions (case folding, nesting) | gpt-6.1-sol | high | Codex | 1 | `rules/dup_links.py`, its test | its tests | fails twice → gpt-6-astra high |
| 6 | Rule: bare URLs | gpt-6.1-sol | medium | Codex | 1 | `rules/bare_urls.py`, its test | its tests | fails twice → gpt-6-astra high |
| 7 | Rule: list marker style | gpt-6.1-sol | medium | Codex | 1 | `rules/list_marker.py`, its test | its tests | fails twice → gpt-6-astra high |
| 8 | Users' guide: enabling and configuring the rules | Opus 5.5 | medium | subagent | 1 | `docs/guide/rules.md` | read at 10 | — |
| 9 | Review the merged rules against the interface, full test suite | gpt-6-astra | high | Codex | 2, 3, 4, 5, 6, 7 | — | findings with severity | — |
| 10 | Final review of the whole change | Opus 5.5 | high | subagent | 8, 9 | — | findings with severity | — |
| 11 | Push and open the pull request | — | — | user | 10 | — | — | — |

- Row 1 is Opus `high`, not Fable: an interface many rows build on, inside one tool, not architecture across
  systems. The orchestrator may write it itself as the contract the rows share; a separate Opus `high` row is
  equally right.
- Rows 2-7 are bounded, have their own tests and no floor, so Codex goes first; only row 5 gets `high` for its
  dense edge cases. One file set each, so they share a wave; the integration owner runs the suite once after it.
- Row 8 starts after 1, not after 2-7: it is written from the interface, and waiting would cost a wave for nothing.
- No review per rule: leaf rows with tests are read from their test output. Row 9 is the join. Row 10 is Claude
  because most of the code is Codex's: the cross-family final review replaces a second same-family one.

## 2. Chain with side work: splitting a name column on a live database

Task: split `users.name` into `given_name` and `family_name` in four steps on the live database; each step needs
the verified state of the one before. A check script, the app change and the docs run beside it.

Orchestrator: Opus 5.5 · high (not a swarm run; production rows stay in the parent). Reviews: 1, at 5. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Plan the four steps: SQL, rollback, verify query each; dry run on a restored copy | Opus 5.5 | high | parent | — | `migrations/0042_*.sql`, `migrations/plan.md` | dry run up and down passes; not Codex: floor, migration on real data | — |
| 2 | Script comparing old and new columns (counts, samples), selftest on a fixture database | gpt-6.1-sol | medium | Codex | 1 | `tools/check_split.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 3 | App reads and writes the new columns behind a flag, off by default, with tests | gpt-6.1-sol | medium | Codex | 1 | `app/models/user.py`, its tests | its tests | fails twice → gpt-6-astra high |
| 4 | Schema docs and changelog entry for the new columns | Sonnet 5.5 | medium | subagent | 1 | `docs/schema.md`, `CHANGELOG.md` | parent reads the diff | — |
| 5 | Review rows 1 and 3 with dry-run and test output | Opus 5.5 | high | subagent | 1, 3 | — | findings with severity | — |
| 6 | Approve the window; deploy the app with the flag off | — | — | user | 5 | — | — | — |
| 7 | Link 1: add the two nullable columns on the live database | Opus 5.5 | high | parent | 6 | live `users` table | schema query shows both; not Codex: production write | error → rollback, stop |
| 8 | Link 2: backfill in batches | Opus 5.5 | high | parent | 2, 7 | live `users` table | `check_split.py` reports 0 mismatches; not Codex: production write | mismatch → stop, report |
| 9 | Link 3: turn the flag on | Opus 5.5 | high | parent | 8 | live flag `name_split` | error rate flat, `check_split.py` clean on new rows; not Codex: production | errors rise → flag off, stop |
| 10 | Link 4: drop `users.name` | — | — | user | 9 | — | — | — |
| 11 | Verify after the drop: row count, app logs for an hour | Opus 5.5 | high | parent | 10 | — | counts match row 8; not a subagent: production data stays in the parent | mismatch → stop, tell the user |

- Rows 7-10 form a chain: each link needs the end state of the one before, so no rule may put two in a wave.
  Each link is judged by a script; the user gates only the window and the irreversible drop.
- Rows 2, 3 and 4 run beside the chain as one wave; the script blocks only link 2, nothing waits for the docs.
- Row 3 goes to Codex although the task is a migration: the app change is bounded code with tests behind a
  flag; the production write is in the links.
- One review, before the gate, covering the two floor rows; Codex wrote row 3, so the Claude reviewer is
  already cross-family. No review inside the chain: the script is the check.

## 3. Mixed plan: one sprint on a self-hosted photo gallery

Task: fix a thumbnail rotation bug (a failing test exists), harden the upload endpoint, rewrite the upload
page's messages, and compare libraries for stripping photo metadata.

Orchestrator: Opus 5.5 · medium (not a swarm run). Reviews: 2, at 3 and 6. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Fix thumbnail rotation; the failing test exists | gpt-6.1-sol | medium | Codex | — | `src/thumbs.py`, its test | the failing test passes, suite green | fails twice → gpt-6-astra high |
| 2 | Upload: check type by content, size limit, strip paths from names | Opus 5.5 | high | subagent | — | `src/upload.py`, its tests | reviewed at 3; not Codex: floor, security | review finds a bypass after the fix round → Opus 5.5 xhigh |
| 3 | Review row 2 with test output | Opus 5.5 | high | subagent | 2 | — | findings with severity | — |
| 4 | Upload page: empty state and error messages | Opus 5.5 | medium | subagent | — | `src/ui/strings/upload.json` | the user reads them at 7 | — |
| 5 | Compare three metadata-stripping libraries: licence, upkeep, open issues, with links | Sonnet 5.5 | medium | subagent | — | `docs/research/metadata-libs.md` | parent opens two links; not Codex: research, not code | sources disagree → Opus 5.5 medium |
| 6 | Final review of rows 1 and 4 | Opus 5.5 | high | subagent | 1, 4 | — | findings with severity | — |
| 7 | Push and open the pull request | — | — | user | 3, 6 | — | — | — |

- Row 1 is a bug with a test, so it is a bounded row: Codex, no review, the parent reads the test output.
- Row 2 is Opus `high`, a first attempt with tests; its one review is Opus `high` as well (SKILL.md section 4),
  raised to `xhigh` only when it finds a major issue. Never Codex, Sonnet or Fable on security.
- Row 4 would wait for row 2's error list; the parent writes that list into the batch's `context` first, so
  rows 1, 2, 4 and 5 share one wave. Opus `medium` for taste.
- Row 5 chooses no approach and a wrong link is cheap to spot: Sonnet `medium`. The user picks the library.
- Row 2 stays out of the final review (its own review covers it); the code left is Codex's row 1, so Claude reviews.

## 4. Trivial task

Task: correct a wrong default port in the README and in the sample config file; both lines are named.

Triage: 1 Opus 5.5·medium (parent).

The parent row names whatever the session runs. Two known lines whose check is the diff: briefing a subagent
costs more than the edit, and a review of a diff the user reads anyway finds nothing.

## 5. Floors and gates: deleting an old storage bucket

Task: archive the objects of an old storage bucket that the database still references, then delete the rest
and the bucket. Production data, a scoped key and an irreversible deletion.

Orchestrator: Opus 5.5 · high (not a swarm run; the floor rows run in the parent). Reviews: 1, at 5. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Script: unreferenced keys from a bucket listing and a reference export, selftest on fixtures | gpt-6.1-sol | medium | Codex | — | `tools/orphans.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 2 | Export the bucket listing and the referenced keys (read-only) | Opus 5.5 | high | parent | — | `work/listing.csv`, `work/refs.csv` | counts match the storage console; not Codex: production data stays in the parent | — |
| 3 | Create a key that may write only the archive bucket | — | — | user | — | — | — | — |
| 4 | Deletion list and archive copy plan, dry run | Opus 5.5 | high | parent | 1, 2 | `work/delete.csv`, `work/copy-plan.md` | kept + deleted = listing; not Codex: floor, irreversible prepare | counts do not add up → stop, report |
| 5 | Review row 4: the list against the references, dry-run output | Opus 5.5 | high | subagent | 4 | — | findings with severity | — |
| 6 | Copy the kept objects to the archive, verify checksums | Opus 5.5 | high | parent | 3, 5 | archive bucket | every checksum matches; not Codex: production write with a key | mismatch → stop, report |
| 7 | Delete the unreferenced objects and the old bucket; revoke the key | — | — | user | 6 | — | — | — |
| 8 | Verify: the app serves archived files, no reference points at the old bucket | Opus 5.5 | high | parent | 7 | — | a sample of 50 references loads; not a subagent: production data | a file fails → stop, tell the user |

- The parent rows run at the parent's model and level: a floor binds them to the parent (production data stays
  out of subagent prompts, and the preparing rows need Opus `high`). That is not lifting.
- Row 1 holds the logic that decides what is deleted, yet goes to Codex: it is bounded and tested on fixtures
  without real data; the parent runs it on the real exports in row 4. Rows 1-3 share the first wave.
- The deletion is a user row although the parent could run it: no model or level replaces the approval. The
  review sits before the copy because everything after it depends on the list being right.

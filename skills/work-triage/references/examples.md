# Worked triages

Five plans that show the judgment behind a triage; they are not templates. Rules: `SKILL.md` and `spawn.md`. In
every example the parent (the main session the user talks to) runs at Opus 5.5 `high` and keeps that level.
Example 1 fits one session and runs solo; examples 2 to 5 assume work larger than one session (SKILL.md section 1).

## 1. Solo: a date filter for an existing CLI

Task: add a `--since` option to an existing log-summary CLI: parse the date, filter the entries, three tests and
one line in the README. Four files, about 200 lines to write; the user asked for no push.

Triage: 1 Opus 5.5·high (parent), solo.

- The work fits one session, so the parent does all of it, in order, and writes no table. At this size every form
  of delegation measured cost more than doing the work (SKILL.md section 1).
- The line names no gate because the plan has no push. A one-line fix, such as a wrong default port in the README,
  gets the same line: briefing a subagent costs more than the edit.

## 2. Swarm run: a bank-statement importer

Task: build a command-line tool that imports bank statements in five formats (CSV dialects, QIF, OFX, MT940,
CAMT.053), maps them to one transaction record, categorises them by user rules and writes monthly reports. The
spec has 40 numbered parts; the estimate is about 30 files and 4,000 lines with tests.

Orchestrator: Opus 5.5 · high (swarm run). Reviews: 1, at 8. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Write the contract: transaction record, error rules, test conventions, shared amount and date helpers | Opus 5.5 | high | parent | — | `docs/contract.md`, `src/core/` | helper tests pass; reviewed at 8 | — |
| 2 | Parsers: CSV dialects and QIF, with tests (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `src/parsers/csv.py`, `src/parsers/qif.py`, its tests | its tests | fails again → parent fix or `wt-worker-hard` |
| 3 | Parser: OFX, with tests (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `src/parsers/ofx.py`, its tests | its tests | fails again → parent fix or `wt-worker-hard` |
| 4 | Parsers: MT940 and CAMT.053, with tests (`wt-worker-hard`) | Sonnet 5.5 | high | subagent | 1 | `src/parsers/mt940.py`, `src/parsers/camt.py`, its tests | its tests | fails again → parent fix or Opus 5.5 high |
| 5 | Categorisation: rule file loader, matcher, rule precedence, with tests (`wt-worker-hard`) | Sonnet 5.5 | high | subagent | 1 | `src/categorise/`, its tests | its tests | fails again → parent fix or Opus 5.5 high |
| 6 | Reports: monthly summary, CSV export, terminal table, with tests (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `src/reports/`, its tests | its tests | fails again → parent fix or `wt-worker-hard` |
| 7 | CLI commands and the users' guide (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `src/cli.py`, its tests, `docs/guide.md` | its tests | fails again → parent fix or `wt-worker-hard` |
| 8 | Review the merged result against the contract and the hardening list (`wt-reviewer`) | Opus 5.5 | high | subagent | 2, 3, 4, 5, 6, 7 | — | findings with severity | major issue or untested risky path → Opus 5.5 xhigh |
| 9 | Push and open the pull request | — | — | user | 8 | — | — | — |

- The build is larger than one session holds comfortably, and its modules share nothing but the contract, so the
  parent orchestrates it (SKILL.md section 2).
- Row 1 stays in the parent: every worker builds on the contract, so the parent writes it and the shared helpers
  itself and puts it into the batch's `context`. It is an interface inside one tool, not architecture across
  systems, so Opus `high` and not Fable.
- Rows 2-7 are modules to a spec with their own tests, so they go to `wt-worker`. Rows 4 and 5 go to
  `wt-worker-hard`: bank formats are dense with number and date edge cases, and rule precedence is an approach to
  choose inside the spec. Small modules are batched, so six workers carry about thirty files. Each file has one
  writer, so all six share one wave, and the parent runs the full suite once after it.
- Row 7 starts after 1, not after 2-6: it is written against the contract, and waiting would cost a wave.
- One review, at the join: row 8 reads the merged result, not file by file. No module gets its own review; the
  parent reads each module's test output. No final or Codex review is planned; the user may ask for one.
- A worker whose tests fail gets the failure back once. If it fails again, the parent fixes a small fault itself
  or moves the row one rung up, as `Escalate if` says. If the user works with Codex, the `wt-worker` rows can go
  to `gpt-6.1-sol` `medium` and the `wt-worker-hard` rows to `gpt-6.1-sol` `high`.

## 3. Chain with side work: splitting a name column on a live database

Task: split `users.name` into `given_name` and `family_name` in four steps on the live database; each step needs
the verified state of the one before. A check script, the app change and the docs run beside it.

Orchestrator: Opus 5.5 · high (not a swarm run; production rows stay in the parent). Reviews: 1, at 5. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Plan the four steps: SQL, rollback, verify query each; dry run on a restored copy | Opus 5.5 | high | parent | — | `migrations/0042_*.sql`, `migrations/plan.md` | dry run up and down passes; floor: migration on real data | — |
| 2 | Script comparing old and new columns (counts, samples), selftest on a fixture database (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `tools/check_split.py`, its test | its selftest | fails again → parent fix or `wt-worker-hard` |
| 3 | App reads and writes the new columns behind a flag, off by default, with tests (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `app/models/user.py`, its tests | its tests | fails again → parent fix or `wt-worker-hard` |
| 4 | Schema docs and changelog entry for the new columns (`wt-worker`) | Sonnet 5.5 | medium | subagent | 1 | `docs/schema.md`, `CHANGELOG.md` | parent reads the diff | — |
| 5 | Review rows 1 and 3 with dry-run and test output (`wt-reviewer`) | Opus 5.5 | high | subagent | 1, 3 | — | findings with severity | — |
| 6 | Approve the window; deploy the app with the flag off | — | — | user | 5 | — | — | — |
| 7 | Link 1: add the two nullable columns on the live database | Opus 5.5 | high | parent | 6 | live `users` table | schema query shows both; floor: production write | error → rollback, stop |
| 8 | Link 2: backfill in batches | Opus 5.5 | high | parent | 2, 7 | live `users` table | `check_split.py` reports 0 mismatches; floor: production write | mismatch → stop, report |
| 9 | Link 3: turn the flag on | Opus 5.5 | high | parent | 8 | live flag `name_split` | error rate flat, `check_split.py` clean on new rows; floor: production | errors rise → flag off, stop |
| 10 | Link 4: drop `users.name` | — | — | user | 9 | — | — | — |
| 11 | Verify after the drop: row count, app logs for an hour | Opus 5.5 | high | parent | 10 | — | counts match row 8; not a subagent: production data stays in the parent | mismatch → stop, tell the user |

- Rows 7-10 form a chain: each link needs the end state of the one before, so no two of them share a wave. A
  script judges each link; the user gates only the window and the irreversible drop.
- Rows 2, 3 and 4 run beside the chain as one wave; the script blocks only link 2, and nothing waits for the docs.
- Row 3 goes to `wt-worker` although the task is a migration: the app change is code to a spec with tests behind
  a flag; the production writes are in the links.
- One review, before the gate, covering the two floor rows. No review inside the chain: the script is the check.

## 4. Mixed plan: one sprint on a self-hosted photo gallery

Task: fix a thumbnail rotation bug (a failing test exists), harden the upload endpoint, rewrite the upload
page's messages, and compare libraries for stripping photo metadata.

Orchestrator: Opus 5.5 · high (not a swarm run). Reviews: 1, at 3. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Fix thumbnail rotation; the failing test exists (`wt-worker`) | Sonnet 5.5 | medium | subagent | — | `src/thumbs.py`, its test | the failing test passes, suite green | fails again → parent fix or `wt-worker-hard` |
| 2 | Upload: check type by content, size limit, strip paths from names | Opus 5.5 | high | subagent | — | `src/upload.py`, its tests | reviewed at 3; floor: security | review finds a bypass after the fix round → Opus 5.5 xhigh |
| 3 | Security review of row 2 with test output (`wt-reviewer`) | Opus 5.5 | high | subagent | 2 | — | findings with severity | — |
| 4 | Upload page: empty state and error messages | Opus 5.5 | medium | subagent | — | `src/ui/strings/upload.json` | the user reads them at 6 | — |
| 5 | Compare three metadata-stripping libraries: licence, upkeep, open issues, with links (`wt-worker`) | Sonnet 5.5 | medium | subagent | — | `docs/research/metadata-libs.md` | parent opens two links | sources disagree → Opus 5.5 medium |
| 6 | Push and open the pull request | — | — | user | 1, 3, 4 | — | — | — |

- Row 1 is a bug with a failing test: `wt-worker`, no review, the parent reads the test output.
- Row 2 touches security, so its floor is Opus `high`. Its one review is a `wt-reviewer` scoped to the upload
  files and their tests (SKILL.md section 4), raised to `xhigh` only when it finds a major issue or no test covers
  the risky path. Never Codex, Sonnet or Fable on security.
- Row 4 would wait for row 2's error list; the parent writes that list into the batch's `context` first, so
  rows 1, 2, 4 and 5 share one wave. Row 4 is taste, so Opus `medium` by per-call `model`.
- Row 5 chooses no approach and a wrong link is cheap to spot, so it goes to `wt-worker`. The user picks the
  library.
- No other review: row 1 has its test, the user reads row 4 at the gate, and no join merges several writers.

## 5. Floors and gates: deleting an old storage bucket

Task: archive the objects of an old storage bucket that the database still references, then delete the rest
and the bucket. Production data, a scoped key and an irreversible deletion.

Orchestrator: Opus 5.5 · high (not a swarm run; the floor rows run in the parent). Reviews: 1, at 5. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Script: unreferenced keys from a bucket listing and a reference export, selftest on fixtures (`wt-worker`) | Sonnet 5.5 | medium | subagent | — | `tools/orphans.py`, its test | its selftest | fails again → parent fix or `wt-worker-hard` |
| 2 | Export the bucket listing and the referenced keys (read-only) | Opus 5.5 | high | parent | — | `work/listing.csv`, `work/refs.csv` | counts match the storage console; floor: production data stays in the parent | — |
| 3 | Create a key that may write only the archive bucket | — | — | user | — | — | — | — |
| 4 | Deletion list and archive copy plan, dry run | Opus 5.5 | high | parent | 1, 2 | `work/delete.csv`, `work/copy-plan.md` | kept + deleted = listing; floor: irreversible prepare | counts do not add up → stop, report |
| 5 | Review row 4: the list against the references, dry-run output (`wt-reviewer`) | Opus 5.5 | high | subagent | 4 | — | findings with severity | — |
| 6 | Copy the kept objects to the archive, verify checksums | Opus 5.5 | high | parent | 3, 5 | archive bucket | every checksum matches; floor: production write with a key | mismatch → stop, report |
| 7 | Delete the unreferenced objects and the old bucket; revoke the key | — | — | user | 6 | — | — | — |
| 8 | Verify: the app serves archived files, no reference points at the old bucket | Opus 5.5 | high | parent | 7 | — | a sample of 50 references loads; not a subagent: production data | a file fails → stop, tell the user |

- The parent rows run at the parent's model and level because a floor binds them to the parent: production data
  stays out of subagent prompts, and the preparing rows need Opus `high`.
- Row 1 holds the logic that decides what is deleted, yet goes to `wt-worker`: it is written to a spec and tested
  on fixtures without real data, and the parent runs it on the real exports in row 4. Rows 1-3 share the first wave.
- The deletion is a user row although the parent could run it: no model or level replaces the approval. The
  review sits before the copy because everything after it depends on the list being right.

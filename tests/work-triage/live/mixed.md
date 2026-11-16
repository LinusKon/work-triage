## Work triage

Orchestrator: Opus 5.5 · high (not a swarm run; the live migration is a gated chain the parent runs). Reviews: 2, at 6 and 10. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Fix the cache bug; the failing test exists | gpt-6.1-sol | medium | Codex | — | the cache module, its test | the failing test passes, suite green; reviewed at 10 | fails twice → gpt-6-astra high |
| 2 | Decide the export endpoint's new field (name, type, nullability, payload shape) | Opus 5.5 | high | parent | — | `docs/export-contract.md` | the parent writes it into the `context` before 3 and 4; reviewed with 3 and 4 at 10 | field needs a data-model change across services → Opus 5.5 xhigh subagent |
| 3 | Implement the export endpoint to the contract, with tests | gpt-6.1-sol | medium | Codex | 2 | the export endpoint, its tests | its tests | fails twice → gpt-6-astra high |
| 4 | Update the client SDK types to the contract | gpt-6.1-sol | medium | Codex | 2 | SDK type files, their tests | SDK type check plus a contract fixture test | fails twice → gpt-6-astra high |
| 5 | Verify webhook signatures and reject replays (timestamp window, nonce store, constant-time compare), with tests | Opus 5.5 | high | subagent | — | the webhook handler, its tests | its tests; reviewed at 6; not Codex: security floor | review finds a bypass after the fix round → Opus 5.5 xhigh |
| 6 | Security review of row 5 with test output | Opus 5.5 | xhigh | subagent | 5 | — | findings with severity | — |
| 7 | Write the data migration with dry run on a restored copy and rollback | Opus 5.5 | high | parent | — | the migration files, `migrations/plan.md` | dry run up and down passes on the copy, counts match; reviewed at 10; not Codex: floor, irreversible prepare on real data | counts do not add up → stop, report |
| 8 | Run the migration on the live data | — | — | user | 10 | — | — | — |
| 9 | Verify the live data after the migration | Opus 5.5 | high | parent | 8 | — | row counts and sample queries match the dry run; not a subagent: production data stays in the parent | mismatch → stop, tell the user; rollback needs a new user approval |
| 10 | Final review of rows 1, 3, 4 and 7 (code, contract, migration and dry-run output; no live data) | Opus 5.5 | high | subagent | 1, 3, 4, 7 | — | findings with severity | — |

Floors: 2 interface, 5 security (own review at 6), 7 irreversible prepare, 8 gate, 9 production read. Waves: 1, 2, 5, 7 → 3, 4, 6 → 10 → chain 8, 9. Row 5 stays out of the final review; row 10 is Claude because most of the code it covers is Codex's.

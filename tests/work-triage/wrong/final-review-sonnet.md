<!-- Expected failure: row 10: below accepted rung range. -->
## Work triage

Orchestrator: Opus 5.5 · medium. Reviews: 2, at 6 and 10. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Fix the cache bug; a failing test exists | gpt-6.1-sol | medium | Codex | — | `cache.py` | Tests and acceptance criteria | — |
| 2 | Decide the new field of the export endpoint | Opus 5.5 | high | subagent | — | `export-contract.md` | Parent accepts the contract before row 3; reviewed at 10 | — |
| 3 | Implement the endpoint to the contract, with tests | gpt-6.1-sol | medium | Codex | 2 | `endpoint.py` | Tests and acceptance criteria | — |
| 4 | Update the client SDK types to the contract | Sonnet 5.5 | medium | subagent | 2 | `sdk/types.py` | Tests and acceptance criteria | — |
| 5 | Verify webhook signatures and reject replays | Opus 5.5 | high | subagent | — | `webhook.py` | Tests and acceptance criteria | — |
| 6 | Review row 5 with test output | Opus 5.5 | xhigh | subagent | 5 | — | Tests and acceptance criteria | — |
| 7 | Write the data migration with dry run and rollback | Opus 5.5 | high | subagent | 2 | `migration.py` | Tests and acceptance criteria | — |
| 8 | Run the migration on the live data | — | — | user | 7, 10 | — | — | — |
| 9 | Verify the data after the migration | Opus 5.5 | medium | parent | 8 | — | Tests and acceptance criteria | — |
| 10 | Final review of rows 1, 3, 4 and 7 | Sonnet 5.5 | medium | subagent | 1, 3, 4, 7 | — | Tests and acceptance criteria | — |

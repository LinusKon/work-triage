<!-- Expected failure: a review after every row adds unaccepted review points. -->
## Work triage

Orchestrator: Opus 5.5 · medium. Reviews: 12, at 6, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Fix the cache bug; a failing test exists | gpt-6.1-sol | medium | Codex | — | `cache.py` | Tests and acceptance criteria | — |
| 2 | Decide the new field of the export endpoint | Opus 5.5 | high | subagent | — | `export-contract.md` | Tests and acceptance criteria | — |
| 3 | Implement the endpoint to the contract, with tests | gpt-6.1-sol | medium | Codex | 2 | `endpoint.py` | Tests and acceptance criteria | — |
| 4 | Update the client SDK types to the contract | Sonnet 5.5 | medium | subagent | 2 | `sdk/types.py` | Tests and acceptance criteria | — |
| 5 | Verify webhook signatures and reject replays | Opus 5.5 | high | subagent | — | `webhook.py` | Tests and acceptance criteria | — |
| 6 | Review row 5 with test output | Opus 5.5 | xhigh | subagent | 5 | — | Tests and acceptance criteria | — |
| 7 | Write the data migration with dry run and rollback | Opus 5.5 | high | subagent | 2 | `migration.py` | Tests and acceptance criteria | — |
| 8 | Run the migration on the live data | — | — | user | 7, 10 | — | — | — |
| 9 | Verify the data after the migration | Opus 5.5 | medium | parent | 8 | — | Tests and acceptance criteria | — |
| 10 | Review rows 1, 3, 4 and 7 for the final change | gpt-6-astra | high | Codex | 1, 3, 4, 7 | — | Tests and acceptance criteria | — |
| 11 | Review after row 1 | Opus 5.5 | high | subagent | 1 | — | Recheck row 1 output | — |
| 12 | Review after row 2 | Opus 5.5 | high | subagent | 2 | — | Recheck row 2 output | — |
| 13 | Review after row 3 | Opus 5.5 | high | subagent | 3 | — | Recheck row 3 output | — |
| 14 | Review after row 4 | Opus 5.5 | high | subagent | 4 | — | Recheck row 4 output | — |
| 15 | Review after row 5 | Opus 5.5 | high | subagent | 5 | — | Recheck row 5 output | — |
| 16 | Review after row 6 | Opus 5.5 | high | subagent | 6 | — | Recheck row 6 output | — |
| 17 | Review after row 7 | Opus 5.5 | high | subagent | 7 | — | Recheck row 7 output | — |
| 18 | Review after row 8 | Opus 5.5 | high | subagent | 8 | — | Recheck row 8 output | — |
| 19 | Review after row 9 | Opus 5.5 | high | subagent | 9 | — | Recheck row 9 output | — |
| 20 | Review after row 10 | Opus 5.5 | high | subagent | 10 | — | Recheck row 10 output | — |

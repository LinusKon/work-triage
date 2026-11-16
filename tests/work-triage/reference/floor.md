## Work triage

Orchestrator: Opus 5.5 · medium. Reviews: 1, at 4. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Find every place the key's variable name is used (names only, no values) | Sonnet 5.5 | medium | subagent | — | — | Tests and acceptance criteria | — |
| 2 | Create the new key | — | — | user | — | — | — | — |
| 3 | Wire the secret-manager reference into the deploy script | Opus 5.5 | high | subagent | 1, 2 | `deploy.sh` | Tests and acceptance criteria | — |
| 4 | Review row 3 | Opus 5.5 | high | subagent | 3 | — | Tests and acceptance criteria | — |
| 5 | Delete the old `.env` file and revoke the old key | — | — | user | 4 | — | — | — |
| 6 | Deploy | — | — | user | 4 | — | — | — |
| 7 | Verify the deployment and that no value is in the repository or the logs | Opus 5.5 | medium | parent | 5, 6 | — | Tests and acceptance criteria | — |

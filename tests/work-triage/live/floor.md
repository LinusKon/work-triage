## Work triage

Orchestrator: Opus 5.5 · high (not a swarm run; the secret and deploy rows run in the parent). Reviews: 1, at 4. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Find every use of the key's variable name (names only: `rg -o`/`-l` on the name, never print the matched line or any `.env` content) | Opus 5.5 | high | parent | — | — | list of path:line hits of the name only; not Codex or Sonnet: secrets floor, files may hold the value | a value appears in any output → stop, `user` row naming path and variable, treat the key as leaked |
| 2 | Create the new key and store it in the secret manager; give the parent only the reference path | — | — | user | — | — | — | — |
| 3 | Wire the secret-manager reference into the deploy script; remove its `.env` read; dry run of the deploy listing planned actions and the rollback (previous release) | Opus 5.5 | high | parent | 1, 2 | the deploy script, its config | dry run resolves the reference without printing it; `rg` for the old variable source shows no `.env` read; reviewed at 4; not Codex: secrets floor, deploy-script prepare | dry run prints a value → stop, `user` row, treat the new key as leaked |
| 4 | Review row 3: reference handling, no value in diff, dry-run output, rollback; prompt carries the no-values rule | Opus 5.5 | high | subagent | 3 | — | findings with severity; one fix round to row 3 | finding still open after the fix round → stop, report to the user |
| 5 | Delete the old `.env` file and revoke the old key | — | — | user | 6 | — | — | — |
| 6 | Deploy with the reviewed script | — | — | user | 4 | — | — | — |
| 7 | Verify the deployment (health, the key-using path works after revocation) and that no value is in the repository, its history or the logs (match by count or hash, never print) | Opus 5.5 | high | parent | 5, 6 | — | health check and a key-using request succeed; value matches in repo, `git log -p` and logs = 0; not a subagent: production and secret values stay in the parent | a value is found → stop, `user` row naming path and variable, never the value; deploy fails → user decides rollback |

- Floors: 1, 3, 7 secrets (Opus `high`, parent; never Sonnet or Codex); 3 also deploy-script prepare (local floor); 7 also production read-only. Gates: 2 key creation, 5 delete and revocation, 6 deploy — all `user` rows.
- Row 5 starts after 6, not after 4 as the plan's order suggests: revoking the old key before the new deploy is live breaks the running production deployment and removes the rollback. Step numbers are kept; only `Starts after` changes.
- Row 7 starts after 5 so it proves the deployment runs without the old key and that the deleted `.env` left no value behind.
- One review only: row 3 is the sole secrets row with code; its own Opus `high` review covers it. No cross-family final review: secrets never enter a Codex review's scope, and no other code is written.
- Mix: 0 Sonnet, 0 Codex, 4 Opus `high`, 3 user rows, 0 Fable.

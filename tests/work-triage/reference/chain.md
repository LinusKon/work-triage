## Work triage

Orchestrator: Opus 5.5 · medium. Reviews: 0. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Write the shot list and prompts for all four beats | Opus 5.5 | medium | subagent | — | `shots.md` | Tests and acceptance criteria | — |
| 2 | Generate beat 1 (paid); the user approves the take | Opus 5.5 | medium | parent | 1 | `beat1.mp4` | user approves cost and inputs before the call; user accepts the result after | — |
| 3 | Generate beat 2 from beat 1's end frame | Opus 5.5 | medium | parent | 2 | `beat2.mp4` | user approves cost and inputs before the call; user accepts the result after | — |
| 4 | Generate beat 3 from beat 2's end frame | Opus 5.5 | medium | parent | 3 | `beat3.mp4` | user approves cost and inputs before the call; user accepts the result after | — |
| 5 | Generate beat 4 from beat 3's end frame | Opus 5.5 | medium | parent | 4 | `beat4.mp4` | user approves cost and inputs before the call; user accepts the result after | — |
| 6 | Write a script that extracts a clip's last frame and checks its size, with a selftest | gpt-6.1-sol | medium | Codex | — | `last_frame.py` | Tests and acceptance criteria | — |
| 7 | Collect sound references for the four beats | Sonnet 5.5 | medium | subagent | — | `sound.md` | Tests and acceptance criteria | — |
| 8 | Write a script that joins four clips, with a selftest on dummy clips | gpt-6.1-sol | medium | Codex | — | `join.py` | Tests and acceptance criteria | — |
| 9 | Join the real clips and check the cut | Opus 5.5 | medium | parent | 5, 8 | `film.mp4` | Tests and acceptance criteria | — |

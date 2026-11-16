## Work triage

Orchestrator: Fable 5.2 · medium (chain profile, not a swarm run; the session keeps its model and level, and the parent runs every paid link). Reviews: 0. Fix rounds: 1 per link gate.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Shot list and prompts for all four beats | Opus 5.5 | medium | subagent | — | `film/shots.md` | the user reads it | — |
| 2 | Beat 1: generate (paid) | Fable 5.2 | medium | parent | 1 | `film/b1/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 3 | Beat 2 from beat 1's end frame (paid) | Fable 5.2 | medium | parent | 2, 6 | `film/b2/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 4 | Beat 3 from beat 2's end frame (paid) | Fable 5.2 | medium | parent | 3 | `film/b3/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 5 | Beat 4 from beat 3's end frame (paid) | Fable 5.2 | medium | parent | 4 | `film/b4/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 6 | Script: extract a clip's last frame and check its size, with a selftest | gpt-6.1-sol | medium | Codex | — | `tools/last_frame.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 7 | Sound references for the four beats | Sonnet 5.5 | medium | subagent | 1 | `film/sound/` | a link per beat; not Codex: research, not code | — |
| 8 | Script: join four clips, with a selftest on dummy clips | gpt-6.1-sol | medium | Codex | — | `tools/join.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 9 | Join the real clips with row 8's script and check the cut | Fable 5.2 | medium | parent | 5, 7, 8 | `film/cut/` | the user watches the cut | — |

Waves: {1, 6, 8}, {2, 7}, {3}, {4}, {5}, {9}. Links 2 → 3 → 4 → 5 → 9 form the chain's path and never share a wave; each link starts only after the user accepted the take before it.

Floors and gates:

- Rows 2-5: paid-run floor. Each runs in the parent, with no automatic retries, and carries the gate in full in `Check`. The parent shows endpoint, parameters and cost estimate with the inputs (the prompt from row 1; from row 3 on, the end frame extracted and size-checked with row 6's script) before every call. A subagent cannot ask the user, so no side row generates or spends.
- Rows 2-5 and 9 are Fable 5.2 · medium only because the chain binds them to the parent; that is the session's model and level, not lifting, and no row is raised to Fable on section 3's condition. If the session runs at another level, these rows take that level.
- Row 1: Opus 5.5 `medium` for taste (prompts for a video model); it differs from the parent, so it is a subagent (`anthropic/claude-opus-5-5:medium`). Never Codex. Rows 2-5 build on it, and the user reads it before row 2.
- Rows 6 and 8: bounded code with a selftest that stands alone and no floor, so Codex goes first; selftests use dummy clips, never a link's output. If Codex is unavailable: Sonnet 5.5 `high` (`anthropic/claude-sonnet-5-5:high`).
- Row 7: chooses no approach and a wrong link is cheap to spot (`anthropic/claude-sonnet-5-5:medium`).
- No review rows: the user's gate is each link's check, and the user watches the joined cut.
- A rejected take is fixed by redoing that link from the same input; every later link is then stale and redone in order, each paid call with a new approval. After two fix rounds on one link the parent stops and asks the user.

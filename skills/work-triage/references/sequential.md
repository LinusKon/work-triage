# Sequential profile: chains

Read this when the plan holds a chain. Detection in short is in `spawn.md` `## Chains`; waves and ownership in
`references/schedule.md`; review points in `references/verify.md`. This profile wins over the swarm count: a
plan whose backbone is a chain the parent must run (paid or gated links) is no swarm run, whatever its waves.
The parent keeps its model and runs the links; side rows are subagent or Codex rows.

## Recognise a chain

A chain is the path of artefact dependencies: link n needs an artefact that exists only after link n-1 has run
**and passed its gate**. A link may have further predecessors (a tool it uses) and further successors (a check
of its result); it is still a link. Examples: a film where each clip starts from the approved end frame of the
clip before; a database migration in steps, where step n runs on the schema step n-1 left; a training run
resumed from checkpoint n-1; a document where each chapter builds on the chapter the user approved before it.

Not a chain: rows that only share a contract (settle the contract first, then run them as a wave), or rows
that need the same input but not each other's output.

## Why a chain is never split

- Splitting cannot help: link n has nothing to start from until link n-1 is done. A wave would run link n on a
  guess, and the guess is thrown away once the real artefact exists.
- More agents do not help: multi-agent setups lose on sequential work (up to −70 % on sequential planning,
  PlanCraft; every variant also lost on SWE-bench Verified; Kim et al., arXiv 2512.08296). A chain has one
  row in flight; extra agents only add hand-offs.
- More reviews do not help: a swarm review inside a chain reads one link at a time, which its gate already
  checks. Check the end state of each link, not every step inside it (Anthropic, "Building effective agents"
  and "How we built our multi-agent research system").

## Run a chain

- One link at a time. The next link starts only after the current one passed its gate.
- The check of a link is its end state: the artefact the next link starts from (the frame, the schema, the
  checkpoint, the approved chapter). No other link shares its wave, so a link runs its own check, suite included.
- The plan names who judges it: the user for taste and for paid results; a script for the rest (frame size,
  migration dry run, checkpoint loads and evaluates).
- No review rows inside the chain; a review at the end, if the plan has one, reads the joined result.

## Beside the chain

While the current link runs, everything that does not need its artefact runs as a wave of its own:

- tools and scripts the chain will use, each with its own selftest (on dummy data, never on a link's output);
- research and references;
- checks of finished links (continuity, size, sound), read-only, each writing its own report;
- every input of the next link that does not need the current artefact.

To find those inputs, list the inputs of link n+1 and ask for each: "does it need the artefact of link n?"
No: it runs now, beside link n. Yes: it waits. Prompt text, references and shot data usually say no; framing
that has to match link n's last frame says yes.

## Paid and gated links stay with the parent

A link that spends money, writes production data or needs the user's approval runs as `parent`: a subagent
cannot ask the user, so it would either stop or run without the gate. Every paid link carries the gate in
full, in its `Check` cell or as a `user` row right before it: "user approves cost and inputs before the call;
user accepts the result after". Side rows never generate, migrate or spend.

## A fix inside a chain

- A link that fails its gate, or a side check of a finished link that finds a fault, is fixed by **redoing that
  link** from the same input, never by patching a later link to hide it.
- Every link after the redone one is stale: it started from the old artefact. Redo them in order; their
  approved inputs (prompts, references) stay valid unless the check says otherwise.
- Catch faults early: the check of link n runs beside link n+1, so at most one later link is lost.
- `Fix rounds` in the plan line counts per link gate in a chain. The cap of two fix rounds per link holds
  (`spawn.md` `## During the run`); after that the parent stops and asks the user, usually to change the input
  of the link (the prompt, the step plan).

## In the plan table

The links form a path in `Starts after`: each link names the link before it, plus any tool it needs; checks of
a link name it too. No two links share a wave. Side rows name only what they need, so they land in the wave
of the link they run beside. Paid links are `Run as` `parent` and carry the full gate text in `Check`.

## Worked example: a short film

Two scenes, five beats. Each beat's clip starts from the end frame of the previous beat's approved take.
Scene 1: beats 1-2. Scene 2: beats 3-5. Beat 4 has a speed ramp.

Orchestrator: Opus 5.5 · medium (chain profile, not a swarm run; the parent runs every paid link).
Reviews: 0. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Shot list and prompts for all five beats, beat constraints in the prompts | Opus 5.5 | medium | parent | — | `film/shots.md` | the user reads it | — |
| 2 | Script: extract a clip's last frame and check its size, with a selftest | gpt-6.1-sol | medium | Codex | — | `tools/last_frame.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 3 | Script: join clips, with a selftest on dummy clips | gpt-6.1-sol | medium | Codex | — | `tools/join.py`, its test | its selftest | fails twice → gpt-6-astra high |
| 4 | Sound references for the five beats | Sonnet 5.5 | medium | subagent | 1 | `film/sound/` | a link per beat | — |
| 5 | Beat 1 (scene 1): generate (paid) | Opus 5.5 | medium | parent | 1 | `film/b1/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 6 | Check beat 1 against the shot list | Sonnet 5.5 | medium | subagent | 2, 5 | `film/checks/b1.md` | report with frame size, length, sound | — |
| 7 | Beat 2 (scene 1) from beat 1's end frame (paid) | Opus 5.5 | medium | parent | 2, 5 | `film/b2/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 8 | Check beat 2 against the shot list | Sonnet 5.5 | medium | subagent | 7 | `film/checks/b2.md` | report | — |
| 9 | Beat 3 (scene 2) from beat 2's end frame (paid) | Opus 5.5 | medium | parent | 7 | `film/b3/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 10 | Check beat 3 against the shot list | Sonnet 5.5 | medium | subagent | 9 | `film/checks/b3.md` | report | — |
| 11 | Beat 4 (scene 2) from beat 3's end frame, speed ramp (paid) | Opus 5.5 | medium | parent | 9 | `film/b4/` | user approves cost and inputs before the call; user accepts the result (take and ramp) after | three takes rejected → rewrite the prompt |
| 12 | Check beat 4 against the shot list | Sonnet 5.5 | medium | subagent | 11 | `film/checks/b4.md` | report | — |
| 13 | Beat 5 (scene 2) from beat 4's end frame (paid) | Opus 5.5 | medium | parent | 11 | `film/b5/` | user approves cost and inputs before the call; user accepts the result after | three takes rejected → rewrite the prompt |
| 14 | Join the approved clips with row 3's script, check beat 5 and the cut | Opus 5.5 | medium | parent | 3, 4, 12, 13 | `film/cut/` | the user watches the cut | — |

Waves: {1, 2, 3}, {4, 5}, {6, 7}, {8, 9}, {10, 11}, {12, 13}, {14}. Six of them hold two or more rows, yet the
plan is no swarm run: the links 5, 7, 9, 11, 13 form the chain's path and never share a wave; each check runs
beside the next link.

Beat constraint fixed before generation: beat 4's speed ramp is written into its prompt in row 1 and produced
by the video model. It is not added by retiming in post, because retiming distorts the generated sound. So
the ramp is judged at the gate of row 11, not in row 14.

Beat 2, step by step:

- **The parent** runs row 2's script on beat 1's accepted take and checks the end frame's size. It shows the
  user the cost and inputs (frame, beat 2's prompt from row 1), starts the paid generation only after the
  user approves, and shows the takes for the user to accept. The accepted take and its end frame are row 7's
  end state.
- **Beside it**, as one wave: row 6 checks beat 1 (read-only, its own report). Row 4, if still running, keeps
  collecting sound. Beat 3's prompt may still be edited where it does not depend on beat 2 (dialogue, sound).
- **Waiting:** beat 3 (row 9) needs beat 2's end frame; any change to beat 3's framing that must match how
  beat 2 ends; the join (row 14).
- If row 6 finds a fault in beat 1, the parent redoes row 5, and beat 2 is redone from the new end frame.

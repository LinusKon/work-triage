---
name: work-triage
description: "Decides who runs each piece of work and at what level: Claude Sonnet 5.5, Opus 5.5 or Fable 5.2 with a thinking level, or Codex (gpt-6.1-sol, gpt-6-luna, gpt-6-astra, gpt-6.1-terra) with a reasoning level. Keeps the main session strong (Opus 5.5 high), runs work that fits one session solo, and for large builds orchestrates few, cheap, batched workers with an explicit model each; holds floors and user gates, and ends with a spec check and a hardening pass. Load before presenting any plan of three or more steps or any plan with a step that spends money, touches secrets or leaves the machine; before spawning subagents or a swarm; whenever work goes to Codex (implementation, review or second opinion, checks of a local app); and when the user asks which model or level a task needs."
metadata:
  version: 2.6.0
---

# Work triage

The best result for the fewest tokens: a strong head, cheap hands. The session keeps its model and level (Opus 5.5
`high` is the default) and saves on the workers, never on itself: in the study behind this skill
(`references/calibration.md`) sessions lowered to `medium` drew major review findings in 2 of 9 runs, sessions at
`high` in 0 of 9.

## 1. Size first

- **The work fits one session** (roughly up to ten files or a thousand lines to write, no long research): do it
  solo, in order. Do not delegate any of it: at this size every form of delegation measured cost more than doing
  the work (three rounds, seven tasks). Write `Triage: 1 Opus 5.5·high (parent), solo.` with the session's real
  model and level, add a gate only for an action the plan has, then go to sections 5 and 6. Sections 3 and 4 still
  hold.
- **The work is larger** (more than one context holds comfortably, many independent modules, a long research
  sweep), or the user asks for subagents: orchestrate it as section 2 says.

## 2. Orchestrating a build

A session that writes everything itself pays for its growing context on every turn; workers start small. But each
spawn has a fixed price (its system prompt and brief, about 12k tokens), and a spawn without `model` inherits the
parent's model and level. So:

1. **Contract first.** The parent writes what the workers share: interface, names, formats, error rules, test
   conventions, shared helpers (and writes those helpers itself). In omp it goes into the batch's `context`, which
   lands once in every worker's system prompt; a long contract goes into a file that `context` names.
2. **Few fat workers.** Group small modules into batches of four to six per worker; a large module gets its own.
   Twenty thin workers cost more than five fat ones. One writer per file; batches share no file.
3. **Route by agent type (omp).** This skill ships three agents in its `agents/` folder; if `wt-worker` is not
   among the task tool's agents, copy them with one command (`cp <this skill>/agents/*.md .omp/agents/`; say so in
   the report). With these agents you need no other reference of this skill and no settings preflight. Set `agent`
   on each item and no `model`; the agent carries its model, level and the rules of sections 5 and 6:
   - `wt-worker` (Sonnet 5.5 `medium`): what, where and how to check are written down; no design others depend
     on; a mistake shows in a test. Modules, CLIs, tests and docs to a spec, a bug with a failing test.
   - `wt-worker-hard` (Sonnet 5.5 `high`): the same, dense with edge cases (parsers, number formats, rounding,
     time, concurrency) or with an approach to choose inside the spec.
   - `wt-reviewer` (Opus 5.5 `high`): the review at the join and the security review; it does not edit.
   - Anything else names its `model` with level, never `effort`: Opus 5.5 `medium` for taste (copy, UI polish,
     prompts for image and video models), Opus 5.5 `high` for floors (section 3). A spawn with neither a fitting
     agent nor a `model` inherits the parent's model and level. Other harnesses, Codex rows, `xhigh` and the plan
     table: [spawn.md](references/spawn.md).
4. **Short briefs.** Save the spec to one file and number its parts; a brief is at most ten lines: the files the
   worker owns and the parts of the spec file it implements, by number. Do not paste spec text, rules the agent
   already carries, or the contract into briefs. Write `solutionSpace` truthfully (`design given, spec'd`): omp uses
   it to set thinking.
5. **One batch, one wait.** Spawn the whole wave as one `tasks[]` call and wait once; do not poll, and do not work
   on the workers' files meanwhile.
6. **The parent does not re-read the workers' code.** It reads the five-line reports, runs the whole suite once
   and reads failures only. A failing module goes back to its author once (`write agent://<name>`); after that the
   parent fixes it.
7. **One review at the join:** one `wt-reviewer` checks the merged result against the contract and the hardening
   list, not file by file. One fix round. Security files get section 4's review instead.

**Fable 5.2** only after Opus `xhigh` had full context and failed on architecture or a root cause that spans several
systems, or for frontier-hard work longer than one context. Never for security, spec'd work, research, orchestration
or triage: there it costs more for the same result (`references/facts.md`).

## 3. Floors

A step that touches a floor gets at least this, solo or not. Look for floors a plan does not name.

| Touches | Floor |
|---|---|
| Deciding an interface or data model others build on; numbers or conclusions the user will act on | Opus `high`. Numbers: two methods where they could disagree |
| Architecture across systems; a major migration; a root cause after one failed fix | Opus `high`; across systems or with no lead, Opus `xhigh`, then Fable 5.2 (section 2) |
| Security (auth, signatures, replay, tokens, crypto, input sanitising, paths, URLs, injection, CORS/CSP) or secrets (references, key handling) | Opus `high`, never Codex, Sonnet or Fable; one review, section 4 |
| Creating, rotating or deleting a key; a secret value found anywhere | a `user` step naming path and variable, never the value; a found value counts as leaked |
| Production or personal data | read-only: parent; any write: Opus `high`, parent, target named first; personal data stays out of subagent prompts |
| Irreversible (deletes git cannot restore, migrations on real data, deploys, posting, messages) | prepare at Opus `high` (dry run, backup, rollback), the action is a `user` gate, then verify in the parent |
| Paid runs (APIs, generation, load tests, batch jobs) | estimate cost and inputs, the user approves, the parent runs, no automatic retries |
| Scripts or skills that act on their own (spend, commit, push, deploy, comment, save) | parent prepares and lists the actions; the run is a `user` gate unless the tool's own scope rule allows it |
| No check exists; unclear goal | write a check first, or clarify first |

If `references/local.md` exists, read it: it holds this installation's own floors and gates.

**Escalation.** A check that fails once: same model, one level up. Fails again with full context: next model up
(Sonnet → Opus `high` → `xhigh`), then Fable only under section 2's condition. Security stops at Opus `xhigh`, then
the user.

## 4. Gates and the security review

- **Gates:** push, PR, merge, deploy, paid calls, key changes and anything irreversible happen only on the user's
  word; a push follows a check of the staged diff for secret values. A noted approval holds for this session only.
- **Security or secrets work gets one review,** by `wt-reviewer` (a fresh Opus 5.5 `high` subagent), scoped to the floor files and
  their tests, with the spec and section 6's hardening list. Its prompt carries the no-values rule. Raise it to
  `xhigh` only when the review finds a major issue or no test covers the risky path. Never Codex, Sonnet or Fable.
  One fix round.
- Where a spec is ambiguous in a way that is unsafe, take the safe reading and say so in one line.

## 5. Work economically

Output tokens are about half of a run's cost and what enters the context about a third; spend them on the result.
- Read only what the step needs; never re-read a file already in context; use search and line ranges.
- Write each file once, complete; no write-then-rewrite cycles. Batch independent tool calls in one turn.
- Keep tool output small: quiet test runs, `tail`, counts instead of dumps.
- No code or plan restated in messages; no files the spec does not ask for.
- The final report: at most ten lines: what was done, the check commands with their result, open points.

## 6. Spec check and hardening before done

- Before writing code, turn every testable sentence of the spec into a test: exact formats, boundaries (`<` against
  `<=`), every error case it names, every unit and constant.
- **Exactly the spec, not stricter.** Accept everything the spec's wording accepts and reject only what it says to
  reject. Half of the major defects in the large-build study were restrictions nobody asked for: an empty or
  repeated list refused, digits limited to ASCII where the spec said `\d`, a keyword argument made positional-only,
  an error for a case the spec gives a result for. When hardening tempts you to add a check, find the spec sentence
  that demands it; without one, the input is valid.
- **Hardening pass.** The major defects found in the study all sat in code whose tests passed. For everything the
  code accepts, try the extremes and add a test for each that applies:
  - values: empty, huge, at the limits of int and float (sums and means that overflow), NaN and infinity, negative
    and zero, non-ASCII, wrong types;
  - files and paths: `..`, symlinks, a file swapped between check and use (open once and work on the descriptor,
    never check then open), leftover temporary files, partial writes;
  - failures: every error path ends in the documented exit code and message, never a traceback.
- Before reporting done, walk the spec once, sentence by sentence, and point each to a passing test or a command
  output; fix what has none. Then run the whole suite once.

## References

- Spawning in detail: [spawn.md](references/spawn.md); harness: [harness-omp.md](references/harness-omp.md),
  [harness-claude-code.md](references/harness-claude-code.md); Codex rows: [codex-implementation.md](references/codex-implementation.md),
  [codex-review.md](references/codex-review.md), [codex-computer-use.md](references/codex-computer-use.md).
- [schedule.md](references/schedule.md), [verify.md](references/verify.md), [sequential.md](references/sequential.md),
  [examples.md](references/examples.md), [calibration.md](references/calibration.md), [facts.md](references/facts.md).

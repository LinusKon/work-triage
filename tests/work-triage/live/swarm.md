## Work triage

Orchestrator: Fable 5.2 · medium (swarm run). Reviews: 2, at 10 and 11. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Decide the plugin interface and write it down: base class, registration, CLI flag, error contract, dependency list | Opus 5.5 | high | subagent | — | `docs/plugin-interface.md`, `exporters/base.py`, `exporters/__init__.py` (registry), `pyproject.toml` | the parent accepts it before 2-9; reviewed at 10; not Codex: interface floor, a design | a format cannot be expressed through it → Opus 5.5 xhigh |
| 2 | CSV format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `exporters/csv.py`, its test | its tests | fails twice → gpt-6-astra high |
| 3 | JSON format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `exporters/json.py`, its test | its tests | fails twice → gpt-6-astra high |
| 4 | YAML format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `exporters/yaml.py`, its test | its tests | needs a dependency row 1 did not list → report to the parent, no edit of `pyproject.toml`; fails twice → gpt-6-astra high |
| 5 | XML format plugin, with its own tests (escaping, illegal element names and characters) | gpt-6.1-sol | high | Codex | 1 | `exporters/xml.py`, its test | its tests | fails twice → gpt-6-astra high |
| 6 | Markdown format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `exporters/markdown.py`, its test | its tests | fails twice → gpt-6-astra high |
| 7 | HTML format plugin, with its own tests (escaping of every value and attribute) | gpt-6.1-sol | high | Codex | 1 | `exporters/html.py`, its test | its tests, including values with `<`, `&`, quotes | the output is served to browsers with untrusted data → security floor: Opus 5.5 high plus its own Opus 5.5 xhigh review; fails twice → Opus 5.5 high |
| 8 | Reference page per plugin from the docstrings | Sonnet 5.5 | medium | subagent | 2, 3, 4, 5, 6, 7 | `docs/reference/{csv,json,yaml,xml,markdown,html}.md` | six pages, every documented option present, the parent reads the diff; not Codex: moving text, not code | a docstring is missing or contradicts the interface → report to the parent; the fix round at 10 changes a docstring → same author redoes that page |
| 9 | README section with examples for users | Opus 5.5 | medium | subagent | 1 | `README.md` (export section) | the parent runs each example command after rows 2-7 land; read at 11 | an example's output differs → same author corrects it |
| 10 | Review the merged plugins against the interface and run the full test suite | gpt-6-astra | high | Codex | 2, 3, 4, 5, 6, 7 | — | findings with severity, suite output attached | suite still red after the fix round → one Fable 5.2 high subagent or the user |
| 11 | Final review of the whole change | Opus 5.5 | high | subagent | 8, 9, 10 | — | findings with severity | — |
| 12 | Push and open the pull request | — | — | user | 11 | — | — | — |

- Waves: 1 · then 2-7 and 9 (seven rows, one batch) · then 8 and 10 · then 11 · then the gate at 12. The wave of 2-7 makes this a swarm run.
- Row 1 is Opus `high`, not Fable: an interface floor inside one tool, not architecture across systems. The orchestrator may write it itself as the contract the rows share; either way its content goes into the `context` of the next wave. It also owns the shared files (registry, `pyproject.toml`) so no plugin row writes them.
- Rows 2-7 are bounded, have their own tests and no floor, so Codex goes first; 5 and 7 get `high` for dense escaping cases. One file set each; they skip the full suite, which runs once at 10.
- Row 7's doubt is in `Escalate if`: escaping in an export file is treated as correctness, not as the security floor, unless the output reaches a browser with untrusted data.
- Row 8 waits for the docstrings; row 9 does not: it is written from the interface, and its examples are checked against the real commands afterwards. Opus `medium` for copy, Sonnet `medium` for text moved with a count check.
- No review per plugin: leaf rows with tests are read from their test output. Row 10 is the join, with one fix round that goes to the authors. Row 11 is Claude because most of the code is Codex's; it also covers the floor row 1 and the docs.
- Row 12 is a gate: no model floor, only on the user's word, after the parent's staged-diff secret check.
- File names are placeholders until row 1 fixes them; the repository was not read for this triage.
- omp `model` per row: 1 and 11 `anthropic/claude-opus-5-5:high`, 9 `anthropic/claude-opus-5-5:medium`, 8 `anthropic/claude-sonnet-5-5:medium`; Codex rows pass model and level explicitly.
- Mix: 1 Sonnet, 1 Opus `medium`, 2 Opus `high`, 7 Codex, 0 Fable rows.

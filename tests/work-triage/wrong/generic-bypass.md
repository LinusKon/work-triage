<!-- Expected failure: Codex first bypassed without a reason; four points. -->
## Work triage

Orchestrator: Opus 5.5 · high (swarm run). Reviews: 2, at 10 and 11. Fix rounds: 1.

| # | Row | Model | Level | Run as | Starts after | Owns | Check | Escalate if |
|---|---|---|---|---|---|---|---|---|
| 1 | Decide the plugin interface and write it down | Opus 5.5 | high | subagent | — | `docs/interface.md` | Parent accepts the contract before consumers start; reviewed at 10 | — |
| 2 | Implement the CSV format plugin, with its own tests | gpt-6.1-sol | medium | subagent | 1 | `plugins/csv.py`, `tests/test_csv.py` | requires pytest | — |
| 3 | Implement the JSON format plugin, with its own tests | gpt-6.1-sol | medium | subagent | 1 | `plugins/json.py`, `tests/test_json.py` | requires pytest | — |
| 4 | Implement the YAML format plugin, with its own tests | gpt-6.1-sol | medium | subagent | 1 | `plugins/yaml.py`, `tests/test_yaml.py` | requires pytest | — |
| 5 | Implement the XML format plugin, with its own tests | gpt-6.1-sol | medium | subagent | 1 | `plugins/xml.py`, `tests/test_xml.py` | requires pytest | — |
| 6 | Implement the Markdown format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `plugins/markdown.py`, `tests/test_markdown.py` | Tests and acceptance criteria | — |
| 7 | Implement the HTML format plugin, with its own tests | gpt-6.1-sol | medium | Codex | 1 | `plugins/html.py`, `tests/test_html.py` | Tests and acceptance criteria | — |
| 8 | Write a reference page per plugin from the docstrings | Sonnet 5.5 | medium | subagent | 2, 3, 4, 5, 6, 7 | `docs/plugins.md` | Tests and acceptance criteria | — |
| 9 | Write the README section with examples for users | Opus 5.5 | medium | subagent | 1 | `README.md` | Tests and acceptance criteria | — |
| 10 | Review the merged plugins against the interface and run the full test suite | Opus 5.5 | high | subagent | 2, 3, 4, 5, 6, 7 | — | Tests and acceptance criteria | — |
| 11 | Review the whole change | gpt-6-astra | high | Codex | 8, 9, 10 | — | Tests and acceptance criteria | — |
| 12 | Push and open the pull request | — | — | user | 11 | — | — | — |

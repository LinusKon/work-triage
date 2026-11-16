Build `tasktrack`, a task tracker library with a command line, in this repository: Python 3.9 standard library only,
tests with `unittest` under `tests/`. Run to the user gate and stop. The interface is fixed.

**1. Model** (`tasktrack/model.py`). `class TaskError(ValueError)`. A task is a dict with exactly these keys:
`id` (int ≥ 1), `title` (str), `status` (`"open"` or `"done"`), `priority` (int 1–5), `tags` (list of str), `due`
(`"YYYY-MM-DD"` or `None`), `created` (`"YYYY-MM-DD"`). `normalize(task) -> dict` returns a new, valid task or raises
`TaskError`: the title is stripped and must then have 1 to 200 characters; `status` defaults to `"open"`, `priority`
to `3`, `tags` to `[]`, `due` to `None` when the key is missing; tags are stripped, lowercased, de-duplicated and
sorted, and each must match `[a-z0-9-]+`; dates must be real calendar dates in exactly the form `YYYY-MM-DD`;
booleans are not ints; an unknown key raises `TaskError`.

**2. Store** (`tasktrack/store.py`). `Store(path)` keeps tasks in one JSON file `{"next_id": <int>, "tasks": [...]}`.
A missing file is an empty store with `next_id` 1; a file that is not valid JSON of that shape raises `TaskError`.
`add(title, *, today, priority=3, tags=(), due=None) -> dict` (the new task, `created` = `today`, `id` = `next_id`,
which then grows by one; ids are never reused), `get(id) -> dict`, `update(id, **changes) -> dict` (any of `title`,
`status`, `priority`, `tags`, `due`; the result is normalized; `id` and `created` cannot be changed), `remove(id)`,
`all() -> list` sorted by `id`. An unknown id raises `TaskError`. Every change is saved at once, through a temporary
file in the same folder and `os.replace`; no temporary file is left behind; returned tasks are copies.

**3. Query** (`tasktrack/query.py`). `parse(text) -> callable` returns a predicate over tasks; `TaskError` on a
syntax error. Grammar, case-sensitive keywords, whitespace between tokens optional around parentheses and operators:
- `status:open`, `status:done`; `tag:NAME` (the task has that tag); `due:none` (no due date).
- `priority OP N` and `due OP YYYY-MM-DD` with `OP` one of `=`, `!=`, `<`, `<=`, `>`, `>=`; a task without a due date
  matches no `due OP DATE` term, not even `!=`.
- `title~"TEXT"`: the title contains `TEXT`, ignoring case; `TEXT` may hold any character except `"`.
- `not X`, `X and Y`, `X or Y`, parentheses; `not` binds tightest, then `and`, then `or`.
- The empty or all-whitespace query matches every task. An unknown field, a bad number or date, an unclosed
  parenthesis or quote, a missing operand and trailing tokens are syntax errors.

**4. Recurrence** (`tasktrack/recur.py`). `next_due(due, rule) -> str` with dates as `YYYY-MM-DD`: `daily` (+1 day),
`weekly` (+7 days), `monthly` (same day next month, the last day of that month when it is shorter), `every N days`
(N an integer ≥ 1), `weekdays` (the next day that is Monday to Friday). Anything else raises `TaskError`.

**5. Formats.** Each module has `dumps(tasks) -> str` and `loads(text) -> list` of normalized tasks (`TaskError` on
bad input); `loads(dumps(tasks)) == tasks` for normalized tasks.
- `tasktrack/fmt_jsonl.py`: one JSON object per line, keys sorted; blank lines are ignored on load.
- `tasktrack/fmt_csv.py`: the `csv` module, header `id,title,status,priority,tags,due,created`, tags joined by one
  space, an empty `due` cell for `None`; a wrong header raises `TaskError`.
- `tasktrack/fmt_md.py`: one line per task, `- [ ] TITLE` or `- [x] TITLE` (done), followed in this order by
  ` #TAG` for every tag, ` !PRIORITY`, ` @DUE` when due is set, ` ^CREATED`, ` (ID)`. Example:
  `- [x] Buy milk #home #shop !2 @2026-01-05 ^2026-01-01 (7)`. Lines that are empty are ignored on load; any other
  line that does not have this shape raises `TaskError`. Titles never contain ` #`, ` !`, ` @`, ` ^` or ` (` in
  this format: `dumps` raises `TaskError` for such a title.

**6. Report** (`tasktrack/report.py`). `summary(tasks, today) -> dict` with `total`, `open`, `done`, `overdue` (open
tasks whose due date is before `today`), `by_priority` (a dict with the keys 1 to 5, open tasks only) and `by_tag`
(a dict of tag to count over open tasks, keys sorted). `render(summary) -> str`: the lines `total: N`, `open: N`,
`done: N`, `overdue: N`, `priority 1: N` … `priority 5: N`, then `tag NAME: N` per tag in key order, joined by
newlines, no trailing newline.

**7. Command line** (`python3 -m tasktrack --file PATH COMMAND …`). `add TITLE [--priority N] [--tag T]…
[--due DATE] --today DATE` prints the new id; `list [--query Q] [--format jsonl|csv|md]` (default `md`) prints the
matching tasks in id order; `done ID` and `rm ID` print nothing; `next ID RULE` sets the task's due date to
`next_due` of its current one (a task without a due date is an error) and prints the new date; `import FORMAT FILE
--today DATE` adds every task of the file as a new task (new ids, `created` = `today`, other fields kept) and prints
how many; `report --today DATE` prints `render(summary(...))`. Every `TaskError`, an unreadable file and bad
arguments exit with status 2 and one line on stderr, never a traceback.

**8. Docs.** `docs/<module>.md` for `model`, `store`, `query`, `recur`, `formats`, `report` and `cli` (what it does,
its functions or commands, one example each) and a README with a short tour. `tests/test_<module>.py` per module.

Steps: 1. Model and the conventions the modules share. 2. Store, query, recurrence, the three formats, report, each
with tests. 3. The command line with tests. 4. Docs and README. 5. Review of the merged result against this
specification and the full suite. 6. Push and open the PR (no remote: a user gate).

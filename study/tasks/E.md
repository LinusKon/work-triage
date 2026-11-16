Build `csvstats` in this repository: Python 3.9 standard library only, tests with `unittest` under `tests/`. Run to
the user gate and stop. The interface is fixed:

- `csvstats.stats.summarize(header, rows) -> dict`: `header` is a list of column names, `rows` a list of lists of
  strings. Returns one entry per column, keyed by name. A cell is empty when it is empty after stripping whitespace;
  empty cells are skipped and counted as `missing`. A column is `numeric` when every non-empty cell parses with
  `float()` and none is a NaN or infinity spelling; then its entry is `{"type": "numeric", "count", "missing",
  "min", "max", "mean", "median"}` (median of an even count: the mean of the middle two). A column with non-empty
  cells that is not numeric is `{"type": "text", "count", "missing", "unique", "top"}` where `unique` counts distinct
  stripped values and `top` is the most common stripped value (ties: the smallest in Python string order). A column
  with no non-empty cell is `{"type": "empty", "count": 0, "missing": <n>}`.
- CLI `python3 -m csvstats FILE [--columns A,B] [--format text|json] [--delimiter X]`: reads `FILE` with the `csv`
  module (first row is the header), summarises every column or only the named ones in the given order.
  `--format json` (default `text`) prints `json.dumps(result, sort_keys=True)` of the selected columns. Text prints
  one line per column: `<name>: <type> key=value …` with keys in the order listed above and numbers formatted with
  `format(x, ".6g")`. Exit status 2 with a message on stderr for: a missing or empty file, an empty or duplicate
  header name, an unknown column in `--columns`, a row whose field count differs from the header (the message names
  the row's line number as the `csv` reader reports it).

Steps: 1. `csvstats/stats.py` with tests. 2. `csvstats/__main__.py` with tests. 3. README usage section with one
example per output format. 4. Push and open the PR (no remote: a user gate).

Build `dataops`, a toolkit of record operations, in this repository: Python 3.9 standard library only, tests with
`unittest` under `tests/`. Run to the user gate and stop. The interface is fixed.

**Core.** Rows are a list of dicts (JSON objects) whose values are strings, numbers, booleans or `None`.
- `dataops/registry.py`: `class OpError(ValueError)`; `register(name, fn)` (a name already registered raises
  `OpError`); `get(name)` (unknown raises `OpError`); `names()` sorted.
- Every operation lives in `dataops/ops/<name>.py` as `run(rows, **params) -> list[dict]` and is registered under
  `<name>` when `dataops` is imported. It never changes its input (rows and row dicts are copied). A missing
  required parameter, an unknown parameter or a parameter of the wrong type raises `OpError`. A named field that a
  row does not have raises `OpError` unless the operation says otherwise. "Numeric" means `int` or `float` but not
  `bool`, and not NaN or infinity.
- `dataops/pipeline.py`: `run_pipeline(rows, steps)`; a step is a dict `{"op": <name>, ...params}`; a failing step
  raises `OpError` whose message starts with `step <i> (<op>): ` (`i` counts from 1).
- CLI: `python3 -m dataops PIPELINE.json INPUT.json` prints `json.dumps(result, sort_keys=True)`; `python3 -m dataops
  --list` prints the operation names, one per line, sorted. Unreadable or invalid JSON files, an input that is not a
  list of objects, and every `OpError` exit with status 2 and one line on stderr, never a traceback.
- `docs/ops/<name>.md` for every operation: what it does in one line, its parameters, one example with input and
  output. `tests/test_<name>.py` for every operation.

**Operations** (20):
1. `select(fields)`: keep only `fields` (a list of names), in that order.
2. `drop(fields)`: remove `fields`; a field a row lacks is ignored.
3. `rename(mapping)`: `{old: new}`; the row keeps its field order; a `new` that equals another existing field of the
   row raises `OpError`.
4. `filter_eq(field, value)`: keep rows whose value equals `value`; `1` equals `1.0`, but a boolean equals only a
   boolean. Rows without the field are dropped.
5. `filter_range(field, min=None, max=None)`: keep rows whose numeric value lies within the inclusive bounds; at
   least one bound is required. Rows whose value is missing, `None` or not numeric are dropped.
6. `sort(by, descending=False)`: stable sort by the list of fields `by`. `None` sorts before every other value
   (after, when `descending`). A field holding both strings and numbers raises `OpError`; booleans are not sortable
   and raise `OpError`.
7. `dedupe(fields=None)`: keep the first row of each distinct combination of `fields` (all fields when `None`); a
   missing field counts as `None`; `1` and `1.0` are the same, `True` and `1` are not.
8. `limit(n, offset=0)`: skip `offset` rows, keep the next `n`; both are integers ≥ 0 (not booleans).
9. `fill(field, value)`: set `field` to `value` where it is missing or `None`.
10. `cast(field, to)`: `to` is `"int"`, `"float"`, `"str"` or `"bool"`. `None` stays `None`. `int`: from an int, a
    float with an integral value, or a string matching `[+-]?\d+` after stripping. `float`: from a number or a
    string `float()` accepts, except NaN and infinity. `str`: a string stays, a boolean becomes `"true"` or
    `"false"`, a number becomes `json.dumps(value)`. `bool`: from a boolean or one of the strings `true`, `false`,
    `1`, `0`, `yes`, `no` (any case, stripped). Anything else raises `OpError` naming the row's index (from 0).
11. `concat(fields, into, sep="")`: join the string values of `fields` with `sep` into the new field `into`; a
    non-string value or an existing `into` raises `OpError`.
12. `split(field, sep, into)`: split the string value at `sep` into exactly `len(into)` parts (the last part keeps
    any further separators) and store them in the new fields `into`; fewer parts, an empty `sep`, a non-string
    value or an existing target field raise `OpError`. The source field stays.
13. `text(field, mode)`: `mode` is `upper`, `lower`, `strip` or `title`; `None` stays `None`; a non-string raises
    `OpError`.
14. `replace(field, old, new, count=None)`: replace `old` by `new` in the string value, at most `count` times
    (a positive integer) when given; an empty `old` or a non-string value raises `OpError`; `None` stays `None`.
15. `group_count(by, into="count")`: one row per distinct combination of the fields `by`, in order of first
    appearance, holding the `by` fields and the number of rows in `into`.
16. `group_sum(by, field, into="sum")`: as `group_count`, with the sum of the numeric values of `field`; missing and
    `None` values are skipped (a group with none sums to `0`); a non-numeric value raises `OpError`. The sum is an
    `int` when every summed value is an `int`, else a `float` computed with `math.fsum`; a sum that is not a finite
    float raises `OpError`.
17. `group_stats(by, field)`: as `group_sum`, adding the fields `count` (numeric values seen), `min`, `max` and
    `mean` (`None` for all three when `count` is 0); a mean that is not a finite float raises `OpError`.
18. `top(n, by, descending=True)`: the `n` rows with the largest (smallest when not `descending`) numeric value of
    the field `by`; ties keep input order; rows whose value is missing or `None` are left out; a non-numeric value
    raises `OpError`.
19. `round(field, digits=0)`: round the numeric value half away from zero to `digits` decimals (an integer ≥ 0);
    with `digits=0` the result is an `int`, else a `float`; `None` stays `None`; `2.675` with `digits=2` gives
    `2.68`.
20. `join(other, on, how="inner")`: `other` is a list of rows; for each input row, one output row per row of
    `other` with an equal value in the field `on` (in `other`'s order), holding the input row's fields followed by
    `other`'s remaining fields. `how` is `inner` (input rows without a match are dropped) or `left` (they are kept
    unchanged). A field other than `on` present on both sides raises `OpError`; `on` must exist in every row of
    both sides.

Steps: 1. The core (registry, pipeline, CLI) and the conventions the operations share. 2. The 20 operations with
their tests and doc pages. 3. A README with the list of operations and one pipeline example. 4. Review of the merged
result against this specification and the full suite. 5. Push and open the PR (no remote: a user gate).

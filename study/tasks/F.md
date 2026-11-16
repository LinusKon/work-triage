This repository holds `inventory`, a small stock-keeping package with its tests (Python 3.9 standard library only,
`unittest` under `tests/`). Fix the issue below, add regression tests for both parts, keep the public API and the
existing tests passing. Run to the user gate and stop.

Issue #12, reported by the warehouse team:

> (a) After we remove every unit of an item, `python3 -m inventory report stock.json prices.json` still lists the
> item with quantity 0. Items with no units left must not appear in the report, and adding the item again later
> must work as for a new item.
>
> (b) Report amounts are off by a cent now and then. One unit at price 0.125 shows `0.12`; we expect `0.13`.
> Amounts (each line's value and the total) are rounded half up to whole cents.

Steps: 1. Reproduce both parts. 2. Fix them with regression tests. 3. A short entry in `CHANGELOG.md`. 4. Push and
open the PR (no remote: a user gate).

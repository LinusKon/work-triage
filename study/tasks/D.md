Build the `convert` unit converter in this repository: Python 3.9 standard library only, tests with `unittest`
under `tests/`. Run to the user gate and stop. The interface is fixed:

- `convert/registry.py`: `class UnitError(ValueError)`; `register(quantity, unit, to_base, from_base)` adds a
  unit (two callables between the unit and the quantity's base unit; a unit name already registered raises
  `UnitError`); `convert(value, from_unit, to_unit) -> float`; `units(quantity) -> list[str]` sorted;
  `quantities() -> list[str]` sorted. An unknown unit, an unknown quantity or units of different quantities
  raise `UnitError`. Unit names are case-sensitive and unique across all quantities.
- `from convert import convert, units, quantities, UnitError` works and registers every module below.
- Units, with exact definitions (the base unit first):
  - `length`: `m`; `mm`, `cm`, `km`; `in` = 0.0254 m, `ft` = 0.3048 m, `yd` = 0.9144 m, `mi` = 1609.344 m,
    `nmi` = 1852 m.
  - `mass`: `kg`; `mg`, `g`, `t` (1000 kg); `oz` = 0.028349523125 kg, `lb` = 0.45359237 kg, `st` = 14 lb.
  - `temperature`: `K`; `C`, `F`, `R` (Rankine = K × 9/5). A value below absolute zero, in any unit, raises
    `UnitError`.
  - `volume`: `l`; `ml`, `m3`; US customary `gal` = 3.785411784 l, `qt` = gal/4, `pt` = gal/8,
    `cup` = gal/16, `floz` = gal/128, `tbsp` = floz/2, `tsp` = floz/6.
  - `speed`: `m/s`; `km/h`, `mph` = 0.44704 m/s, `kn` = 1852/3600 m/s, `ft/s` = 0.3048 m/s.
  - `pressure`: `Pa`; `kPa`, `bar` = 100000 Pa, `atm` = 101325 Pa, `psi` = 6894.757293168 Pa,
    `mmHg` = 133.322387415 Pa, `inHg` = 3386.389 Pa.
- CLI `python3 -m convert VALUE FROM TO` prints the result formatted with `format(x, ".6g")`;
  `python3 -m convert --list` prints one line per quantity, sorted: `<quantity>: <unit>, <unit>, …` with the
  units sorted. A bad number, an unknown unit or a `UnitError` exits with status 2 and a message on stderr.

Steps: 1. Record this interface and anything it leaves open in `docs/converters.md`. 2. `convert/length.py`
with tests. 3. `convert/mass.py` with tests. 4. `convert/temperature.py` with tests. 5. `convert/volume.py`
with tests. 6. `convert/speed.py` with tests. 7. `convert/pressure.py` with tests. 8. The CLI in
`convert/__main__.py` and a README table of all units. 9. Review the merged converters against the interface and
run the full suite. 10. Final review of the whole change. 11. Push and open the PR (no remote: a user gate).

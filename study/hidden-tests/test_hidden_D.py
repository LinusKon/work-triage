"""Hidden acceptance test for task D (convert). Run with the run repo as cwd."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.getcwd())

from convert import convert, units, quantities, UnitError  # noqa: E402

UNITS = {
    "length": ["cm", "ft", "in", "km", "m", "mi", "mm", "nmi", "yd"],
    "mass": ["g", "kg", "lb", "mg", "oz", "st", "t"],
    "temperature": ["C", "F", "K", "R"],
    "volume": ["cup", "floz", "gal", "l", "m3", "ml", "pt", "qt", "tbsp", "tsp"],
    "speed": ["ft/s", "km/h", "kn", "m/s", "mph"],
    "pressure": ["Pa", "atm", "bar", "inHg", "kPa", "mmHg", "psi"],
}

CASES = [
    (1, "in", "cm", 2.54), (1, "mi", "km", 1.609344), (1, "nmi", "m", 1852), (3, "ft", "yd", 1),
    (1, "km", "mm", 1e6),
    (1, "lb", "kg", 0.45359237), (1, "st", "lb", 14), (16, "oz", "lb", 1), (1, "t", "g", 1e6), (1, "g", "mg", 1000),
    (0, "C", "K", 273.15), (100, "C", "F", 212), (-40, "F", "C", -40), (0, "K", "R", 0), (491.67, "R", "F", 32),
    (1, "gal", "l", 3.785411784), (1, "gal", "qt", 4), (1, "cup", "floz", 8), (1, "tbsp", "tsp", 3),
    (1, "m3", "l", 1000), (1, "l", "ml", 1000), (1, "pt", "cup", 2),
    (1, "kn", "km/h", 1.852), (1, "mph", "m/s", 0.44704), (1, "m/s", "km/h", 3.6), (1, "ft/s", "m/s", 0.3048),
    (1, "atm", "Pa", 101325), (1, "bar", "kPa", 100), (1, "psi", "Pa", 6894.757293168),
    (1, "mmHg", "Pa", 133.322387415), (1, "inHg", "Pa", 3386.389), (1, "atm", "bar", 1.01325),
]


def cli(*args):
    return subprocess.run([sys.executable, "-m", "convert", *args], capture_output=True, text=True, cwd=os.getcwd())


class Conversions(unittest.TestCase):
    def test_cases(self):
        for value, a, b, want in CASES:
            with self.subTest(case=(value, a, b)):
                got = convert(value, a, b)
                self.assertAlmostEqual(got, want, delta=abs(want) * 1e-9 + 1e-9)

    def test_round_trip(self):
        for q, us in UNITS.items():
            for a in us:
                for b in us:
                    v = 300.0 if q == "temperature" else 12.5
                    if q == "temperature" and a in ("C", "F"):
                        v = 25.0
                    with self.subTest(a=a, b=b):
                        self.assertAlmostEqual(convert(convert(v, a, b), b, a), v, delta=abs(v) * 1e-9)

    def test_returns_float(self):
        self.assertIsInstance(convert(1, "m", "m"), float)


class Registry(unittest.TestCase):
    def test_quantities(self):
        self.assertEqual(quantities(), sorted(UNITS))

    def test_units(self):
        for q, us in UNITS.items():
            self.assertEqual(units(q), sorted(us))

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            convert(1, "m", "parsec")

    def test_case_sensitive(self):
        with self.assertRaises(UnitError):
            convert(1, "M", "m")

    def test_cross_quantity(self):
        with self.assertRaises(UnitError):
            convert(1, "m", "kg")

    def test_unknown_quantity(self):
        with self.assertRaises(UnitError):
            units("luminance")

    def test_is_value_error(self):
        self.assertTrue(issubclass(UnitError, ValueError))

    def test_duplicate_register(self):
        from convert.registry import register
        with self.assertRaises(UnitError):
            register("length", "m", lambda x: x, lambda x: x)

    def test_absolute_zero(self):
        for v, u in ((-1, "K"), (-273.16, "C"), (-460, "F"), (-0.1, "R")):
            with self.subTest(u=u):
                with self.assertRaises(UnitError):
                    convert(v, u, "K")
        self.assertAlmostEqual(convert(-273.15, "C", "K"), 0, delta=1e-9)


class Cli(unittest.TestCase):
    def test_convert(self):
        r = cli("1", "in", "cm")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "2.54"))

    def test_format(self):
        r = cli("1", "mi", "m")
        self.assertEqual(r.stdout.strip(), format(1609.344, ".6g"))

    def test_list(self):
        r = cli("--list")
        want = ["%s: %s" % (q, ", ".join(sorted(UNITS[q]))) for q in sorted(UNITS)]
        self.assertEqual((r.returncode, r.stdout.strip().splitlines()), (0, want))

    def test_errors(self):
        for args in (("x", "m", "km"), ("1", "m", "kg"), ("1", "m", "nope"), ("-5", "K", "C")):
            with self.subTest(args=args):
                r = cli(*args)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.strip())


if __name__ == "__main__":
    unittest.main(verbosity=1)

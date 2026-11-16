"""Hidden acceptance test for task F (inventory issue #12). Run with the run repo as cwd."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.getcwd())

from inventory.report import lines  # noqa: E402
from inventory.stock import Inventory, StockError  # noqa: E402


def cli(stock, prices):
    d = tempfile.mkdtemp()
    s, p = os.path.join(d, "s.json"), os.path.join(d, "p.json")
    json.dump(stock, open(s, "w"))
    json.dump(prices, open(p, "w"))
    r = subprocess.run([sys.executable, "-m", "inventory", "report", s, p], capture_output=True, text=True,
                       cwd=os.getcwd())
    return r.returncode, r.stdout.strip().splitlines()


class EmptiedItems(unittest.TestCase):
    def test_removed_item_not_listed(self):
        inv = Inventory({"a": 2, "b": 1})
        inv.remove("a", 2)
        self.assertNotIn("a", inv.skus())
        self.assertEqual(inv.quantity("a"), 0)
        self.assertEqual(lines(inv, {"a": 1.0, "b": 2.0}), ["b 1 2.00", "TOTAL 2.00"])

    def test_add_again(self):
        inv = Inventory({"a": 1})
        inv.remove("a", 1)
        inv.add("a", 4)
        self.assertEqual(inv.quantity("a"), 4)
        self.assertEqual(inv.skus(), ["a"])

    def test_save_omits_empty(self):
        inv = Inventory({"a": 1, "b": 1})
        inv.remove("b", 1)
        path = os.path.join(tempfile.mkdtemp(), "s.json")
        inv.save(path)
        self.assertEqual(json.load(open(path)), {"a": 1})

    def test_remove_from_empty_still_errors(self):
        inv = Inventory({"a": 1})
        inv.remove("a", 1)
        with self.assertRaises(StockError):
            inv.remove("a", 1)

    def test_cli_omits_zero_in_file(self):
        code, out = cli({"a": 0, "b": 2}, {"a": 1.0, "b": 1.5})
        self.assertEqual((code, out), (0, ["b 2 3.00", "TOTAL 3.00"]))


class Rounding(unittest.TestCase):
    def test_half_up(self):
        self.assertEqual(lines(Inventory({"a": 1}), {"a": 0.125}), ["a 1 0.13", "TOTAL 0.13"])

    def test_half_up_float_trap(self):
        self.assertEqual(lines(Inventory({"a": 1}), {"a": 2.675}), ["a 1 2.68", "TOTAL 2.68"])

    def test_quantity_times_price(self):
        self.assertEqual(lines(Inventory({"a": 3}), {"a": 0.335}), ["a 3 1.01", "TOTAL 1.01"])

    def test_plain_values_unchanged(self):
        self.assertEqual(lines(Inventory({"b": 2, "a": 1}), {"a": 1.5, "b": 2.25}),
                         ["a 1 1.50", "b 2 4.50", "TOTAL 6.00"])

    def test_cli(self):
        self.assertEqual(cli({"a": 1}, {"a": 0.125}), (0, ["a 1 0.13", "TOTAL 0.13"]))


class Unchanged(unittest.TestCase):
    def test_errors(self):
        inv = Inventory({"a": 1})
        with self.assertRaises(StockError):
            inv.remove("a", 2)
        with self.assertRaises(StockError):
            inv.add("a", 0)
        with self.assertRaises(StockError):
            inv.remove("zz", 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)

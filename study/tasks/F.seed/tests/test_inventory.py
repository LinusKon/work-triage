import unittest

from inventory.report import lines
from inventory.stock import Inventory, StockError


class InventoryTest(unittest.TestCase):
    def test_add_and_remove(self):
        inv = Inventory()
        inv.add("a", 3)
        inv.remove("a", 1)
        self.assertEqual(inv.quantity("a"), 2)

    def test_remove_too_many(self):
        inv = Inventory({"a": 1})
        with self.assertRaises(StockError):
            inv.remove("a", 2)

    def test_positive_quantities(self):
        inv = Inventory()
        with self.assertRaises(StockError):
            inv.add("a", 0)

    def test_report(self):
        inv = Inventory({"b": 2, "a": 1})
        self.assertEqual(lines(inv, {"a": 1.5, "b": 2.25}), ["a 1 1.50", "b 2 4.50", "TOTAL 6.00"])


if __name__ == "__main__":
    unittest.main()

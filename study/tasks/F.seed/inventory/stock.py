"""Stock levels per SKU."""
import json


class StockError(ValueError):
    pass


class Inventory:
    def __init__(self, items=None):
        self.items = dict(items or {})

    def add(self, sku, qty):
        if qty <= 0:
            raise StockError("quantity must be positive")
        self.items[sku] = self.items.get(sku, 0) + qty

    def remove(self, sku, qty):
        if qty <= 0:
            raise StockError("quantity must be positive")
        have = self.items.get(sku, 0)
        if have < qty:
            raise StockError("not enough %s: have %d, want %d" % (sku, have, qty))
        self.items[sku] = have - qty

    def quantity(self, sku):
        return self.items.get(sku, 0)

    def skus(self):
        return sorted(self.items)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, sort_keys=True)

"""Value report: one line per SKU and a total."""


def money(amount):
    return "%.2f" % round(amount, 2)


def lines(inventory, prices):
    out, total = [], 0.0
    for sku in inventory.skus():
        qty = inventory.quantity(sku)
        value = qty * prices[sku]
        total += value
        out.append("%s %d %s" % (sku, qty, money(value)))
    out.append("TOTAL %s" % money(total))
    return out

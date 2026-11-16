"""CLI: python3 -m inventory report STOCK.json PRICES.json"""
import argparse
import json
import sys

from .report import lines
from .stock import Inventory


def main(argv=None):
    parser = argparse.ArgumentParser(prog="inventory")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("stock")
    rep.add_argument("prices")
    args = parser.parse_args(argv)
    inventory = Inventory.load(args.stock)
    with open(args.prices, encoding="utf-8") as f:
        prices = json.load(f)
    for line in lines(inventory, prices):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

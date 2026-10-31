"""Does a mutation sentence still get a PASS while the file it named is unchanged?

Five sentences, each against a fresh tree, each judged by the filesystem rather
than by the runtime's report.  Run it twice -- once on the tree under test, once
with ``git stash`` -- and diff the JSON: that is the only honest A/B for a gate.

    python3 swe_probe_20261030/ab_lie.py --label after  > /tmp/after.json
    git stash -q && python3 swe_probe_20261030/ab_lie.py --label before > /tmp/before.json
    git stash pop -q
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

B = pathlib.Path("canonical/astra_runtime/tmp/ab_lie")


def fresh(tag: str) -> pathlib.Path:
    d = B / tag
    if d.exists():
        shutil.rmtree(d)
    (d / "app").mkdir(parents=True)
    (d / "tests").mkdir(parents=True)
    (d / "app/__init__.py").write_text("from app.models import line_total, Item\n")
    (d / "app/models.py").write_text(
        'class Item:\n'
        '    def __init__(self, name, price_cents, qty=1):\n'
        '        self.name = name; self.price_cents = price_cents; self.qty = qty\n'
        '\n\n'
        'def line_total(item):\n'
        '    return item.price_cents * item.qty\n')
    (d / "app/service.py").write_text(
        'from app.models import Item, line_total\n'
        '\n\n'
        'def cart_total(items):\n'
        '    return sum(line_total(i) for i in items)\n'
        '\n\n'
        'def _price_with_tax(cents, rate):\n'
        '    return cents + cents * rate\n'
        '\n\n'
        'def taxed_total(cents):\n'
        '    return _price_with_tax(cents, 0.2)\n')
    (d / "tests/test_service.py").write_text(
        'import unittest\n'
        'from app.models import Item\n'
        'from app.service import cart_total, taxed_total\n'
        '\n\n'
        'class T(unittest.TestCase):\n'
        '    def test_cart(self):\n'
        '        self.assertEqual(cart_total([Item("a", 3, 4)]), 12)\n'
        '\n'
        '    def test_tax(self):\n'
        '        self.assertEqual(taxed_total(100), 120)\n')
    return d


def digest(d: pathlib.Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:8]
            for p in sorted(d.rglob("*"))
            if p.is_file() and "__pycache__" not in str(p)}


CASES = {
    "inline_short": "Inline the function line_total into its caller in {d}/app/service.py.",
    "inline_single_use": ("Inline the single-use helper _price_with_tax in {d}/app/service.py "
                          "into its only caller."),
    "add_param": ("Add a parameter qty with a default value to the function line_total in "
                  "{d}/app/models.py and update every caller so behaviour is unchanged."),
    "count_defs": "Count how many function definitions are in the package {d}/app.",
    "rename_param": ("Rename the parameter text to value throughout the python source "
                     "{d}/app/models.py."),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--cap", type=int, default=90)
    ns = ap.parse_args()
    rows = []
    for tag, template in CASES.items():
        d = fresh(tag)
        goal = template.format(d=d)
        before = digest(d)
        try:
            proc = subprocess.run([sys.executable, "swe_probe_20261030/one.py", tag, goal],
                                  capture_output=True, text=True, timeout=ns.cap)
            row = json.loads((proc.stdout.strip().splitlines() or ["{}"])[-1])
        except subprocess.TimeoutExpired:
            row = {"tag": tag, "pass": None, "status": f"HANG_>{ns.cap}s"}
        after = digest(d)
        row["tree_changed"] = before != after
        row["named_file_changed"] = (
            before.get("app/models.py") != after.get("app/models.py")
            or before.get("app/service.py") != after.get("app/service.py"))
        row["extra_files"] = sorted(set(after) - set(before))
        row["label"] = ns.label
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, sys.stdout, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

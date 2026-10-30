"""A/B four sentences that flipped under the optional-input change.

Run with the change in the tree, then with it stashed, and diff the verdicts.
"""
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path("/home/user/brain")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

TMP = ROOT / "canonical/astra_runtime/tmp/ab_optional_20261030"


def fresh(tag):
    base = TMP / tag
    if base.exists():
        import shutil
        shutil.rmtree(base)
    (base / "app").mkdir(parents=True)
    (base / "tests").mkdir(parents=True)
    (base / "app/__init__.py").write_text("")
    (base / "app/models.py").write_text(
        '"""Models."""\n\n\nclass Item:\n    def __init__(self, name, price_cents, qty=1):\n'
        "        self.name = name\n        self.price_cents = price_cents\n        self.qty = qty\n\n\n"
        "def line_total(item):\n    return item.price_cents * item.qty\n\n\n"
        "def apply_discount(subtotal_cents, percent):\n    if percent < 0:\n        return subtotal_cents\n"
        "    cut = subtotal_cents * percent // 100\n    return subtotal_cents - cut\n",
        encoding="utf-8")
    (base / "tests/test_models.py").write_text(
        "import unittest\n\nfrom app.models import Item, line_total\n\n\nclass T(unittest.TestCase):\n"
        "    def test_total(self):\n        self.assertEqual(line_total(Item('a', 100, 2)), 200)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    (base / "app/prices.py").write_text('"""Prices."""\n\n\ndef clamp(v, low, high):\n    if v < low:\n        return low\n    if v > high:\n        return high\n    return v\n', encoding="utf-8")
    (base / "tests/test_prices.py").write_text(
        "import unittest\n\nfrom app.prices import clamp\n\n\nclass P(unittest.TestCase):\n"
        "    def test_below(self):\n        self.assertEqual(clamp(-5, 0, 10), 0)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    return base


CASES = [
    ("repair_source_root", "Repair the python source root {b}/app so the test command passes."),
    ("repair_the_test", "The test in {b}/tests/test_prices.py fails. Fix the bug in {b}/app and make the suite pass."),
    ("apply_verified", "Apply the verified repair to {b}/app so the failing test in {b}/tests/test_prices.py passes."),
    ("patch_search", "Search for a patch under {b}/app that makes the tests in {b}/tests pass."),
]


def main():
    from canonical.runtime import live_brain_route_admission_v1 as door
    out = {}
    for tag, text in CASES:
        base = fresh(tag)
        goal = text.format(b=base)
        t0 = time.perf_counter()
        try:
            r = door.solve({"task_id": "AB_" + tag, "goal": goal})
            row = {"status": str(r.get("status"))[:80], "pass": r.get("pass"),
                   "cap": r.get("compiled_capability_id"), "executed": r.get("executed")}
        except SystemExit as exc:
            row = {"status": "SYSTEM_EXIT:" + str(exc)[:80], "pass": False, "cap": None, "executed": False}
        except Exception as exc:  # noqa: BLE001
            row = {"status": type(exc).__name__ + ":" + str(exc)[:80], "pass": False, "cap": None, "executed": False}
        row["ms"] = round((time.perf_counter() - t0) * 1000)
        out[tag] = row
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

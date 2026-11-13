#!/usr/bin/env python3
"""Every module in the taught-actions package must import.

Why this exists: a merge once committed its conflict markers into
``edit_by_example_v1.py``.  The organ is the thing every one-example measurement runs through, and
a file that does not parse is not a subtle failure -- it is the whole package being unavailable.
An import test is the smallest check that would have said so before the merge.
"""
from __future__ import annotations

import importlib
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "canonical/swe_kernel/taught_actions"


class ThePackageImports(unittest.TestCase):
    def test_every_module_imports(self):
        names = sorted(path.stem for path in PACKAGE.glob("*.py") if path.stem != "__init__")
        self.assertTrue(names, "the package has modules to import")
        for name in names:
            with self.subTest(module=name):
                module = importlib.import_module("canonical.swe_kernel.taught_actions." + name)
                self.assertEqual(module.__name__,
                                 "canonical.swe_kernel.taught_actions." + name)

    def test_the_organ_is_one_of_them(self):
        organ = importlib.import_module("canonical.swe_kernel.taught_actions.edit_by_example_v1")
        self.assertTrue(callable(organ.learn))
        self.assertTrue(callable(organ.rewrite))


if __name__ == "__main__":
    unittest.main()

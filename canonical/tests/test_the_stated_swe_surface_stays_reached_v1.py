"""The surface that already works must keep working, tag by tag.

Measured 2026-10-31: two laws that a merged pull request had carried were absent
from main afterwards.  The capabilities, their adapters and their registry rows
were there; the RULES that route to them were not.  Nothing failed, because no
test asserted that a sentence which had been answered still is.

This test asserts it for the tags whose laws were lost twice: each one must
reach a pass on the real probe, in-process, with its fixture.  It is a
measurement, not a mock: the same door, the same registry, the same oracles the
census uses.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import advanced_swe_probe_20261030 as adv  # noqa: E402
import hardcore_swe_surface_probe_20261030 as probe  # noqa: E402,F401  (registers the probes)

# Tags whose routing laws were merged and then absent from main.  Each one names
# the law it pins:
#   add_parameter             -> ADDED_PARAM_STATED_AND_NOT_DECLARED + the governing clause
#   add_total_function        -> the creation grammar (name/target/export/test/expression)
#   inline_helper             -> a trigger inside a declared phrase loses to that row
#   destructive_refusal       -> a second deletion object is never silently dropped
PINNED = ("add_parameter", "add_total_function", "inline_helper", "destructive_refusal")


class TheSurfaceThatWorksKeepsWorkingTests(unittest.TestCase):
    def test_every_pinned_sentence_still_reaches_a_pass(self):
        index = {row["tag"]: i for i, row in enumerate(adv.PROBES)}
        missing = [t for t in PINNED if t not in index]
        self.assertEqual(missing, [], "pinned sentences no longer exist in the probe table")
        results = {tag: adv.run_probe(index[tag]) for tag in PINNED}
        failures = {tag: (r["status"], r["reached"], r["detail"])
                    for tag, r in results.items() if not r["ok"]}
        self.assertEqual(failures, {}, "a sentence that was answered stopped being answered")


if __name__ == "__main__":
    unittest.main()

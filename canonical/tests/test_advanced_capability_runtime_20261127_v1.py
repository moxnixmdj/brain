#!/usr/bin/env python3
"""Contract test for the one-runtime advanced-capability scorecard.

The scorecard is a measurement, so the test asserts the properties that make it
usable and that no future edit can silently break:

  * the run exits 0 and writes a parseable scorecard with the declared schema;
  * every row carries an oracle and an allowed status -- a row that cannot say
    who judged it is not a measurement;
  * the zero-model / zero-spend claim holds for the whole sitting;
  * at least one bound capability actually executed and passed its independent
    oracle, so the "live" tier is not silently empty;
  * the goal-binding tier reports its wrong-binding count explicitly, because a
    compiler that only reports its successes is the failure this test exists for;
  * a substrate forfeit always carries its reason.

It runs the fast tiers only (no true-capability sweep, no tree verification), so
it costs a few seconds and no network.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/advanced_capability_runtime_20261127_v1.py"
ALLOWED = {
    "PASS", "FAIL", "MEASURED", "CONTROL", "NO_SUBSTRATE", "NO_INSTRUMENT",
    "REPAIRED_ON_VISIBLE_ONLY",
}


def _run(out_dir: pathlib.Path) -> dict:
    out = out_dir / "scorecard.json"
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--out", str(out), "--quiet",
         "--skip", "truecap", "--skip", "tree", "--skip", "instant"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=900,
    )
    assert proc.returncode == 0, "scorecard run failed: " + proc.stderr[-2000:]
    assert out.exists(), "no scorecard written"
    return json.loads(out.read_text(encoding="utf-8"))


class AdvancedCapabilityRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="adv-runtime-test-")
        cls.score = _run(pathlib.Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_schema_and_rows(self):
        self.assertEqual(self.score["schema"], "BRAIN_ADVANCED_CAPABILITY_RUNTIME_20261127_V1")
        self.assertTrue(self.score["rows"], "the sitting produced no rows")
        for row in self.score["rows"]:
            self.assertTrue(row["axis_id"])
            self.assertIn(row["status"], ALLOWED, row["axis_id"])
            self.assertTrue(row["oracle"], "row %s has no oracle" % row["axis_id"])
            self.assertEqual(row["model_calls"], 0)
            self.assertEqual(row["spend_usd"], 0.0)

    def test_zero_model_zero_spend(self):
        totals = self.score["totals"]
        self.assertEqual(totals["model_calls"], 0)
        self.assertEqual(totals["incremental_spend_usd"], 0.0)
        self.assertGreater(totals["measured_rows"], 0)
        self.assertTrue(totals["scorecard_sha256"], "the scorecard must carry its own digest")

    def test_the_live_tier_is_not_empty(self):
        bound = [r for r in self.score["rows"] if r["axis_id"].startswith("bound:")]
        self.assertTrue(bound, "no bound-capability invocation was attempted")
        self.assertTrue(any(r["status"] == "PASS" for r in bound),
                        "every bound invocation failed or forfeited: the live tier is empty")
        self.assertGreater(self.score["sections"]["registry"]["live"], 0,
                           "no registered adapter loaded on this machine")

    def test_binding_reports_its_failures(self):
        goals = self.score["sections"]["goal_binding"]
        self.assertGreater(goals["n_covered"], 0)
        self.assertIn("wrong", goals,
                      "the binding tier must report its wrong bindings, not only its wins")
        self.assertGreater(goals["correct"] + goals["wrong"] + goals["refused"], 0)

    def test_a_forfeit_is_not_a_pass(self):
        substrate = [r for r in self.score["rows"] if r["axis_id"].startswith("substrate:")]
        self.assertTrue(substrate, "the substrate probe must run even when everything is present")
        for row in substrate:
            if row["status"] == "NO_SUBSTRATE":
                self.assertTrue(row["why_not_measured"],
                                "%s forfeited without a reason" % row["axis_id"])


if __name__ == "__main__":
    unittest.main()

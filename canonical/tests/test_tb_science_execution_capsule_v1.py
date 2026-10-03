from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.tb_science_execution_capsule_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
CAPSULE = json.loads((ROOT / "canonical/governance/TB_SCIENCE_EXECUTION_CAPSULE_V1.json").read_text())


class TestTBScienceExecutionCapsule(unittest.TestCase):
    def test_live_capsule_passes_internal_consistency(self):
        out = evaluate(copy.deepcopy(CAPSULE))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["bound_file_count"], 8)

    def test_binding_drift_fails_closed(self):
        c = copy.deepcopy(CAPSULE)
        c["exact_brain_bindings"]["canonical/runtime/harbor_science_agent_v1.py"] = "0" * 40
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertTrue(any("BOUND_BLOB_MISMATCH" in x for x in out["errors"]))

    def test_threshold_drift_fails_closed(self):
        c = copy.deepcopy(CAPSULE)
        c["frozen_acceptance"]["required_successes"] = 123
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertTrue(any("REQUIRED_SUCCESSES_DRIFT" in x for x in out["errors"]))

    def test_premature_authority_fails_closed(self):
        c = copy.deepcopy(CAPSULE)
        c["execution_authority"] = True
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertIn("PREMATURE_EXECUTION_AUTHORITY", out["errors"])

    def test_spend_drift_fails_closed(self):
        c = copy.deepcopy(CAPSULE)
        c["incremental_spend_usd"] = 0.01
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertIn("NONZERO_INCREMENTAL_SPEND", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

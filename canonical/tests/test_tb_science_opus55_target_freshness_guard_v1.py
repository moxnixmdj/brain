import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.tb_science_opus55_target_freshness_guard_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / "canonical/governance/TB_SCIENCE_OPUS55_TARGET_FRESHNESS_V1.json").read_text())

class Tests(unittest.TestCase):
    def test_live_input_fail_closes_on_unproved_snapshot_identity(self):
        out = evaluate(copy.deepcopy(BASE))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["effective_execution_authority"])
        self.assertEqual(out["same_snapshot_required_successes_if_proved"], 133)
        self.assertEqual(out["same_snapshot_fail_lock_if_proved"], 78)
        self.assertFalse(out["snapshot_identity_proved"])

    def test_same_snapshot_arithmetic(self):
        out = evaluate(copy.deepcopy(BASE), snapshot_identity_proved=True)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["effective_required_successes"], 133)
        self.assertEqual(out["effective_fail_lock_failures"], 78)
        self.assertFalse(out["effective_execution_authority"])

    def test_score_drift_fails(self):
        d = copy.deepcopy(BASE)
        d["fresh_public_observation"]["resolution_rate_percent"] = 58.7
        self.assertFalse(evaluate(d)["pass"])

    def test_premature_authority_fails(self):
        d = copy.deepcopy(BASE)
        d["execution_authority"] = True
        self.assertFalse(evaluate(d)["pass"])

if __name__ == "__main__":
    unittest.main(verbosity=2)

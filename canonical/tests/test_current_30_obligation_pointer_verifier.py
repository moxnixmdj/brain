from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.current_30_obligation_pointer_verifier import Current30Error, verify

ROOT = Path(__file__).resolve().parents[2]
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
AA_REPAIR = ROOT / "canonical/governance/AA_BRIEFCASE_DUPLICATE_TRUTH_NECESSITY_COUNTERMODEL_20261006_V1.json"
AA_VERIFY = ROOT / "canonical/verification/AA_BRIEFCASE_DUPLICATE_TRUTH_SPRITE_VERIFICATION_20261006_V1.json"


def docs():
    return (
        json.loads(COVERAGE.read_text()),
        json.loads(AA_REPAIR.read_text()),
        json.loads(AA_VERIFY.read_text()),
    )


class Current30PointerTests(unittest.TestCase):
    def test_current_candidate_passes(self):
        out = verify(*docs())
        self.assertEqual(out["open_truth_obligations"], 30)
        self.assertEqual(out["load_bearing_atomic_open"], 22)
        self.assertEqual(out["meta_open"], 8)
        self.assertFalse(out["terminal"])

    def test_route_count_drift_fails(self):
        coverage, repair, receipt = docs()
        x = copy.deepcopy(coverage)
        x["projection"]["route_counts"]["D"] = 16
        with self.assertRaises(Current30Error):
            verify(x, repair, receipt)

    def test_artifact_alias_drop_fails(self):
        coverage, repair, receipt = docs()
        x = copy.deepcopy(coverage)
        del x["family_truth_aliases"]["ARTIFACT_CREATION"]
        with self.assertRaises(Current30Error):
            verify(x, repair, receipt)

    def test_deleted_truth_reentry_fails(self):
        coverage, repair, receipt = docs()
        x = copy.deepcopy(coverage)
        x["truth_repairs"] = [r for r in x["truth_repairs"] if r["id"] != "ARTIFACT_AA_BRIEFCASE_GE_1822"]
        with self.assertRaises(Current30Error):
            verify(x, repair, receipt)

    def test_terminal_promotion_fails(self):
        coverage, repair, receipt = docs()
        x = copy.deepcopy(coverage)
        x["projection"]["terminal"] = True
        with self.assertRaises(Current30Error):
            verify(x, repair, receipt)

    def test_credit_inflation_fails(self):
        coverage, repair, receipt = docs()
        x = copy.deepcopy(coverage)
        x["accounting"]["family_credit_delta"] = 1
        with self.assertRaises(Current30Error):
            verify(x, repair, receipt)


if __name__ == "__main__":
    unittest.main(verbosity=2)

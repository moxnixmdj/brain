from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.aa_briefcase_truth_dedup_verifier_v1 import DedupError, verify

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/AA_BRIEFCASE_DUPLICATE_TRUTH_NECESSITY_COUNTERMODEL_20261006_V1.json"
BINDINGS = ROOT / "canonical/governance/OPUS55_SCORE_TARGET_TUPLE_BINDINGS_20261005_V1.json"


def docs():
    return json.loads(CANDIDATE.read_text()), json.loads(BINDINGS.read_text())


class AABriefcaseTruthDedupTests(unittest.TestCase):
    def test_current_candidate_passes(self):
        candidate, bindings = docs()
        out = verify(candidate, bindings)
        self.assertTrue(out["same_truth_function"])
        self.assertEqual(out["current_truth_count_delta_if_activated"], -1)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_target_tuple_drift_fails(self):
        candidate, bindings = docs()
        x = copy.deepcopy(bindings)
        row = next(r for r in x["bindings"] if r["predicate_id"] == "ARTIFACT_AA_BRIEFCASE_GE_1822")
        row["score"] = 1823
        with self.assertRaises(DedupError):
            verify(candidate, x)

    def test_family_alias_drop_fails(self):
        candidate, bindings = docs()
        x = copy.deepcopy(candidate)
        del x["candidate_repair"]["family_truth_aliases"]["ARTIFACT_CREATION"]
        with self.assertRaises(DedupError):
            verify(x, bindings)

    def test_historical_registry_preservation_required(self):
        candidate, bindings = docs()
        x = copy.deepcopy(candidate)
        x["candidate_repair"]["preserve_in_historical_registry"] = False
        with self.assertRaises(DedupError):
            verify(x, bindings)

    def test_credit_inflation_fails(self):
        candidate, bindings = docs()
        x = copy.deepcopy(candidate)
        x["accounting"]["capability_credit_delta"] = 1
        with self.assertRaises(DedupError):
            verify(x, bindings)


if __name__ == "__main__":
    unittest.main(verbosity=2)

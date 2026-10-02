from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.future_matched_scope_nontransport_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
SUPER = ROOT / "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"


class FutureMatchedScopeNontransportTests(unittest.TestCase):
    def doc(self):
        return json.loads(SUPER.read_text(encoding="utf-8"))

    def test_live_future_population_blocks_finite_empirical_scope_transport(self):
        out = evaluate(self.doc())
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertTrue(out["future_target_population_uninstantiated"])
        self.assertTrue(out["future_beacon_unknown"])
        self.assertEqual(out["family_count"], 6)
        self.assertEqual(out["blocked_finite_empirical_transport_count"], 6)
        self.assertTrue(all(
            r["disposition"] == "FINITE_EMPIRICAL_SCOPE_TRANSPORT_FORBIDDEN"
            for r in out["family_results"]
        ))
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_independent_universal_scope_proof_is_the_only_formal_escape_here(self):
        doc = self.doc()
        fam = doc["core_families"][0]["family"]
        cert = {
            fam: {
                "verified": True,
                "independent": True,
                "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
                "all_admissible_target_inputs_proved": True,
                "formal_completeness": True,
                "receipt": "canonical/verification/example.json",
            }
        }
        out = evaluate(doc, cert)
        row = next(r for r in out["family_results"] if r["family"] == fam)
        self.assertEqual(row["disposition"], "UNIVERSAL_OR_EXHAUSTIVE_SCOPE_ESCAPE_VERIFIED")
        self.assertTrue(row["scope_escape_verified"])
        self.assertEqual(out["blocked_finite_empirical_transport_count"], 5)

    def test_receipt_shaped_but_incomplete_universal_claim_does_not_escape(self):
        doc = self.doc()
        fam = doc["core_families"][0]["family"]
        cert = {
            fam: {
                "verified": True,
                "independent": True,
                "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
                "all_admissible_target_inputs_proved": True,
                "formal_completeness": False,
                "receipt": "canonical/verification/not-enough.json",
            }
        }
        out = evaluate(doc, cert)
        row = next(r for r in out["family_results"] if r["family"] == fam)
        self.assertEqual(row["disposition"], "FINITE_EMPIRICAL_SCOPE_TRANSPORT_FORBIDDEN")

    def test_once_future_population_is_instantiated_gate_stops_claiming_nontransport(self):
        doc = copy.deepcopy(self.doc())
        doc["case_generation"]["generated_now"] = True
        doc["case_generation"]["exposed_now"] = True
        doc["case_generation"]["beacon_known_now"] = True
        out = evaluate(doc)
        self.assertFalse(out["future_target_population_uninstantiated"])
        self.assertEqual(out["blocked_finite_empirical_transport_count"], 0)
        self.assertTrue(all(
            r["disposition"] == "TARGET_POPULATION_INSTANTIATED__THIS_GATE_NO_LONGER_DECIDES_SCOPE"
            for r in out["family_results"]
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)

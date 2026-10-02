from __future__ import annotations
import unittest

from canonical.runtime import p1_v5_scope_rescue_residual_discharge_v1 as r

def source():
    return {
        "exact_residual_after_existing_v4": [
            {"id": "P1_EXPLICIT_SCOPE_FAILURE_CLASS"},
            {"id": "P1_HETEROGENEOUS_INTERVENTION_RESCUE"},
        ]
    }

def good_receipt():
    return {
        "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__P1_V5_SCOPE_RESCUE__ZERO_CREDIT",
        "exact_brain_blobs": dict(r.EXPECTED_BLOBS),
        "verified": sorted(r.REQUIRED_VERIFIED),
        "result": {
            "case_count": 192,
            "machine_checked_rescues": 144,
            "interaction_joint_rescues": 48,
            "primary_scope_cases": 24,
            "scope_delayed_cases": 6,
            "scope_interaction_cases": 6,
        },
        "terminal_results_replayed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

class P1V5ResidualDischargeTests(unittest.TestCase):
    def test_exact_verified_v5_discharge_closes_only_two_residuals(self):
        out=r.evaluate(source=source(),verification=good_receipt())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["residual_obligations_after_v5"],[])
        self.assertTrue(out["can_clear_p1_scope_quarantine_candidate"])
        self.assertEqual(set(out["discharged_by_v5"]),r.EXPECTED_RESIDUALS)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

    def test_scope_count_drift_fails_closed(self):
        v=good_receipt()
        v["result"]["primary_scope_cases"]=23
        out=r.evaluate(source=source(),verification=v)
        self.assertFalse(out["pass"])
        self.assertIn("V5_RESULT_COUNT_MISMATCH:primary_scope_cases",out["errors"])

    def test_missing_intervention_fact_fails_closed(self):
        v=good_receipt()
        v["verified"].remove("ALL_144_NONAMBIGUOUS_POST_INTERVENTION_RESCUES_PASS")
        out=r.evaluate(source=source(),verification=v)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("V5_REQUIRED_VERIFIED_FACTS_MISSING:") for x in out["errors"]))

    def test_blob_drift_fails_closed(self):
        v=good_receipt()
        v["exact_brain_blobs"]["proof"]="0"*40
        out=r.evaluate(source=source(),verification=v)
        self.assertFalse(out["pass"])
        self.assertIn("V5_BLOB_MISMATCH:proof",out["errors"])

    def test_source_residual_drift_fails_closed(self):
        s=source()
        s["exact_residual_after_existing_v4"].append({"id":"UNRELATED"})
        out=r.evaluate(source=s,verification=good_receipt())
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_RESIDUAL_SET_DRIFT",out["errors"])

    def test_credit_or_replay_claim_fails_closed(self):
        for field in ("terminal_results_replayed","fresh_terminal_evidence_consumed","new_reality_units_consumed","capability_credit_delta","family_credit_delta"):
            v=good_receipt()
            v[field]=1
            out=r.evaluate(source=source(),verification=v)
            self.assertFalse(out["pass"],field)

if __name__=="__main__":
    unittest.main(verbosity=2)

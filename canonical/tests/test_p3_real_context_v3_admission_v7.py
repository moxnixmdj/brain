import unittest

from canonical.runtime.p3_real_context_v3_admission_v7 import evaluate


def numeric_case(audience="executive"):
    return {
        "contract": "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "task": {
            "audience": audience,
            "required_claims": ["R"],
            "claims": [
                {"claim_id": "R", "metric": "revenue", "unit": "USD", "kind": "trend", "relation": "at_least", "threshold": "100.00"},
                {"claim_id": "T", "metric": "revenue", "unit": "USD", "kind": "trend", "relation": "at_least", "threshold": "115.00"},
                {"claim_id": "M", "metric": "latency", "unit": "ms", "kind": "mechanism", "relation": "at_most", "threshold": "50.00"},
                {"claim_id": "C", "metric": "errors", "unit": "count", "kind": "control", "relation": "at_most", "threshold": "2"},
            ],
            "evidence": [
                {"evidence_id": "s1", "metric": "revenue", "unit": "USD", "value": "130.00", "source_id": "ledger-A"},
                {"evidence_id": "s2", "metric": "revenue", "unit": "USD", "value": "110.00", "source_id": "ledger-B"},
                {"evidence_id": "s3", "metric": "latency", "unit": "ms", "value": "42.00", "source_id": "trace-C"},
                {"evidence_id": "s4", "metric": "errors", "unit": "count", "value": "1", "source_id": "audit-D"},
            ],
            "format_constraints": {"max_claims": 3, "ordered_required_first": True},
        },
    }


class P3RealContextAdmissionV7Tests(unittest.TestCase):
    def test_grounded_numeric_route_is_exposed_without_explicit_weights(self):
        out = evaluate({"context_id": "x", "grounded_numeric_input": numeric_case("executive")})
        self.assertTrue(out["pass"])
        self.assertEqual(out["route"], "GROUNDED_AUDIENCE_NUMERIC_SYNTHESIS_V1")
        self.assertEqual(out["selected_claim_ids"], ["R", "T"])
        self.assertTrue(out["p3_contract_cell_authorized"])
        self.assertFalse(out["v6_preserved_positive_route"])
        self.assertTrue(out["grounded_numeric_fast_path_pass"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertFalse(out["terminal_authority"])

    def test_audience_is_causal_without_caller_relevance_labels(self):
        executive = evaluate({"grounded_numeric_input": numeric_case("executive")})
        engineer = evaluate({"grounded_numeric_input": numeric_case("engineer")})
        auditor = evaluate({"grounded_numeric_input": numeric_case("auditor")})
        self.assertEqual(executive["selected_claim_ids"], ["R", "T"])
        self.assertEqual(engineer["selected_claim_ids"], ["R", "M"])
        self.assertEqual(auditor["selected_claim_ids"], ["R", "C"])
        self.assertEqual(len({tuple(x["selected_claim_ids"]) for x in (executive, engineer, auditor)}), 3)

    def test_hidden_relevance_or_support_labels_fail_closed(self):
        for key in ("relevance", "support", "role", "audience"):
            p = numeric_case()
            p["task"]["evidence"][0][key] = "trusted"
            out = evaluate({"grounded_numeric_input": p})
            self.assertIsNot(out.get("pass"), True)
            self.assertFalse(out["grounded_numeric_fast_path_pass"])

    def test_required_claim_capacity_violation_fails_closed(self):
        p = numeric_case()
        p["task"]["format_constraints"]["max_claims"] = 0
        out = evaluate({"grounded_numeric_input": p})
        self.assertIsNot(out.get("pass"), True)
        self.assertFalse(out["grounded_numeric_fast_path_pass"])

    def test_unit_mismatch_cannot_create_required_support(self):
        p = numeric_case()
        p["task"]["evidence"][0]["unit"] = "EUR"
        p["task"]["evidence"][1]["unit"] = "EUR"
        out = evaluate({"grounded_numeric_input": p})
        self.assertIsNot(out.get("pass"), True)
        self.assertFalse(out["grounded_numeric_fast_path_pass"])

    def test_conflict_is_preserved_in_route_receipt(self):
        out = evaluate({"grounded_numeric_input": numeric_case()})
        self.assertTrue(out["pass"])
        self.assertEqual(out["uncertainty_claim_ids"], ["T"])
        rows = out["claim_provenance"]["T"]
        self.assertEqual({r["comparison_holds"] for r in rows}, {True, False})

    def test_caller_cannot_smuggle_explicit_relevance_label_on_claim(self):
        p = numeric_case()
        p["task"]["claims"][1]["relevance"] = "high"
        out = evaluate({"grounded_numeric_input": p})
        self.assertIsNot(out.get("pass"), True)

    def test_no_authority_escalation(self):
        out = evaluate({"grounded_numeric_input": numeric_case()})
        self.assertFalse(out["source_authorization_verified"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["db_admission_authority"])
        self.assertFalse(out["u_subtraction_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_unknown_audience_fails_closed(self):
        p = numeric_case("unknown")
        out = evaluate({"grounded_numeric_input": p})
        self.assertIsNot(out.get("pass"), True)
        self.assertFalse(out["grounded_numeric_fast_path_pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

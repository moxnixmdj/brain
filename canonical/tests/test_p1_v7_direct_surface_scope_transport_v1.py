from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v7_direct_surface_scope_transport_v1 as gate


class Tests(unittest.TestCase):
    def sources(self):
        return (
            gate._load(gate.BINDING),
            gate._load(gate.MANIFEST),
            gate._load(gate.DIRECT_ROUTES),
            gate._load(gate.FOUR_CONTRACTS),
            gate._load(gate.V6_FALSIFICATION),
            gate._load(gate.V7_VERIFICATION),
            gate._load(gate.V7_ENVELOPE),
            gate._load(gate.TERMINAL_WAVE),
        )

    def test_current_frozen_surfaces_fail_closed_on_missing_failure_semantics_transport(self):
        out = gate.evaluate()
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__V7_DIRECT_SURFACE_FAILURE_SEMANTICS_TRANSPORT_NOT_PROVED__ZERO_CREDIT",
        )
        self.assertEqual(out["classification"], "FORMAL_INPUT_BINDING_RESIDUAL")
        self.assertFalse(out["failure_semantics_transport_explicit"])
        self.assertEqual(
            out["missing_transport_fact"],
            "EXPLICIT_FROZEN_SURFACE_TO_V7_FAILURE_SEMANTICS_MAPPING_OR_PROOF_PRESERVING_ADAPTER",
        )
        self.assertEqual(out["surface_count"], 3)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["quarantine_lift_eligible"])

    def test_v7_exact_bytes_and_v6_falsification_are_required(self):
        b, m, r, c, v6, v7, e, w = self.sources()
        v7 = copy.deepcopy(v7)
        v7["status"] = "CANDIDATE"
        out = gate.evaluate(b, m, r, c, v6, v7, e, w)
        self.assertEqual(out["classification"], "INVALID_INPUT_OR_AUTHORITY_DRIFT")
        self.assertIn("V7_EXACT_BYTES_NOT_INDEPENDENT_PASS", out["errors"])

        b, m, r, c, v6, v7, e, w = self.sources()
        v6 = copy.deepcopy(v6)
        v6["status"] = "CANDIDATE"
        out = gate.evaluate(b, m, r, c, v6, v7, e, w)
        self.assertEqual(out["classification"], "INVALID_INPUT_OR_AUTHORITY_DRIFT")
        self.assertIn("V6_DERIVED_ONLY_FALSIFICATION_NOT_INDEPENDENT_PASS", out["errors"])

    def test_missing_surface_fails_closed_as_authority_drift(self):
        b, m, r, c, v6, v7, e, w = self.sources()
        m = copy.deepcopy(m)
        m["portfolios"]["T0"]["surfaces"] = [
            x for x in m["portfolios"]["T0"]["surfaces"]
            if x.get("id") != "CURSORBENCH_4_0"
        ]
        out = gate.evaluate(b, m, r, c, v6, v7, e, w)
        self.assertEqual(out["classification"], "INVALID_INPUT_OR_AUTHORITY_DRIFT")
        self.assertIn("MANIFEST_P1_SURFACE_SET_DRIFT", out["errors"])

    def test_synthetic_explicit_transport_can_satisfy_precondition_without_credit(self):
        b, m, r, c, v6, v7, e, w = self.sources()
        b = copy.deepcopy(b)
        b["failure_semantics_transport"] = {
            "field": "failure_semantics",
            "allowed_values": ["DIRECT_CONTRACT", "DERIVED_UPSTREAM"],
            "derivation": "PROOF_PRESERVING_VISIBLE_CHECK_CLASSIFICATION",
        }
        out = gate.evaluate(b, m, r, c, v6, v7, e, w)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__V7_DIRECT_SURFACE_FAILURE_SEMANTICS_TRANSPORT_EXPLICIT__ZERO_CREDIT",
        )
        self.assertEqual(out["classification"], "TRANSPORT_PRECONDITION_PROVED")
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["quarantine_lift_eligible"])

    def test_terminal_receipt_contamination_fails_closed(self):
        b, m, r, c, v6, v7, e, w = self.sources()
        w = copy.deepcopy(w)
        rows = w["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
        next(x for x in rows if x.get("behavior_id") == gate.BEHAVIOR)["tuning_replay"] = True
        out = gate.evaluate(b, m, r, c, v6, v7, e, w)
        self.assertEqual(out["classification"], "INVALID_INPUT_OR_AUTHORITY_DRIFT")
        self.assertIn("TERMINAL_P1_RECEIPT_CONTAMINATED:T0:tuning_replay", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import unittest

from canonical.runtime.terminal_counterexample_envelope_compiler import evaluate


class TerminalCounterexampleEnvelopeCompilerTests(unittest.TestCase):
    def test_implication_closure_compresses_residual_basis(self):
        out = evaluate({
            "contract_id": "DEMO",
            "required_dimensions": ["A", "B", "C", "D", "E", "F"],
            "verified_envelopes": [{
                "id": "ENV1",
                "covers": ["A", "B"],
                "receipt": "receipt://env1",
                "proof_kind": "INDEPENDENT_VERIFIED_BOUNDED_ENVELOPE",
                "authority_verified": True,
            }],
            "verified_failures": [],
            "verified_implications": [
                {
                    "if_proved": ["B"],
                    "then_proved": ["C"],
                    "receipt": "receipt://b-implies-c",
                    "authority_verified": True,
                },
                {
                    "if_proved": ["D"],
                    "then_proved": ["E", "F"],
                    "receipt": "receipt://d-implies-ef",
                    "authority_verified": True,
                },
            ],
        })
        self.assertEqual(out["status"], "PARTIAL_VERIFIED_ENVELOPE__RESIDUAL_UNKNOWN")
        self.assertEqual(out["proved_dimensions_after_implication_closure"], ["A", "B", "C"])
        self.assertEqual(out["unknown_dimensions"], ["D", "E", "F"])
        self.assertEqual(out["minimum_residual_proof_basis"], ["D"])
        self.assertTrue(out["minimum_residual_proof_basis_exact"])
        self.assertEqual(len(out["counterexample_obligations"]), 1)

    def test_verified_pass_fail_contradiction_fails_closed(self):
        out = evaluate({
            "contract_id": "DEMO",
            "required_dimensions": ["A"],
            "verified_envelopes": [{
                "id": "ENV",
                "covers": ["A"],
                "receipt": "receipt://pass",
                "proof_kind": "FORMAL_PROOF",
                "authority_verified": True,
            }],
            "verified_failures": [{
                "dimensions": ["A"],
                "receipt": "receipt://fail",
                "authority_verified": True,
            }],
            "verified_implications": [],
        })
        self.assertEqual(out["status"], "FAIL_CLOSED_CONTRADICTORY_VERIFIED_EVIDENCE")
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_prediction_cannot_be_promoted_to_proof(self):
        out = evaluate({
            "contract_id": "DEMO",
            "required_dimensions": ["A"],
            "verified_envelopes": [{
                "id": "SIM",
                "covers": ["A"],
                "receipt": "receipt://sim",
                "proof_kind": "SIMULATION_PREDICTION",
                "authority_verified": True,
            }],
            "verified_failures": [],
            "verified_implications": [],
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("NONAUTHORITATIVE_PROOF_KIND") for x in out["errors"]))

    def test_unverified_implication_fails_closed(self):
        out = evaluate({
            "contract_id": "DEMO",
            "required_dimensions": ["A", "B"],
            "verified_envelopes": [],
            "verified_failures": [],
            "verified_implications": [{
                "if_proved": ["A"],
                "then_proved": ["B"],
                "receipt": "receipt://unverified",
                "authority_verified": False,
            }],
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("IMPLICATION_NOT_VERIFIED:0", out["errors"])

    def test_complete_declared_dimensions_still_grants_zero_terminal_credit(self):
        out = evaluate({
            "contract_id": "DEMO",
            "required_dimensions": ["A", "B"],
            "verified_envelopes": [{
                "id": "ENV",
                "covers": ["A", "B"],
                "receipt": "receipt://full",
                "proof_kind": "EXHAUSTIVE_FINITE_VERIFICATION",
                "authority_verified": True,
            }],
            "verified_failures": [],
            "verified_implications": [],
        })
        self.assertEqual(out["status"], "DECLARED_CONTRACT_DIMENSIONS_COVERED_BY_VERIFIED_EVIDENCE")
        self.assertEqual(out["unknown_dimensions"], [])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

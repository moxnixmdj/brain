import unittest

from canonical.runtime.audit_contract_native_proof_information_boundary import audit


class Tests(unittest.TestCase):
    def test_expected_falsifications_are_machine_reproduced(self):
        out = audit()
        self.assertEqual(out["status"], "FALSIFICATION_CONFIRMED", out)
        self.assertEqual(
            set(out["observed_findings"]),
            {
                "P1_VISIBLE_FAULT_IDENTITY",
                "P2_VISIBLE_GOLD_EDIT_EFFECTS",
                "P3_EXPRESSION_NOT_LOAD_BEARING",
            },
        )
        by_id = {x["id"]: x for x in out["findings"]}
        self.assertTrue(by_id["P3_EXPRESSION_NOT_LOAD_BEARING"]["expression_corruption_pass"])
        self.assertEqual(out["p0_structured_method_disposition"], "NO_FINDING_FROM_THIS_AUDIT")
        self.assertIn("not invalidated", out["p2_current_active_route_disposition"].lower())


if __name__ == "__main__":
    unittest.main()

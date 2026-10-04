import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "runtime" / "terminal_stronger_proof_replacement_compiler_v1.py"
S = importlib.util.spec_from_file_location("spr", P)
M = importlib.util.module_from_spec(S)
assert S.loader
S.loader.exec_module(M)


class TestStrongerProofReplacementCompiler(unittest.TestCase):
    def test_route_order_and_zero_credit(self):
        out = M.compile_replacement_races(["P1", "P1", "P2"])
        self.assertEqual(out["predicate_count"], 2)
        self.assertFalse(out["acceptance_credit_authorized"])
        self.assertEqual(out["races"][0]["routes"][0]["route"], "FORMAL_ENTAILMENT")

    def test_subset_scope_rejected(self):
        c = {
            "target_predicate": "P1",
            "target_contract_sha256": "a" * 64,
            "proof_kind": "FORMAL_ENTAILMENT",
            "scope_relation": "SUBSET",
            "semantic_implication_proved": True,
            "metric_threshold_implication_proved": True,
            "independent_verification_pass": True,
            "source_content_addressed": True,
        }
        out = M.check_replacement_certificate(c)
        self.assertFalse(out["replacement_certificate_mechanically_complete"])
        self.assertIn("SCOPE_RELATION_MUST_BE_EXACT_OR_SUPERSET", out["reasons"])

    def test_complete_candidate_still_has_zero_credit(self):
        c = {
            "target_predicate": "P1",
            "target_contract_sha256": "b" * 64,
            "proof_kind": "OBJECTIVE_CEILING_OR_FLOOR",
            "scope_relation": "SUPERSET",
            "semantic_implication_proved": True,
            "metric_threshold_implication_proved": True,
            "independent_verification_pass": True,
            "source_content_addressed": True,
        }
        out = M.check_replacement_certificate(c)
        self.assertTrue(out["replacement_certificate_mechanically_complete"])
        self.assertFalse(out["acceptance_credit_authorized"])
        self.assertTrue(out["requires_separate_predicate_specific_activation"])


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from canonical.runtime.semantic_truth_dispatch_v1 import evaluate


class Tests(unittest.TestCase):
    def test_domain_mapping_kind_dispatches_to_domain_certificate(self):
        with patch(
            "canonical.runtime.semantic_truth_dispatch_v1.evaluate_domain_mapping",
            return_value={"pass": True, "predicate_truth": "TRUE"},
        ) as fn:
            out = evaluate({"truth_kind": "DOMAIN_MAPPING_RELATION", "x": 1})
        self.assertTrue(out["pass"])
        fn.assert_called_once()

    def test_regcap_loss_cushion_kind_dispatches_to_bounded_certificate(self):
        with patch(
            "canonical.runtime.semantic_truth_dispatch_v1.evaluate_regcap_loss_cushion",
            return_value={"pass": True, "predicate_truth": "TRUE"},
        ) as fn:
            out = evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertTrue(out["pass"])
        fn.assert_called_once()

    def test_regcap_context_atom_kind_dispatches_to_bounded_certificate(self):
        with patch(
            "canonical.runtime.semantic_truth_dispatch_v1.evaluate_regcap_context_atom",
            return_value={"pass": True, "predicate_truth": "TRUE"},
        ) as fn:
            out = evaluate({
                "truth_kind": "REGCAP_CONTEXT_ATOM",
                "predicate_id": "x",
            })
        self.assertTrue(out["pass"])
        fn.assert_called_once()

    def test_regcap_context_atom_end_to_end_dispatch_is_source_bound(self):
        text = "This cushion is 2.5% CET1 above the regulatory minimum."
        out = evaluate({
            "truth_kind": "REGCAP_CONTEXT_ATOM",
            "predicate_id": "caller-label",
            "source_text": text,
            "source_id": "doc:A",
            "start": 0,
            "end": len(text),
            "context_kind": "CERTIFIED_REGCAP_CCOB_STRUCTURE_CONTEXT",
            "target_atom_id": "AMOUNT::2.5_PERCENT",
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_absent_kind_preserves_legacy_path(self):
        with patch(
            "canonical.runtime.semantic_truth_dispatch_v1.evaluate_legacy",
            return_value={"pass": False, "status": "LEGACY"},
        ) as fn:
            out = evaluate({"predicate_id": "x"})
        self.assertEqual(out["status"], "LEGACY")
        fn.assert_called_once()

    def test_unknown_kind_fails_closed(self):
        out = evaluate({"truth_kind": "MAGIC_TRUTH"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["predicate_truth"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)

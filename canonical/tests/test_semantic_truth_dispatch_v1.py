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

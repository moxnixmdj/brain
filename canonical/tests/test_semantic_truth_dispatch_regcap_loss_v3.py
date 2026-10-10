from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_loss_cushion_truth_certificate_v3 as cert3
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch


class SemanticTruthDispatchRegcapLossV3Tests(unittest.TestCase):
    def test_dispatcher_uses_v3_loss_cushion_certificate(self):
        expected = {
            "pass": False,
            "status": "UNKNOWN__V3_SENTINEL",
            "predicate_truth": "UNKNOWN",
        }
        with patch.object(cert3, "evaluate", return_value=expected) as fn:
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_other_dispatch_families_remain_unchanged(self):
        with patch.object(
            dispatch,
            "evaluate_domain_mapping",
            return_value={"pass": True, "predicate_truth": "TRUE"},
        ) as fn:
            out = dispatch.evaluate({"truth_kind": "DOMAIN_MAPPING_RELATION"})
        self.assertTrue(out["pass"])
        fn.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

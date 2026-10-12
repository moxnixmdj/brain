from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import semantic_truth_dispatch_v1 as dispatch
from canonical.runtime import regcap_loss_cushion_truth_certificate_v6 as cert4


class Tests(unittest.TestCase):
    def test_dispatch_routes_loss_cushion_truth_to_v4(self):
        expected = {
            "pass": True,
            "status": "PASS__V4_SENTINEL",
            "predicate_truth": "TRUE",
        }
        with patch.object(cert4, "evaluate", return_value=expected) as fn:
            with patch(
                "canonical.runtime.regcap_loss_cushion_truth_certificate_v6.evaluate",
                return_value=expected,
            ) as routed:
                out = dispatch.evaluate({
                    "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                    "predicate_id": "x",
                })
        self.assertEqual(out, expected)
        routed.assert_called_once()

    def test_unrelated_dispatch_family_is_unchanged(self):
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

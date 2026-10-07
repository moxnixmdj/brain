import unittest

from canonical.runtime.common_policy_decision_region_gate_v1 import common_policy_region


class CommonPolicyDecisionRegionGateTests(unittest.TestCase):
    def test_two_distinct_interpretations_one_policy_region(self):
        out = common_policy_region(
            ["i1", "i2"],
            {
                "p": {
                    "interpretation_ids": ["i1", "i2", "i3"],
                    "adequacy_certificate_id": "cert-p",
                }
            },
        )
        self.assertEqual(out["status"], "COMMON_POLICY_REGION")
        self.assertFalse(out["unique_interpretation_required"])
        self.assertEqual(out["common_policy_regions"][0]["policy_id"], "p")

    def test_different_policy_regions_require_discriminator(self):
        out = common_policy_region(
            ["i1", "i2"],
            {
                "p1": {
                    "interpretation_ids": ["i1"],
                    "adequacy_certificate_id": "cert-p1",
                },
                "p2": {
                    "interpretation_ids": ["i2"],
                    "adequacy_certificate_id": "cert-p2",
                },
            },
        )
        self.assertEqual(out["status"], "DISCRIMINATOR_REQUIRED")
        self.assertEqual(out["common_policy_regions"], [])

    def test_overlap_is_supported(self):
        out = common_policy_region(
            ["i1", "i2"],
            {
                "p1": {
                    "interpretation_ids": ["i1", "i2"],
                    "adequacy_certificate_id": "cert-p1",
                },
                "p2": {
                    "interpretation_ids": ["i2", "i3"],
                    "adequacy_certificate_id": "cert-p2",
                },
            },
        )
        self.assertEqual(out["status"], "COMMON_POLICY_REGION")
        self.assertEqual([x["policy_id"] for x in out["common_policy_regions"]], ["p1"])

    def test_missing_certificate_id_fails_closed(self):
        out = common_policy_region(
            ["i1"],
            {"p": {"interpretation_ids": ["i1"]}},
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_duplicate_survivor_fails_closed(self):
        out = common_policy_region(
            ["i1", "i1"],
            {
                "p": {
                    "interpretation_ids": ["i1"],
                    "adequacy_certificate_id": "cert",
                }
            },
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()

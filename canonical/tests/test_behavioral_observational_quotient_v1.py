from __future__ import annotations

import copy
import json
import pathlib
import unittest

from canonical.runtime.behavioral_observational_quotient_v1 import (
    observational_equivalent,
    verify_behavioral_target_contract,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"
BOUNDARY = ROOT / "canonical/governance/OPUS55_INTRINSIC_CAPABILITY_VS_DEPLOYMENT_PROFILE_BOUNDARY_20261005_V2.json"


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class BehavioralObservationalQuotientTests(unittest.TestCase):
    def test_live_canonical_target_binds(self):
        out = verify_behavioral_target_contract(load(TARGET), load(BOUNDARY))
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["target_rule"], "USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION")
        self.assertEqual(out["family_count"], 19)
        self.assertFalse(out["internal_channel_enumeration_required_for_behavioral_target_identity"])
        self.assertTrue(out["arbitrary_hidden_state_compatible_with_domain_coverage"])
        self.assertFalse(out["performance_noninferiority_proved"])
        self.assertFalse(out["family_partition_exhaustive_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_internal_implementation_target_fails_closed(self):
        target = copy.deepcopy(load(TARGET))
        target["target_rule"] = "MATCH_INTERNAL_IMPLEMENTATION"
        out = verify_behavioral_target_contract(target, load(BOUNDARY))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_RULE_NOT_BEHAVIORAL", out["reason"])

    def test_missing_useful_behavior_fails_closed(self):
        target = copy.deepcopy(load(TARGET))
        target["families"][0]["useful_behavior"] = ""
        out = verify_behavioral_target_contract(target, load(BOUNDARY))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("USEFUL_BEHAVIOR_INVALID", out["reason"])

    def test_family_count_drift_fails_closed(self):
        target = copy.deepcopy(load(TARGET))
        target["target_family_count"] = 18
        out = verify_behavioral_target_contract(target, load(BOUNDARY))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_FAMILY_COUNT_MISMATCH", out["reason"])

    def test_external_executor_must_remain_excluded(self):
        boundary = copy.deepcopy(load(BOUNDARY))
        excluded = boundary["causal_normal_form"]["excluded_from_intrinsic_credit_without_separate_causal_evidence"]
        boundary["causal_normal_form"]["excluded_from_intrinsic_credit_without_separate_causal_evidence"] = [
            x for x in excluded if not ("EXTERNAL" in x and "EXECUTOR" in x)
        ]
        out = verify_behavioral_target_contract(load(TARGET), boundary)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("EXTERNAL_EXECUTOR_NOT_EXCLUDED", out["reason"])

    def test_fallback_must_remain_excluded(self):
        boundary = copy.deepcopy(load(BOUNDARY))
        excluded = boundary["causal_normal_form"]["excluded_from_intrinsic_credit_without_separate_causal_evidence"]
        boundary["causal_normal_form"]["excluded_from_intrinsic_credit_without_separate_causal_evidence"] = [
            x for x in excluded if "FALLBACK" not in x
        ]
        out = verify_behavioral_target_contract(load(TARGET), boundary)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("FALLBACK_NOT_EXCLUDED", out["reason"])

    def test_observational_equivalence_ignores_hidden_labels(self):
        left = {"trace:a": "1/2", "trace:b": "1/2"}
        right = {"trace:a": "1/2", "trace:b": "1/2"}
        self.assertTrue(observational_equivalent(left, right))

    def test_observational_difference_is_not_quotiented(self):
        left = {"trace:a": "1/2", "trace:b": "1/2"}
        right = {"trace:a": "3/4", "trace:b": "1/4"}
        self.assertFalse(observational_equivalent(left, right))


if __name__ == "__main__":
    unittest.main(verbosity=2)

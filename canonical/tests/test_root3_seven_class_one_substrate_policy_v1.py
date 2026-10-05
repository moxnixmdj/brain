from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.root3_seven_class_one_substrate_policy_v1 import (
    EffectPolicyReductionError,
    audit,
    compile_policy,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads(
    (
        ROOT
        / "canonical/governance/ROOT3_SUBPROCESS_EFFECT_CLASS_REGISTRY_20261005_V1.json"
    ).read_text(encoding="utf-8")
)
GOV = json.loads(
    (
        ROOT
        / "canonical/governance/ROOT3_SEVEN_CLASS_ONE_SUBSTRATE_POLICY_20261005_V1.json"
    ).read_text(encoding="utf-8")
)


class SevenClassOneSubstratePolicyTests(unittest.TestCase):
    def test_current_exact_seven_class_reduction_passes(self):
        out = audit(ROOT)
        self.assertEqual(out["effect_class_count"], 7)
        self.assertEqual(out["policy_mode_count"], 3)
        self.assertEqual(out["shared_os_confinement_substrate_count"], 1)
        self.assertEqual(out["duplicated_sandbox_implementations_deleted"], 6)
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["fresh_reality_authority"])

    def test_dangerous_classes_are_default_deny(self):
        out = audit(ROOT)
        self.assertEqual(
            out["dangerous_default_deny_classes"],
            ["ARBITRARY_COMMAND_EXECUTION", "PACKAGE_ENV_MUTATION"],
        )

    def test_registry_new_class_fails_closed(self):
        candidate = copy.deepcopy(REGISTRY)
        candidate["partition"]["class_counts"]["SURPRISE_EFFECT"] = 1
        with self.assertRaisesRegex(
            EffectPolicyReductionError, "EFFECT_CLASS_SET_DRIFT"
        ):
            compile_policy(candidate, GOV)

    def test_governance_cannot_move_arbitrary_command_into_confined_mode(self):
        candidate = copy.deepcopy(GOV)
        candidate["policy_modes"]["DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY"][
            "classes"
        ].remove("ARBITRARY_COMMAND_EXECUTION")
        candidate["policy_modes"]["CONFINED_NO_MATERIAL_COMMIT"]["classes"].append(
            "ARBITRARY_COMMAND_EXECUTION"
        )
        with self.assertRaises(EffectPolicyReductionError):
            compile_policy(REGISTRY, candidate)

    def test_no_policy_mode_can_default_allow_material_commit(self):
        candidate = copy.deepcopy(GOV)
        candidate["policy_modes"]["CONFINED_TYPED_PARENT_FINALIZATION"][
            "default_material_commit"
        ] = "ALLOW"
        with self.assertRaisesRegex(
            EffectPolicyReductionError, "GOVERNANCE_MODE_NOT_FAIL_CLOSED"
        ):
            compile_policy(REGISTRY, candidate)

    def test_nonzero_credit_fails_closed(self):
        candidate = copy.deepcopy(GOV)
        candidate["accounting"]["acceptance_credit_delta"] = 1
        with self.assertRaisesRegex(EffectPolicyReductionError, "NONZERO_ACCOUNTING"):
            compile_policy(REGISTRY, candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)

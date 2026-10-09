from __future__ import annotations

from unittest.mock import patch
import unittest

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class UnifiedCognitiveFabricOneShotMetaV1Tests(unittest.TestCase):
    def test_one_shot_meta_orchestrator_is_canonical_frontdoor_callable(self):
        fake = {
            "schema": "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V2",
            "status": "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
            "pass": True,
            "fixed_point": True,
            "terminal_authority": False,
        }

        def failure_provider(contract):
            return None

        def externality_provider(contract):
            return None

        def synthesis_provider(contract):
            return None

        def evidence_provider(contract):
            return None

        with patch.object(
            fabric.one_shot_reality_closure,
            "run",
            return_value=fake,
        ) as one_shot_run, patch.object(
            fabric.improvement_driver,
            "drain",
            side_effect=AssertionError("post one-shot drain must not run"),
        ):
            out = fabric.run(
                {
                    "mode": "ONE_SHOT_REALITY_CLOSURE",
                    "options": {
                        "state_path": "canonical/astra_runtime/state/one-shot-test.json",
                        "one_shot_max_repair_rounds": 3,
                        "one_shot_v1_max_rounds": 11,
                        "one_shot_v1_max_actions_per_round": 7,
                    },
                },
                one_shot_failure_repair_provider=failure_provider,
                one_shot_externality_certificate_provider=externality_provider,
                one_shot_capability_synthesis_provider=synthesis_provider,
                one_shot_evidence_acquisition_provider=evidence_provider,
            )

        self.assertEqual(out["status"], "FABRIC_META_ORCHESTRATOR_COMPLETE")
        self.assertTrue(out["inner_pass"])
        self.assertTrue(out["result"]["fixed_point"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertEqual(out["engine"], "one_shot_reality_closure_v2.run")

        kwargs = one_shot_run.call_args.kwargs
        self.assertEqual(
            kwargs["state_path"],
            "canonical/astra_runtime/state/one-shot-test.json",
        )
        self.assertIs(kwargs["failure_repair_provider"], failure_provider)
        self.assertIs(kwargs["externality_certificate_provider"], externality_provider)
        self.assertIs(kwargs["capability_synthesis_provider"], synthesis_provider)
        self.assertIs(kwargs["evidence_acquisition_provider"], evidence_provider)
        self.assertEqual(kwargs["max_repair_rounds"], 3)
        self.assertEqual(kwargs["v1_max_rounds"], 11)
        self.assertEqual(kwargs["v1_max_actions_per_round"], 7)

    def test_one_shot_is_meta_orchestrator_not_live_owned_engine(self):
        self.assertIn("ONE_SHOT_REALITY_CLOSURE", fabric.META_ORCHESTRATORS)
        self.assertNotIn("ONE_SHOT_REALITY_CLOSURE", fabric.ENGINE_DESCRIPTORS)


if __name__ == "__main__":
    unittest.main(verbosity=2)

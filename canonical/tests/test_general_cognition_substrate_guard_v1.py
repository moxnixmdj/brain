import unittest
from unittest import mock

from canonical.runtime import enforce_goal_hierarchy as guard


class GeneralCognitionSubstrateGuardTests(unittest.TestCase):
    def setUp(self):
        guard.FAIL.clear()

    def tearDown(self):
        guard.FAIL.clear()

    def _intent(self):
        return {
            "action_kind": "REAL_TASK_EXECUTION",
            "capability_target": "TEST_COGNITIVE_CAPABILITY",
        }

    def _obs(self, *, include_config=True, role="GENERAL_COMPUTATION_COGNITION_SUBSTRATE",
             opaque_provider=False):
        preflight = {
            "execution_dependencies": [
                {
                    "dependency": "Qwen3.5-9B-M-local",
                    "kind": "LOCAL_MODEL",
                    "capability_role": role,
                    "opaque_target_capability_provider": opaque_provider,
                }
            ]
        }
        if include_config:
            preflight["brain_owned_capability_configuration"] = {
                "artifacts": [
                    "canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V3.md"
                ],
                "materially_load_bearing": True,
                "external_model_is_capability_provider": False,
                "promotion_evaluates_brain_configured_system": True,
                "configuration_survives_substrate_unavailability": True,
            }
        return {"route_frontier": {"selected_route_preflight": preflight}}

    def _run(self, obs):
        with mock.patch.object(
            guard,
            "_frontier_scope_chain",
            return_value=[{"parent_families": ["TECHNICAL_SCIENTIFIC_REASONING"]}],
        ):
            guard.enforce_cognition_substrate_ownership(self._intent(), obs)
        return list(guard.FAIL)

    def test_bare_model_route_still_fails_closed(self):
        errors = self._run(self._obs(include_config=False))
        self.assertIn("GENERAL_SUBSTRATE_BRAIN_CONFIGURATION_MISSING", errors)

    def test_opaque_capability_provider_still_rejected(self):
        errors = self._run(self._obs(opaque_provider=True))
        self.assertTrue(
            any(x.startswith("GENERAL_SUBSTRATE_OPAQUE_PROVIDER_FLAG_NOT_FALSE:") for x in errors),
            errors,
        )

    def test_model_must_be_declared_general_substrate(self):
        errors = self._run(self._obs(role="TARGET_CAPABILITY_PROVIDER"))
        self.assertTrue(
            any(x.startswith("GENERAL_SUBSTRATE_MODEL_ROLE_INVALID:") for x in errors),
            errors,
        )

    def test_current_law_allows_valid_general_substrate_under_brain_configuration(self):
        errors = self._run(self._obs())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

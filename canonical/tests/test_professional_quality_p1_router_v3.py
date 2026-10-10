from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime import professional_quality_p1_router_v3 as router


class ProfessionalQualityP1RouterV3Tests(unittest.TestCase):
    def test_current_profile_contract_is_bound(self):
        self.assertTrue(router._profile_ok())

    def test_non_object_state_fails_closed(self):
        out = router.route([])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "STATE_NOT_OBJECT")
        self.assertFalse(out["terminal_authority"])

    def test_preflight_cannot_be_self_attested(self):
        out = router.route({
            "step_results": {
                router.PREFLIGHT_STEP: "PASS",
            }
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PREFLIGHT_SELF_ATTESTATION_FORBIDDEN")

    def test_preflight_input_pair_is_required(self):
        for state in (
            {"artifact_paths": ["a.docx"], "step_results": {}},
            {"hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1", "step_results": {}},
        ):
            with self.subTest(state=state):
                out = router.route(state)
                self.assertEqual(out["status"], "FAIL_CLOSED")
                self.assertEqual(out["reason"], "PREFLIGHT_INPUT_PAIR_REQUIRED")

    def test_missing_preflight_inputs_abstains_instead_of_bypassing(self):
        out = router.route({"step_results": {}})
        self.assertEqual(out["status"], "ABSTAIN__P1_INCOMPLETE")
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertEqual(out["blocking_steps"], [router.PREFLIGHT_STEP])
        self.assertFalse(out["quality_judgment_authority"])
        self.assertFalse(out["terminal_authority"])

    @mock.patch.object(router.base, "route")
    @mock.patch.object(router.hard, "verify")
    def test_hard_defect_failure_blocks_base_router(self, verify, base_route):
        verify.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED__PROFILE_HARD_DEFECT_OR_INSPECTION_FAILURE",
            "terminal_authority": False,
        }
        out = router.route({
            "artifact_paths": ["a.docx"],
            "hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
            "step_results": {},
        })
        self.assertEqual(out["status"], "ABSTAIN__P1_HARD_FAILURE")
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertEqual(out["blocking_steps"], [router.PREFLIGHT_STEP])
        self.assertIs(out["hard_defect_preflight_result"], verify.return_value)
        base_route.assert_not_called()

    @mock.patch.object(router.base, "route")
    @mock.patch.object(router.hard, "verify")
    def test_verified_preflight_delegates_once_without_control_field_leakage(
        self, verify, base_route
    ):
        verify.return_value = {
            "pass": True,
            "status": "PASS__NO_PROFILE_REQUIRED_HARD_DEFECT_FOUND",
            "terminal_authority": False,
        }
        base_route.return_value = {
            "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V2",
            "status": "ROUTE__P1_ORDINARY",
            "route": "P1",
            "terminal_authority": False,
            "quality_judgment_authority": False,
        }
        state = {
            "artifact_paths": ["a.docx"],
            "hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
            "step_results": {"COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS": "PASS"},
            "detected_triggers": [],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile_path = root / router.PROFILE_PATH
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(json.dumps({
                "schema": router.PROFILE_SCHEMA,
                "steps": [router.PREFLIGHT_STEP],
                "hard_defect_preflight": {
                    "binding_git_blob_sha": router.BINDING_SHA,
                },
            }))
            out = router.route(state, repo_root=root)
            verify.assert_called_once_with({
                "artifact_paths": ["a.docx"],
                "profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
            })
            base_route.assert_called_once()
            delegated = base_route.call_args.args[0]
            self.assertNotIn("artifact_paths", delegated)
            self.assertNotIn("hard_defect_profile_id", delegated)
            self.assertEqual(
                delegated["step_results"],
                {"COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS": "PASS"},
            )
            self.assertEqual(base_route.call_args.kwargs["repo_root"], root)
        self.assertEqual(out["schema"], router.SCHEMA)
        self.assertIs(out["hard_defect_preflight_result"], verify.return_value)
        self.assertFalse(out["preflight_self_attestation_allowed"])
        self.assertFalse(out["terminal_authority"])

    def test_profile_contract_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / router.PROFILE_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            bad = {
                "schema": router.PROFILE_SCHEMA,
                "steps": [router.PREFLIGHT_STEP],
                "hard_defect_preflight": {
                    "binding_git_blob_sha": "0" * 40,
                },
            }
            path.write_text(json.dumps(bad))
            out = router.route({"step_results": {}}, repo_root=root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PROFILE_ROUTER_CONTRACT_DRIFT")

    def test_missing_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out = router.route({"step_results": {}}, repo_root=td)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PROFILE_LOAD_FAILURE")


if __name__ == "__main__":
    unittest.main()

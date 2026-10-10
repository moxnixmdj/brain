from __future__ import annotations

import unittest
from unittest import mock

from canonical.runtime import professional_quality_p1_router_v4 as router
from canonical.runtime import professional_target_instance_compiler_v1 as compiler


def target() -> dict:
    return {
        "schema": compiler.TARGET_SCHEMA,
        "source_id": "test://professional-target",
        "raw_task_text": "Create an evidence-grounded brief. Do not invent facts.",
        "objective": "Create an evidence-grounded professional brief.",
        "audience": "Executive reviewer",
        "source_evidence": ["evidence://packet/v1"],
        "artifact_type": "BRIEF",
        "hard_constraints": ["NO_UNSUPPORTED_FACTS"],
        "plausible_interpretations": ["EVIDENCE_GROUNDED_BRIEF"],
        "target_construct": "Professional brief quality under evidence constraints",
        "claim_scope": "Supplied evidence only",
        "current_draft_render": "NONE__NEW_ARTIFACT",
    }


class ProfessionalQualityP1RouterV4Tests(unittest.TestCase):
    def test_target_step_cannot_be_self_attested(self):
        out = router.route({
            "target_instance": target(),
            "step_results": {router.TARGET_STEP: "PASS"},
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_STEP_SELF_ATTESTATION_FORBIDDEN")
        self.assertFalse(out["terminal_authority"])

    def test_missing_target_instance_abstains_before_legacy_router(self):
        out = router.route({"step_results": {}})
        self.assertEqual(out["status"], "ABSTAIN__P1_INCOMPLETE")
        self.assertEqual(out["blocking_steps"], [router.TARGET_STEP])
        self.assertFalse(out["target_instance_compiled_by_brain"])

    @mock.patch.object(router.legacy, "route")
    @mock.patch.object(router.target_compiler, "compile_target")
    def test_verified_target_is_the_only_pass_injected_downstream(
        self, compile_target, legacy_route
    ):
        compile_target.return_value = {
            "pass": True,
            "status": "PASS__EXPLICIT_PROFESSIONAL_TARGET_INSTANCE_BOUND",
            "r1_target_step_verified": True,
            "target_instance_sha256": "a" * 64,
            "terminal_authority": False,
        }
        legacy_route.return_value = {
            "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V3",
            "status": "ABSTAIN__P1_INCOMPLETE",
            "route": "ABSTAIN",
            "blocking_steps": [router.PREFLIGHT_STEP],
            "terminal_authority": False,
        }
        state = {
            "target_instance": target(),
            "step_results": {"GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION": "OPEN"},
            "detected_triggers": [],
        }
        out = router.route(state)
        compile_target.assert_called_once()
        legacy_route.assert_called_once()
        delegated = legacy_route.call_args.args[0]
        self.assertNotIn("target_instance", delegated)
        self.assertEqual(delegated["step_results"][router.TARGET_STEP], "PASS")
        self.assertEqual(
            delegated["step_results"]["GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION"],
            "OPEN",
        )
        self.assertTrue(out["r1_target_step_verified"])
        self.assertTrue(out["target_instance_compiled_by_brain"])
        self.assertFalse(out["target_step_self_attestation_allowed"])
        self.assertFalse(out["terminal_authority"])

    @mock.patch.object(router.legacy, "route")
    @mock.patch.object(router.target_compiler, "compile_target")
    def test_failed_target_never_reaches_legacy_router(self, compile_target, legacy_route):
        compile_target.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "TARGET_LIST_FIELD_INVALID:plausible_interpretations",
            "r1_target_step_verified": False,
            "terminal_authority": False,
        }
        out = router.route({"target_instance": target(), "step_results": {}})
        legacy_route.assert_not_called()
        self.assertEqual(out["status"], "ABSTAIN__P1_TARGET_SPEC_UNRESOLVED")
        self.assertEqual(out["blocking_steps"], [router.TARGET_STEP])
        self.assertFalse(out["terminal_authority"])

    def test_actual_target_compilation_executes_then_legacy_preflight_remains_open(self):
        out = router.route({
            "target_instance": target(),
            "step_results": {},
            "detected_triggers": [],
        })
        self.assertEqual(out["status"], "ABSTAIN__P1_INCOMPLETE", out)
        self.assertTrue(out["r1_target_step_verified"], out)
        self.assertTrue(out["target_compilation_result"]["pass"], out)
        self.assertEqual(out["blocking_steps"], [router.PREFLIGHT_STEP], out)
        self.assertFalse(out["terminal_authority"])

    def test_actual_invalid_target_is_not_convertible_to_pass(self):
        t = target()
        t["plausible_interpretations"] = []
        out = router.route({
            "target_instance": t,
            "step_results": {},
        })
        self.assertEqual(out["status"], "ABSTAIN__P1_TARGET_SPEC_UNRESOLVED")
        self.assertFalse(out["target_compilation_result"]["pass"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

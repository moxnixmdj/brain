from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3


class R3IntegratorDispositionTotalityV1Tests(unittest.TestCase):
    def temp_state(self) -> Path:
        return Path(tempfile.mkdtemp()) / "state.json"

    def test_marker_only_success_becomes_durable_adapter_work(self):
        path = self.temp_state()
        out = {
            "pass": True,
            "status": "PASS__MARKER_ONLY",
            "current_episode_verified": False,
            "skill_candidate": None,
            "verified_executable_skill": None,
            "verified_skill_reuse_authorized": False,
        }
        integrated = r3.integrate_solver_output(out, state_path=path)

        self.assertEqual(
            integrated["status"],
            "SUCCESS_RETAINED__ADMISSIBLE_LEARNING_EVIDENCE_INCOMPLETE",
        )
        self.assertEqual(
            integrated["integration_disposition_reason"],
            "NO_ADMISSIBLE_LEARNING_EVIDENCE",
        )
        self.assertFalse(integrated["permanent_reuse_authorized"])
        work = r3.next_improvement_action(state_path=path)
        self.assertEqual(work["kind"], "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE")
        self.assertEqual(
            work["payload"]["required_result"],
            "VERIFIED_EPISODE_OR_TRUTHFUL_VERIFICATION_FRONTIER_DISPOSITION",
        )
        self.assertNotIn("PROVED_NONLEARNABLE", repr(work))

    def test_unaddressed_skill_candidate_cannot_create_phantom_verify_status(self):
        path = self.temp_state()
        out = {
            "pass": True,
            "status": "PASS__UNADDRESSED_CANDIDATE",
            "current_episode_verified": False,
            "skill_candidate": {"steps": [{"capability_id": "x"}]},
            "verified_executable_skill": None,
            "verified_skill_reuse_authorized": False,
        }
        integrated = r3.integrate_solver_output(out, state_path=path)

        self.assertEqual(
            integrated["status"],
            "SUCCESS_RETAINED__ADMISSIBLE_LEARNING_EVIDENCE_INCOMPLETE",
        )
        self.assertEqual(
            integrated["integration_disposition_reason"],
            "SKILL_CANDIDATE_MISSING_CONTENT_ADDRESS",
        )
        self.assertEqual(
            r3.next_improvement_action(state_path=path)["kind"],
            "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
        )

    def test_verified_episode_claim_without_episode_fails_closed(self):
        path = self.temp_state()
        with self.assertRaisesRegex(r3.SelfImprovementError, "VERIFIED_EPISODE_MISSING"):
            r3.integrate_solver_output(
                {
                    "pass": True,
                    "status": "PASS__BAD_EPISODE_AUTHORITY",
                    "current_episode_verified": True,
                    "current_episode": None,
                },
                state_path=path,
            )

    def test_verified_skill_reuse_claim_without_skill_fails_closed(self):
        path = self.temp_state()
        with self.assertRaisesRegex(
            r3.SelfImprovementError,
            "VERIFIED_SKILL_REUSE_AUTHORITY_MISSING",
        ):
            r3.integrate_solver_output(
                {
                    "pass": True,
                    "status": "PASS__BAD_SKILL_AUTHORITY",
                    "current_episode_verified": False,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": None,
                },
                state_path=path,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations\n\nimport unittest\nfrom unittest.mock import patch\n\nfrom canonical.runtime import one_shot_verified_closure_v1 as closure


class OneShotHistoricalEvidenceCertificateTests(unittest.TestCase):
    def _snap(self, pending):
        return {
            "schema": closure.SCHEMA,
            "digest": "same",
            "state_sha256": "state-same",
            "payload": {
                "state_file": {
                    "path": "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json",
                    "sha256": "state-same",
                    "bytes": 1,
                },
                "files": [],
                "pending": pending,
                "stats": {},
            },
        }

    def test_bounded_historical_certificate_refines_residual_without_fake_global_pass(self):
        pending = [{
            "work_id": "w-history",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "status": "PENDING",
            "last_attempt_status": "IMPROVEMENT_ACTION_EXCEPTION",
            "last_attempt_reason": (
                "SelfImprovementError:SUCCESS_OBSERVATION_NOT_REPLAYABLE:observation:x"
            ),
            "frontier_expansion_work_id": None,
            "payload": {
                "replayable": False,
                "proof_available": False,
                "replay_capsule_sha256": None,
                "proof_capsule_sha256": None,
            },
        }]
        blocker = {
            "work_id": "w-history",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        }
        cert = {
            "schema": "PROJECT_BRAIN_R3_HISTORICAL_EVIDENCE_IRREDUCIBILITY_V1",
            "status": "PASS__EXACT_HISTORICAL_SUCCESS_UNRECONSTRUCTIBLE_FROM_CURRENT_RETAINED_EVIDENCE",
            "pass": True,
            "irreducible_current_evidence_requirement_proved": True,
            "future_evidence_reopens": True,
            "terminal_authority": False,
        }
        snaps = [self._snap(pending), self._snap(pending), self._snap(pending)]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{"blockers": [blocker]}],
            },
        ), patch.object(
            closure.historical_evidence,
            "certify_pending_set",
            return_value=cert,
        ):
            out = closure.run(repo_root=".", state_path="state.json")

        self.assertFalse(out["pass"])
        self.assertTrue(out["fixed_point"])
        self.assertFalse(out["irreducible_external_information_proved"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertTrue(out["residual"]["internal_unsolved"])
        self.assertTrue(
            out["residual"]["pending_acquisition_or_experiment_required"]
        )
        self.assertTrue(out["residual"]["current_evidence_irreducibility_proved"])
        self.assertTrue(out["bounded_historical_evidence_certificate"]["pass"])
        self.assertFalse(out["verified_goal_satisfied_or_irreducible_external_only"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


def superset_skill() -> dict:
    return {
        "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
        "status": "VERIFIED_EXECUTABLE_SKILL",
        "source_episode_ids": ["ep1", "ep2"],
        "source_episode_receipts": ["EPVR:ep1", "EPVR:ep2"],
        "source_scopes": ["scope"],
        "steps": [{"index": 0, "op": "op0", "inputs": [], "outputs": ["goal"]}],
        "preconditions": [],
        "postconditions": ["goal"],
        "invalidators": [],
        "candidate_sha256": "sha256:" + ("7" * 64),
        "verified_skill": True,
        "reuse_authorized": True,
        "candidate_only": False,
        "scope_relation": "PROVEN_SUPERSET",
        "scope_predicate": learning.VERIFIED_SUPERSET_SCOPE_PREDICATE,
    }


class R3QuarantineRecoveryV1Tests(unittest.TestCase):
    def temp_state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def seed(self, path: Path, *, safe: bool = True) -> str:
        skill = superset_skill()
        sid = learning._skill_id(skill)
        family = learning._family_id(skill)
        state = learning._empty_state()
        state["skills"][sid] = {
            "skill": skill,
            "family_id": family,
            "pareto_metrics": learning._skill_pareto_row(sid, skill),
            "active": False,
            "quarantined": True,
            "generalization_counterexample_scopes": ["outside-scope"],
            "generalization_repromotion_blocked": True,
        }
        state["pareto_frontiers"][family] = []
        state["improvement_queue"] = {
            "recover": {
                "work_id": "recover",
                "kind": "REVERIFY_QUARANTINED_SKILL",
                "priority": 5,
                "identity": {"skill_id": sid},
                "payload": {
                    "skill_id": sid,
                    "family_id": family,
                    "counterexample_scope_id": "outside-scope",
                    "source_scopes": ["scope"],
                    "previous_scope_relation": "PROVEN_SUPERSET",
                    "scope_contraction_safe": safe,
                },
                "status": "PENDING",
                "observations": 1,
                "reopen_count": 0,
            }
        }
        learning._refresh_stats(state)
        learning._write_state(state, path)
        return sid

    def test_verified_exact_scope_recovery_reactivates_without_regeneralizing(self):
        path = self.temp_state()
        sid = self.seed(path)
        exact = {**superset_skill(), "scope_relation": "EXACT", "scope_predicate": None}
        provider = mock.Mock(return_value={"receipt": {}, "verification": {}})
        with mock.patch(
            "canonical.runtime.r3_quarantine_recovery_v1.authenticate_skill_verification",
            return_value={"pass": True, "verified_skill": exact},
        ):
            out = driver.advance_once(
                state_path=path,
                skill_verification_provider=provider,
            )

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(out["status"], "RECOVERED_BY_EXACT_SCOPE_CONTRACTION")
        state = learning.load_state(path)
        self.assertTrue(state["skills"][sid]["active"])
        self.assertEqual(state["skills"][sid]["skill"]["scope_relation"], "EXACT")
        self.assertTrue(state["skills"][sid]["recovered_from_quarantine_by_scope_contraction"])
        self.assertEqual(state["skills"][sid]["generalization_counterexample_scopes"], ["outside-scope"])
        self.assertFalse(any(
            row.get("kind") == "SEEK_VERIFIED_SCOPE_GENERALIZATION"
            and row.get("status") == "PENDING"
            and row.get("identity", {}).get("skill_id") == sid
            for row in state["improvement_queue"].values()
        ))
        request = provider.call_args.args[0]
        self.assertEqual(request["requested_scope_relation"], "EXACT")
        self.assertEqual(request["source_scopes"], ["scope"])

    def test_unsafe_quarantine_recovery_remains_blocked(self):
        path = self.temp_state()
        self.seed(path, safe=False)
        provider = mock.Mock()
        out = driver.advance_once(
            state_path=path,
            skill_verification_provider=provider,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        self.assertEqual(
            out["blockers"][0]["blocker"],
            "COUNTEREXAMPLE_REVERIFICATION_REQUIRES_FRESH_CANDIDATE_OR_REPLACEMENT",
        )
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import json
import shutil
import unittest
from copy import deepcopy
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json
from canonical.runtime import r3_direct_adequacy_success_adapter_v1 as adapter
from canonical.runtime import r3_direct_adequacy_readback_verifier_v1 as readback
from canonical.runtime import r3_independent_learning_verifier_v1 as independent


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_REL = "canonical/astra_runtime/tmp/R3_DIRECT_READBACK_TEST.json"
ARTIFACT = ROOT / ARTIFACT_REL
RECEIPT_REL = "canonical/astra_runtime/tmp/r3_direct_readback_receipts"
RECEIPTS = ROOT / RECEIPT_REL
GOAL = (
    "Create " + ARTIFACT_REL + " containing exactly "
    "one record with fields id and name: 1 alpha"
)


class R3DirectAdequacyReadbackV1Tests(unittest.TestCase):
    def setUp(self):
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        if ARTIFACT.exists():
            ARTIFACT.unlink()
        if RECEIPTS.exists():
            shutil.rmtree(RECEIPTS)

        pf = literal_json.preflight(GOAL, root=ROOT)
        self.assertTrue(pf["matched"], pf)
        ARTIFACT.write_text(
            json.dumps(pf["expected_records"], indent=2) + "\n",
            encoding="utf-8",
        )
        contract = literal_json.compile_contract(
            GOAL,
            source_id="user",
            routing_target_effects=[literal_json.ROUTING_EFFECT],
        )
        self.accepted_ids = list(
            contract["acceptance_contract"]["required_obligation_ids"]
        )
        self.request = {"task_id": "r3-direct-readback", "goal": GOAL}
        direct_out = {
            "schema": "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "pass": True,
            "r2_fixed_point_status": "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
            "route_id": "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1",
            "capability_id": None,
            "selected_policy_id": "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1",
            "goal_sha256": pf["goal_sha256"],
            "output_path": ARTIFACT_REL,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": self.accepted_ids,
            "raw_acceptance_obligation_count": len(self.accepted_ids),
            "terminal_authority": False,
        }
        self.capsule = learning._make_success_proof_capsule(direct_out)
        self.assertIsInstance(self.capsule, dict)
        self.assertEqual(
            self.capsule["material"]["proof_kind"],
            readback.VERIFICATION_KIND,
        )
        self.adapted = adapter.adapt(
            {
                "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                "observation": {"proof_capsule": deepcopy(self.capsule)},
                "replay_context": {
                    "mode": "decision",
                    "request": deepcopy(self.request),
                    "learn": True,
                },
                "improvement_work_id": "work:test",
                "authority_requested": "CANDIDATE_ONLY",
            },
            repo_root=ROOT,
        )
        self.assertIsInstance(self.adapted, dict)

    def tearDown(self):
        if ARTIFACT.exists():
            ARTIFACT.unlink()
        if RECEIPTS.exists():
            shutil.rmtree(RECEIPTS)

    def _verify(self, adapted=None):
        adapted = adapted or self.adapted
        solver = adapted["solver_output"]
        return readback.verify_material(
            problem=adapted["problem"],
            episode=solver["current_episode"],
            trace=solver["trace"],
            fact_capsule_head_hash=solver["state_capsule_head_hash"],
            value_capsule_head_hash=solver["value_capsule_head_hash"],
            repo_root=ROOT,
        )

    def test_literal_json_direct_success_reverifies_without_producer_replay(self):
        verdict = self._verify()
        self.assertTrue(verdict["pass"], verdict)
        self.assertFalse(verdict["execution_replayed"])
        self.assertTrue(verdict["producer_independent_readback"])
        self.assertEqual(
            verdict["accepted_raw_obligation_ids"],
            self.accepted_ids,
        )

    def test_artifact_mutation_fails_readback(self):
        ARTIFACT.write_text('[{"id":999,"name":"mutated"}]\n', encoding="utf-8")
        verdict = self._verify()
        self.assertFalse(verdict["pass"], verdict)
        self.assertIn("CURRENT_ARTIFACT_MISMATCH", verdict["reason"])

    def test_candidate_program_tampering_fails_readback(self):
        changed = deepcopy(self.adapted)
        changed["solver_output"]["current_episode"]["scope_id"] = "forged-scope"
        verdict = self._verify(changed)
        self.assertFalse(verdict["pass"], verdict)
        self.assertIn("DIRECT_EPISODE_CANDIDATE_MISMATCH", verdict["reason"])

    def test_independent_r3_verifier_emits_authenticated_pair_from_readback(self):
        solver = self.adapted["solver_output"]
        out = independent.verify_episode_request(
            {
                "kind": "EPISODE_VERIFICATION",
                "problem": self.adapted["problem"],
                "episode": solver["current_episode"],
                "trace": solver["trace"],
                "fact_capsule_head_hash": solver["state_capsule_head_hash"],
                "value_capsule_head_hash": solver["value_capsule_head_hash"],
            },
            repo_root=ROOT,
            receipt_dir=RECEIPT_REL,
        )
        self.assertIsInstance(out, dict)
        self.assertEqual(
            out["independent_verifier_id"],
            independent.INDEPENDENT_VERIFIER_ID,
        )
        self.assertTrue((ROOT / out["receipt"]["path"]).is_file())
        self.assertTrue((ROOT / out["verification"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)

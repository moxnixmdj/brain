from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import promote_r2_direct_live_route_v1 as promote
from canonical.runtime import r2_direct_live_dispatcher_v1 as live


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


BASELINE = """
def preflight(request, *, repo_root=None):
    goal = str(request.get("goal") or "")
    if goal in {"base", "overlap"}:
        return {"matched": True, "route_id": "BASE", "status": "MATCHED"}
    return {"matched": False, "status": "NOT_APPLICABLE"}

def run(request, *, repo_root=None):
    return {"matched": True, "route_id": "BASE", "pass": True, "status": "PASS_BASE"}
"""

DYNAMIC = """
def preflight(request, *, repo_root=None):
    goal = str(request.get("goal") or "")
    if goal in {"dynamic", "overlap"}:
        return {"matched": True, "route_id": "DYN", "status": "MATCHED"}
    return {"matched": False, "status": "NOT_APPLICABLE"}

def run(request, *, repo_root=None):
    return {"matched": True, "route_id": "DYN", "pass": True, "status": "PASS_DYN"}
"""


class PromoteR2DirectLiveRouteV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ("canonical/runtime", "canonical/governance", "canonical/verification"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)

        baseline_sha = self.write_text("canonical/runtime/fake_baseline.py", BASELINE)
        state = {
            "schema": live.STATE_SCHEMA,
            "status": "ACTIVE_R2_DIRECT_LIVE_STATE",
            "generation": 1,
            "baseline": {
                "runtime_path": "canonical/runtime/fake_baseline.py",
                "runtime_git_blob_sha": baseline_sha,
                "preflight_callable": "preflight",
                "run_callable": "run",
                "declared_route_count": 1,
                "declared_route_ids": ["BASE"],
            },
            "dynamic_routes": [],
            "terminal_authority": False,
        }
        state_raw = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()
        state_path = self.root / "canonical/governance/R2_DIRECT_LIVE_STATE_INITIAL.json"
        state_path.write_bytes(state_raw)
        self.initial_state_sha = blob_sha(state_raw)
        self.pointer = self.root / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"
        self.write_pointer(
            "canonical/governance/R2_DIRECT_LIVE_STATE_INITIAL.json",
            self.initial_state_sha,
        )
        self.initial_pointer_bytes = self.pointer.read_bytes()

        runtime_sha = self.write_text("canonical/runtime/fake_dynamic.py", DYNAMIC)
        verify_doc = {
            "schema": "FAKE_ROUTE_VERIFY_V1",
            "status": "PASS__INDEPENDENT_ROUTE_VERIFICATION",
            "pass": True,
            "terminal_authority": False,
        }
        verify_sha = self.write_json(
            "canonical/verification/fake_dynamic_route_verify.json",
            verify_doc,
        )
        self.candidate_rel = "canonical/governance/fake_dynamic_candidate.json"
        candidate = {
            "schema": promote.CANDIDATE_SCHEMA,
            "route_id": "DYN",
            "capability_id": "fake.dynamic",
            "runtime_path": "canonical/runtime/fake_dynamic.py",
            "runtime_git_blob_sha": runtime_sha,
            "preflight_callable": "preflight",
            "run_callable": "run",
            "route_verification_path": "canonical/verification/fake_dynamic_route_verify.json",
            "route_verification_git_blob_sha": verify_sha,
            "scope": "FAKE_DYNAMIC_SCOPE",
            "selection_class": promote.SELECTION_CLASS,
            "semantic_open_barrier": False,
            "deployment_requested": True,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }
        candidate_sha = self.write_json(self.candidate_rel, candidate)
        self.receipt_rel = "canonical/verification/fake_dynamic_deployment_receipt.json"
        receipt = {
            "schema": promote.RECEIPT_SCHEMA,
            "status": "INDEPENDENT_PASS__R2_DIRECT_LIVE_DEPLOYMENT",
            "candidate_path": self.candidate_rel,
            "candidate_git_blob_sha": candidate_sha,
            "route_id": "DYN",
            "runtime_path": "canonical/runtime/fake_dynamic.py",
            "runtime_git_blob_sha": runtime_sha,
            "route_verification_path": "canonical/verification/fake_dynamic_route_verify.json",
            "route_verification_git_blob_sha": verify_sha,
            "selection_class": promote.SELECTION_CLASS,
            "semantic_open_barrier": False,
            "semantic_open_barrier_authorized": False,
            "independent_verified": True,
            "preflight_pure_no_effect": True,
            "matched_route_failure_no_fallthrough": True,
            "producer_independent_acceptance": True,
            "exact_raw_obligation_acceptance": True,
            "deployment_eligible": True,
            "verification_authority_mutated": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "incremental_spend_usd": 0,
        }
        self.write_json(self.receipt_rel, receipt)

    def tearDown(self):
        self.tmp.cleanup()

    def write_text(self, rel: str, text: str) -> str:
        raw = text.encode()
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return blob_sha(raw)

    def write_json(self, rel: str, value) -> str:
        raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return blob_sha(raw)

    def write_pointer(self, target_rel: str, target_sha: str):
        value = {
            "schema": live.POINTER_SCHEMA,
            "status": "ACTIVE_CURRENT_R2_DIRECT_LIVE_STATE_POINTER",
            "binding_semantics": (
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__"
                "IMMUTABLE_TARGET_GIT_BLOB_BOUND"
            ),
            "target": {
                "path": target_rel,
                "git_blob_sha": target_sha,
                "schema": live.STATE_SCHEMA,
            },
            "terminal_authority": False,
        }
        self.pointer.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def promote(self, goal="dynamic"):
        return promote.promote(
            candidate_path=self.candidate_rel,
            receipt_path=self.receipt_rel,
            replay_request={"task_id": "original", "goal": goal},
            repo_root=self.root,
            pointer_path=self.pointer,
        )

    def test_verified_route_promotes_to_new_state_and_replays_through_current(self):
        out = self.promote()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["frontier_changed"])
        self.assertEqual(out["route_id"], "DYN")
        self.assertEqual(out["new_generation"], 2)
        self.assertTrue(out["postcommit_default_routable"])
        self.assertEqual(out["replay_route_id"], "DYN")

        state = live.load_state(repo_root=self.root, pointer_path=self.pointer)
        self.assertEqual(state["generation"], 2)
        self.assertEqual([r["route_id"] for r in state["dynamic_routes"]], ["DYN"])
        replay = live.preflight(
            {"task_id": "original", "goal": "dynamic"},
            repo_root=self.root,
            pointer_path=self.pointer,
        )
        self.assertTrue(replay["matched"], replay)
        self.assertEqual(replay["_live_route_source"], "DYNAMIC")

    def test_tampered_independent_receipt_fails_without_pointer_mutation(self):
        receipt_path = self.root / self.receipt_rel
        receipt = json.loads(receipt_path.read_text())
        receipt["deployment_eligible"] = False
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        with self.assertRaises(promote.R2DirectLivePromotionError):
            self.promote()
        self.assertEqual(self.pointer.read_bytes(), self.initial_pointer_bytes)

    def test_overlap_on_original_replay_rolls_pointer_back(self):
        with self.assertRaises(promote.R2DirectLivePromotionError):
            self.promote(goal="overlap")
        self.assertEqual(self.pointer.read_bytes(), self.initial_pointer_bytes)
        state = live.load_state(repo_root=self.root, pointer_path=self.pointer)
        self.assertEqual(state["generation"], 1)
        self.assertEqual(state["dynamic_routes"], [])

    def test_baseline_route_id_cannot_be_promoted_as_dynamic(self):
        candidate_path = self.root / self.candidate_rel
        receipt_path = self.root / self.receipt_rel
        candidate = json.loads(candidate_path.read_text())
        candidate["route_id"] = "BASE"
        candidate_sha = self.write_json(self.candidate_rel, candidate)
        receipt = json.loads(receipt_path.read_text())
        receipt["route_id"] = "BASE"
        receipt["candidate_git_blob_sha"] = candidate_sha
        self.write_json(self.receipt_rel, receipt)
        with self.assertRaises(promote.R2DirectLivePromotionError):
            self.promote(goal="base")
        self.assertEqual(self.pointer.read_bytes(), self.initial_pointer_bytes)

    def test_exact_repeat_is_idempotent_and_still_default_routable(self):
        first = self.promote()
        self.assertTrue(first["frontier_changed"])
        second = self.promote()
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["frontier_changed"])
        self.assertEqual(second["status"], "ALREADY_LIVE_EXACT_BINDING")
        self.assertTrue(second["postcommit_default_routable"])
        state = live.load_state(repo_root=self.root, pointer_path=self.pointer)
        self.assertEqual(len(state["dynamic_routes"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

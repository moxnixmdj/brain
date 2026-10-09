from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import r2_direct_live_dispatcher_v1 as live


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


BASELINE = """
def preflight(request, *, repo_root=None):
    goal = str(request.get("goal") or "")
    if goal == "base":
        return {"matched": True, "route_id": "BASE", "status": "MATCHED"}
    if goal == "open":
        return {
            "matched": False,
            "route_id": "BASE_OPEN",
            "status": "OPEN",
            "direct_route_semantic_open": True,
        }
    return {"matched": False, "status": "NOT_APPLICABLE"}

def run(request, *, repo_root=None):
    return {"matched": True, "route_id": "BASE", "pass": True, "status": "PASS_BASE"}
"""

DYNAMIC = """
def preflight(request, *, repo_root=None):
    goal = str(request.get("goal") or "")
    if goal in {"dynamic", "both"}:
        return {"matched": True, "route_id": "DYN", "status": "MATCHED"}
    if goal == "dynamic-open":
        return {
            "matched": False,
            "route_id": "DYN",
            "status": "OPEN",
            "direct_route_semantic_open": True,
        }
    return {"matched": False, "status": "NOT_APPLICABLE"}

def run(request, *, repo_root=None):
    return {"matched": True, "route_id": "DYN", "pass": True, "status": "PASS_DYN"}
"""

BASELINE_OVERLAP = BASELINE.replace(
    'if goal == "base":',
    'if goal in {"base", "both"}:',
)


class R2DirectLiveDispatcherV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "canonical/runtime").mkdir(parents=True)
        (self.root / "canonical/governance").mkdir(parents=True)
        (self.root / "canonical/verification").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> str:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = text.encode("utf-8")
        path.write_bytes(raw)
        return blob_sha(raw)

    def install_state(
        self,
        *,
        dynamic: bool = False,
        overlap: bool = False,
        dynamic_open_barrier: bool = False,
    ):
        baseline_sha = self.write(
            "canonical/runtime/fake_baseline.py",
            BASELINE_OVERLAP if overlap else BASELINE,
        )
        helper_sha = self.write(
            "canonical/runtime/fake_baseline_helper.py",
            "VALUE = 1\n",
        )
        activation = {
            "schema": "TEST_ACTIVATION_V1",
            "status": "ACTIVE_TEST",
            "current_routes": [{"route_id": "BASE"}],
        }
        activation_text = json.dumps(activation, indent=2, sort_keys=True) + "\n"
        activation_sha = self.write(
            "canonical/governance/fake_activation.json",
            activation_text,
        )
        routes = []
        if dynamic:
            dynamic_sha = self.write("canonical/runtime/fake_dynamic.py", DYNAMIC)
            verify = {
                "schema": "TEST_VERIFY_V1",
                "status": "PASS__INDEPENDENT",
                "pass": True,
                "terminal_authority": False,
            }
            verify_text = json.dumps(verify, sort_keys=True) + "\n"
            verify_sha = self.write(
                "canonical/verification/fake_dynamic_verify.json",
                verify_text,
            )
            routes.append(
                {
                    "route_id": "DYN",
                    "runtime_path": "canonical/runtime/fake_dynamic.py",
                    "runtime_git_blob_sha": dynamic_sha,
                    "preflight_callable": "preflight",
                    "run_callable": "run",
                    "verification_path": "canonical/verification/fake_dynamic_verify.json",
                    "verification_git_blob_sha": verify_sha,
                    "semantic_open_barrier": dynamic_open_barrier,
                }
            )

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
                "authority_activation_path": "canonical/governance/fake_activation.json",
                "authority_activation_git_blob_sha": activation_sha,
                "runtime_closure": [
                    {
                        "path": "canonical/runtime/fake_baseline.py",
                        "git_blob_sha": baseline_sha,
                    },
                    {
                        "path": "canonical/runtime/fake_baseline_helper.py",
                        "git_blob_sha": helper_sha,
                    },
                ],
            },
            "dynamic_routes": routes,
            "terminal_authority": False,
        }
        state_text = json.dumps(state, indent=2, sort_keys=True) + "\n"
        state_sha = self.write(
            "canonical/governance/R2_DIRECT_LIVE_STATE_TEST.json",
            state_text,
        )
        pointer = {
            "schema": live.POINTER_SCHEMA,
            "status": "ACTIVE_CURRENT_R2_DIRECT_LIVE_STATE_POINTER",
            "binding_semantics": (
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__"
                "IMMUTABLE_TARGET_GIT_BLOB_BOUND"
            ),
            "target": {
                "path": "canonical/governance/R2_DIRECT_LIVE_STATE_TEST.json",
                "git_blob_sha": state_sha,
                "schema": live.STATE_SCHEMA,
            },
            "terminal_authority": False,
        }
        pointer_path = self.root / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"
        pointer_path.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
        return pointer_path

    def test_baseline_match_and_semantic_open_are_preserved(self):
        pointer = self.install_state()
        matched = live.preflight(
            {"task_id": "t", "goal": "base"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertTrue(matched["matched"])
        self.assertEqual(matched["route_id"], "BASE")
        self.assertEqual(matched["_live_route_source"], "BASELINE")

        opened = live.preflight(
            {"task_id": "t", "goal": "open"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(opened["matched"])
        self.assertTrue(opened["direct_route_semantic_open"])
        self.assertEqual(opened["_live_route_source"], "BASELINE")

    def test_one_disjoint_dynamic_route_becomes_live_without_source_edit(self):
        pointer = self.install_state(dynamic=True)
        pf = live.preflight(
            {"task_id": "t", "goal": "dynamic"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertTrue(pf["matched"], pf)
        self.assertEqual(pf["route_id"], "DYN")
        self.assertEqual(pf["_live_route_source"], "DYNAMIC")

        out = live.run(
            {"task_id": "t", "goal": "dynamic"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route_id"], "DYN")
        self.assertEqual(out["_live_route_source"], "DYNAMIC")

    def test_dynamic_overlap_with_baseline_fails_closed(self):
        pointer = self.install_state(dynamic=True, overlap=True)
        out = live.preflight(
            {"task_id": "t", "goal": "both"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION")
        self.assertEqual(set(out["matching_route_ids"]), {"BASE", "DYN"})

    def test_dynamic_semantic_open_without_barrier_authority_fails_closed(self):
        pointer = self.install_state(dynamic=True, dynamic_open_barrier=False)
        out = live.preflight(
            {"task_id": "t", "goal": "dynamic-open"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_BARRIER_AUTHORITY",
        )

    def test_pointer_target_hash_drift_fails_closed(self):
        pointer = self.install_state()
        target = self.root / "canonical/governance/R2_DIRECT_LIVE_STATE_TEST.json"
        target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
        out = live.preflight(
            {"task_id": "t", "goal": "base"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CURRENT_LIVE_STATE_TARGET_BLOB_MISMATCH", out["reason"])

    def test_baseline_transitive_runtime_drift_fails_closed(self):
        pointer = self.install_state()
        helper = self.root / "canonical/runtime/fake_baseline_helper.py"
        helper.write_text("VALUE = 2\n", encoding="utf-8")
        out = live.preflight(
            {"task_id": "t", "goal": "base"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R2_DIRECT_LIVE_BASELINE_CLOSURE_BLOB_MISMATCH", out["reason"])

    def test_baseline_activation_drift_fails_closed(self):
        pointer = self.install_state()
        activation = self.root / "canonical/governance/fake_activation.json"
        activation.write_text(activation.read_text(encoding="utf-8") + " ", encoding="utf-8")
        out = live.preflight(
            {"task_id": "t", "goal": "base"},
            repo_root=self.root,
            pointer_path=pointer,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R2_DIRECT_LIVE_BASELINE_ACTIVATION_BLOB_MISMATCH", out["reason"])

    def test_catalog_declares_future_route_growth_source_edit_free(self):
        pointer = self.install_state(dynamic=True)
        out = live.catalog(repo_root=self.root, pointer_path=pointer)
        self.assertTrue(out["pass"])
        self.assertEqual(out["baseline_route_count"], 1)
        self.assertEqual(out["dynamic_route_count"], 1)
        self.assertFalse(out["future_route_source_edit_required"])
        self.assertFalse(out["future_fixed_point_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

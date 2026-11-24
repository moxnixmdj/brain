"""Controlled checks for the effect-bound carrier gate; no carrier qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import effect_bound_carrier_gate_v1 as gate
from canonical.tools import effect_bound_carrier_gate_v1 as tool
from canonical.tools import effect_bound_carrier_independent_verifier_v1 as independent

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EffectBoundCarrierGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_temp = tempfile.TemporaryDirectory(prefix="brain_effect_bound_source_")
        self.addCleanup(self.source_temp.cleanup)
        self.source_root = Path(self.source_temp.name)
        (self.source_root / "tiny.py").write_bytes(b"value = 1\n")
        self.fixture = {
            "id": "T1_MODIFY",
            "sources": ("tiny.py",),
            "mutations": ({"op": "modify", "path": "tiny.py"},),
        }
        self.git_state = {"base_commit": "0" * 40, "dirty_tree_sha256": "0" * 64}
        self.runner_sha = _sha(Path(tool.__file__).resolve(strict=True).read_bytes())

    def _run_fixture(self) -> tuple[dict, dict]:
        return tool.run_fixture(
            self.fixture,
            repo_root=self.source_root,
            code_root=REPO_ROOT,
            git_state=self.git_state,
            python_version="3.11.2",
            runner_source_sha256=self.runner_sha,
        )

    def test_real_fixture_produces_independently_verified_exact_bytes_without_authority(self) -> None:
        material, result = self._run_fixture()
        self.assertTrue(material["patch_nonempty"])
        self.assertIn(b"diff --git a/tiny.py b/tiny.py", material["patch_bytes"])
        self.assertTrue(result["receipt_verified"])
        self.assertTrue(result["independent_process_verification"])
        self.assertFalse(result["independent_attestation"])
        self.assertEqual(result["status"], "EFFECT_BOUND_RECEIPT_VERIFIED__CARRIER_NOT_QUALIFIED")
        self.assertEqual(result["patch_sha256"], _sha(material["patch_bytes"]))
        self.assertEqual(len(set(result["run_references"].values())), 4)
        self.assertNotEqual(result["verifier"]["verifier_pid"], os.getpid())
        self.assertTrue(result["verifier"]["git_apply_check_passed"])
        self.assertTrue(result["verifier"]["patch_replay_ok"])
        self.assertFalse(result["carrier_qualified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["patch_published"])
        self.assertEqual(result["section_6"], "NOT_DONE")
        self.assertFalse(result["completion_claim"])
        self.assertFalse(result["truth_achieved"])
        self.assertEqual(result["runtime_model_calls"], 0)
        self.assertEqual(result["runtime_network_calls"], 0)
        serialized = json.dumps(result, sort_keys=True).encode("utf-8")
        self.assertNotIn(b"diff --git", serialized)

    def test_preregistered_negative_cases_all_refuse(self) -> None:
        material, result = self._run_fixture()
        cases = tool.run_negative_cases(
            material,
            result,
            repo_root=REPO_ROOT,
            base_commit=self.git_state["base_commit"],
        )
        self.assertGreaterEqual(len(cases), 15)
        self.assertTrue(all(case["refused"] for case in cases))
        names = {case["name"] for case in cases}
        self.assertIn("caller_authority_field", names)
        self.assertIn("shared_run_references", names)
        self.assertIn("symlink_effect", names)
        self.assertIn("special_effect", names)
        self.assertIn("mutated_base", names)
        self.assertIn("verifier_script_digest_mismatch", names)
        self.assertIn("sentinel_outside_allocated_workspace", names)

    def test_external_store_is_inspectable_editable_deletable_and_restarts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="brain_effect_bound_store_") as temp:
            store_path = Path(temp) / "store.json"
            info = tool.prepare_store(
                store_path,
                repo_root=REPO_ROOT,
                receipt_relpath=tool.DEFAULT_RECEIPT_RELPATH,
            )
            self.assertTrue(info["created"])
            self.assertTrue(info["external_store_editability_ok"])
            self.assertTrue(info["store_removal_refused"])
            self.assertEqual(info["store_removal_refusal_reason"], "STORE_MISSING__REFUSE")
            self.assertTrue(info["restore_ok"])
            self.assertTrue(info["restart_digest_match"])
            self.assertTrue(store_path.is_file())
            self.assertEqual(store_path.read_bytes(), gate.canonical_bytes(info["document"]))
            self.assertNotIn("fixture", store_path.read_text(encoding="utf-8"))
            self.assertNotIn("outcome", store_path.read_text(encoding="utf-8"))

    def test_patch_parser_refuses_traversal_and_binary_metadata(self) -> None:
        with self.assertRaises(independent.Refused):
            independent.parse_patch_paths(
                b"diff --git a/../escape b/../escape\n--- /dev/null\n+++ b/../escape\n@@ -0,0 +1 @@\n+escape\n"
            )
        with self.assertRaises(independent.Refused):
            independent.parse_patch_paths(b"GIT binary patch\nliteral 0\n")

    def test_caller_authority_and_run_reference_collision_refuse(self) -> None:
        with self.assertRaises(gate.GateRefused):
            gate.deny_caller_authority({"carrier_qualified": True})
        with self.assertRaises(gate.GateRefused):
            gate.run_independent_verifier(
                receipt_bytes=b"{}",
                expected_receipt_sha256="0" * 64,
                effect_bytes={},
                baseline={"files": {}, "directories": (), "digest": "0" * 64},
                expected_effect_paths=(),
                expected_effect_sha256s={},
                expected_patch_sha256="0" * 64,
                expected_run_id="run",
                expected_base_commit="0" * 40,
                expected_runtime_policy_sha256="0" * 64,
                producer_run_ref="a" * 16,
                collector_run_ref="a" * 16,
                verifier_ticket_run_ref="b" * 16,
                code_root=REPO_ROOT,
            )


if __name__ == "__main__":
    unittest.main()

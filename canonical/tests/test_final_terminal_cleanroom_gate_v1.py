from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import final_terminal_cleanroom_gate_v1 as gate


class FinalTerminalCleanroomGateV1Tests(unittest.TestCase):
    def test_current_repository_cannot_cleanroom_pass_before_terminal_candidate(self):
        out = gate.evaluate(repo_root=gate.ROOT)
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["terminal_authority"])
        self.assertTrue(out["internal_unsolved"])
        self.assertFalse(out["final_cleanroom_executed"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__TERMINAL_PRECONDITIONS_NOT_CLOSED",
        )
        self.assertFalse(out["open_truth"]["terminal"])

    def _write_json(self, root: Path, rel: str, value: dict) -> tuple[str, str]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return rel, gate._git_blob(path)

    def _fixture(self, root: Path):
        terminal = {
            "schema": "SYNTHETIC_TERMINAL",
            "pointer_revision": 999,
            "live_truth": {
                "terminal": True,
                "current_U_empty_proved": True,
                "complete_selected_context_ABC_closed": True,
                "D_finality_closed": True,
                "frozen_terminal_family_pass_count": 19,
                "frozen_terminal_family_open_count": 0,
                "frozen_atomic_predicates_proved": 38,
                "frozen_atomic_predicates_unresolved": 0,
                "r2_primary_internal_unsolved_count": 0,
                "r2_primary_internal_unsolved_cell": None,
            },
        }
        self._write_json(root, gate.TERMINAL_PATH, terminal)

        candidate = "a" * 64
        bindings = {}
        for name in gate.REQUIRED_CONJUNCTS:
            rel = f"canonical/verification/{name}.json"
            receipt = {
                "schema": "SYNTHETIC_CONJUNCT",
                "status": "PASS",
                "pass": True,
                "independent_verifier_passed": True,
                "predicate": name,
                "value": 1,
                "candidate_sha256": candidate,
            }
            _, blob = self._write_json(root, rel, receipt)
            bindings[name] = {"path": rel, "git_blob_sha": blob}

        cleanroom_rel = "canonical/verification/cleanroom.json"
        cleanroom = {
            "schema": "SYNTHETIC_CLEANROOM",
            "status": "PASS",
            "pass": True,
            "independent_verifier_passed": True,
            "cleanroom_rebuilt_from_canonical_state": True,
            "donor_removed_or_unreachable": True,
            "network_denied": True,
            "behavior_preserved": True,
            "resource_constraints_satisfied": True,
            "external_contribution_census_complete": True,
            "full_runtime_dependency_inventory_complete": True,
            "runtime_cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "external_model_runtime_dependency_count": 0,
            "online_teacher_call_count": 0,
            "teacher_fallback_path_count": 0,
            "copied_or_rehosted_teacher_present": False,
            "brain_owned_operative_artifact": True,
            "operative_solver_role": "BRAIN_OWNED_NATIVE_MECHANISM",
            "undeclared_dependency_count": 0,
            "candidate_sha256": candidate,
        }
        _, cleanroom_blob = self._write_json(root, cleanroom_rel, cleanroom)
        manifest = {
            "candidate_sha256": candidate,
            "conjuncts": bindings,
            "cleanroom": {
                "path": cleanroom_rel,
                "git_blob_sha": cleanroom_blob,
            },
        }
        return manifest

    def _projection_pass(self):
        return {
            "pass": True,
            "current_r2": {"git_blob_sha": "b" * 40, "version": 999},
            "current_terminal_authority": {
                "git_blob_sha": "c" * 40,
                "pointer_revision": 999,
            },
        }

    def test_exact_six_part_final_proof_can_pass(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            with patch.object(
                gate.projection,
                "evaluate",
                return_value=self._projection_pass(),
            ):
                out = gate.evaluate(manifest, repo_root=root)

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["terminal_authority"])
        self.assertEqual(out["coverage"], 1)
        self.assertEqual(out["adequacy"], 1)
        self.assertEqual(out["ownership"], 1)
        self.assertEqual(out["reliability"], 1)
        self.assertEqual(out["resource_constraints_satisfied"], 1)
        self.assertEqual(out["donor_independence_cleanroom"], 1)
        self.assertEqual(out["errors"], [])

    def test_stale_receipt_blob_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            path = root / manifest["conjuncts"]["coverage"]["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["status"] = "MUTATED_AFTER_BINDING"
            path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

            with patch.object(
                gate.projection,
                "evaluate",
                return_value=self._projection_pass(),
            ):
                out = gate.evaluate(manifest, repo_root=root)

        self.assertFalse(out["pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertTrue(
            any("CONJUNCT_COVERAGE:BLOB_MISMATCH" in e for e in out["errors"]),
            out,
        )

    def test_self_asserted_conjunct_without_independent_verifier_fails(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            binding = manifest["conjuncts"]["adequacy"]
            path = root / binding["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["independent_verifier_passed"] = False
            path.write_text(
                json.dumps(receipt, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            binding["git_blob_sha"] = gate._git_blob(path)

            with patch.object(
                gate.projection,
                "evaluate",
                return_value=self._projection_pass(),
            ):
                out = gate.evaluate(manifest, repo_root=root)

        self.assertFalse(out["pass"])
        self.assertIn(
            "CONJUNCT_ADEQUACY:INDEPENDENT_VERIFIER_NOT_PASSED",
            out["errors"],
        )

    def test_cleanroom_without_donor_removal_fails(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            binding = manifest["cleanroom"]
            path = root / binding["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["donor_removed_or_unreachable"] = False
            path.write_text(
                json.dumps(receipt, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            binding["git_blob_sha"] = gate._git_blob(path)

            with patch.object(
                gate.projection,
                "evaluate",
                return_value=self._projection_pass(),
            ):
                out = gate.evaluate(manifest, repo_root=root)

        self.assertFalse(out["pass"])
        self.assertIn("CLEANROOM:DONOR_REMOVED_OR_UNREACHABLE_NOT_TRUE", out["errors"])

    def test_candidate_identity_mismatch_fails(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            binding = manifest["conjuncts"]["reliability"]
            path = root / binding["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["candidate_sha256"] = "d" * 64
            path.write_text(
                json.dumps(receipt, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            binding["git_blob_sha"] = gate._git_blob(path)

            with patch.object(
                gate.projection,
                "evaluate",
                return_value=self._projection_pass(),
            ):
                out = gate.evaluate(manifest, repo_root=root)

        self.assertFalse(out["pass"])
        self.assertIn("CONJUNCT_RELIABILITY:CANDIDATE_MISMATCH", out["errors"])

    def test_cleanroom_with_local_rehosted_model_fails(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            binding = manifest["cleanroom"]
            path = root / binding["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["copied_or_rehosted_teacher_present"] = True
            receipt["model_dependency_count"] = 1
            receipt["external_model_runtime_dependency_count"] = 1
            receipt["runtime_cognition_dependency_class"] = "MODEL_DEPENDENT"
            path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            binding["git_blob_sha"] = gate._git_blob(path)
            with patch.object(gate.projection, "evaluate", return_value=self._projection_pass()):
                out = gate.evaluate(manifest, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertIn("CLEANROOM:MODEL_DEPENDENCY_COUNT_NOT_ZERO", out["errors"])
        self.assertIn("CLEANROOM:COPIED_OR_REHOSTED_TEACHER_NOT_EXPLICITLY_FALSE", out["errors"])

    def test_cleanroom_unknown_model_dependency_inventory_fails(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._fixture(root)
            binding = manifest["cleanroom"]
            path = root / binding["path"]
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt.pop("full_runtime_dependency_inventory_complete")
            path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            binding["git_blob_sha"] = gate._git_blob(path)
            with patch.object(gate.projection, "evaluate", return_value=self._projection_pass()):
                out = gate.evaluate(manifest, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("CLEANROOM:RUNTIME_DEPENDENCY_INVENTORY_INCOMPLETE", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

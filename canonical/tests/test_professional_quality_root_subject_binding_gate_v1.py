from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_root_subject_binding_gate_v1 as gate


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


class RootSubjectBindingGateV1Tests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        subject_path = root / "canonical/governance/subject.json"
        subject = {
            "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V2",
            "subject_kind": "DECLARED_SYSTEM",
            "subject_id": "S",
            "subject_sha256": "a" * 64,
        }
        write(subject_path, subject)
        worklist = {
            "roots": [{
                "root_id": "R1_TARGET_SPECIFICATION",
                "semantic_support": "SEM",
                "execution_support": "EXE",
            }]
        }
        write(root / gate.WORKLIST_PATH, worklist)
        registry = {
            "entries": [
                {"root_id": "R1_TARGET_SPECIFICATION", "scope_id": "SEM"},
                {"root_id": "R1_TARGET_SPECIFICATION", "scope_id": "EXE"},
            ]
        }
        write(root / gate.REGISTRY_PATH, registry)
        bridge_path = root / "canonical/verification/bridge.json"
        bridge = {
            "schema": gate.BRIDGE_VERIFY_SCHEMA,
            "status": "PASS",
            "pass": True,
            "root_id": "R1_TARGET_SPECIFICATION",
            "subject_kind": "DECLARED_SYSTEM",
            "subject_id": "S",
            "subject_sha256": "a" * 64,
            "subject_git_blob_sha": blob(subject_path),
            "semantic_scope_id": "SEM",
            "execution_scope_id": "EXE",
            "root_specific_semantics_verified": True,
            "root_subject_binding_authority": True,
            "global_subject_identity_authority": False,
            "terminal_authority": False,
        }
        write(bridge_path, bridge)
        payload = {
            "root_id": "R1_TARGET_SPECIFICATION",
            "subject": {"path": "canonical/governance/subject.json", "git_blob_sha": blob(subject_path)},
            "semantic_scope_id": "SEM",
            "execution_scope_id": "EXE",
            "bridge_verification": {"path": "canonical/verification/bridge.json", "git_blob_sha": blob(bridge_path)},
        }
        current = {
            "pass": True,
            "status": "PASS",
            "subject_kind": "DECLARED_SYSTEM",
            "subject_id": "S",
            "subject_sha256": "a" * 64,
        }
        return td, root, payload, current, bridge_path

    def test_valid_independent_bridge_passes_structural_gate_only(self):
        td, root, payload, current, _ = self._repo()
        with td, patch.object(gate.subject_verify, "verify", return_value=current):
            out = gate.evaluate(payload, repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["binding"]["root_id"], "R1_TARGET_SPECIFICATION")

    def test_component_membership_without_bridge_cannot_pass(self):
        td, root, payload, current, _ = self._repo()
        with td, patch.object(gate.subject_verify, "verify", return_value=current):
            payload.pop("bridge_verification")
            out = gate.evaluate(payload, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertTrue(out["reason"].startswith("BRIDGE_"))

    def test_wrong_worklist_scope_fails_closed(self):
        td, root, payload, current, _ = self._repo()
        with td, patch.object(gate.subject_verify, "verify", return_value=current):
            payload["semantic_scope_id"] = "OTHER"
            out = gate.evaluate(payload, repo_root=root)
        self.assertEqual(out["reason"], "SEMANTIC_SCOPE_NOT_CURRENT_WORKLIST_SUPPORT")

    def test_bridge_must_bind_exact_subject_blob(self):
        td, root, payload, current, bridge_path = self._repo()
        with td:
            bridge = json.loads(bridge_path.read_text())
            bridge["subject_git_blob_sha"] = "0" * 40
            write(bridge_path, bridge)
            payload["bridge_verification"]["git_blob_sha"] = blob(bridge_path)
            with patch.object(gate.subject_verify, "verify", return_value=current):
                out = gate.evaluate(payload, repo_root=root)
        self.assertEqual(out["reason"], "BRIDGE_SUBJECT_BLOB_MISMATCH")

    def test_bridge_cannot_self_grant_without_root_semantics(self):
        td, root, payload, current, bridge_path = self._repo()
        with td:
            bridge = json.loads(bridge_path.read_text())
            bridge["root_specific_semantics_verified"] = False
            write(bridge_path, bridge)
            payload["bridge_verification"]["git_blob_sha"] = blob(bridge_path)
            with patch.object(gate.subject_verify, "verify", return_value=current):
                out = gate.evaluate(payload, repo_root=root)
        self.assertEqual(out["reason"], "ROOT_SPECIFIC_SEMANTICS_NOT_VERIFIED")

    def test_subject_currentness_failure_blocks_binding(self):
        td, root, payload, _, _ = self._repo()
        with td, patch.object(gate.subject_verify, "verify", return_value={"pass": False, "status": "FAIL_CLOSED", "reason": "STALE"}):
            out = gate.evaluate(payload, repo_root=root)
        self.assertEqual(out["reason"], "SUBJECT_CURRENTNESS_NOT_PROVED")


if __name__ == "__main__":
    unittest.main()

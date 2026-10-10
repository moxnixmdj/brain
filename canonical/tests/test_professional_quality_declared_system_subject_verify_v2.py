from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_declared_system_subject_verify_v2 as v


def git_blob(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def canon(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class DeclaredSystemSubjectVerifyV2Tests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        comp = root / "canonical/runtime/component.py"
        comp.parent.mkdir(parents=True)
        data = b"print('x')\n"
        comp.write_bytes(data)
        material = {
            "schema": v.MATERIAL_SCHEMA,
            "components": [{
                "path": "canonical/runtime/component.py",
                "git_blob_sha": git_blob(data),
            }],
        }
        subject = {
            "schema": v.SUBJECT_SCHEMA,
            "subject_kind": "DECLARED_SYSTEM",
            "subject_id": "S",
            "subject_sha256": sha256(canon(material)).hexdigest(),
            "system_material": material,
            "identity_semantics": {
                "component_inclusion_does_not_imply_root_satisfaction": True,
                "scoped_evidence_inclusion_does_not_transport_scope": True,
                "root_subject_binding_requires_independent_verification": True,
                "global_subject_identity_authority": False,
            },
            "terminal_authority": False,
        }
        sp = root / v.DEFAULT_SUBJECT_PATH
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(subject), encoding="utf-8")
        return td, root, subject, comp, sp

    def test_valid_subject_passes_with_zero_root_authority(self):
        td, root, _, _, _ = self._repo()
        with td:
            out = v.verify(repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["subject_identity_verified"])
            self.assertTrue(out["component_currentness_verified"])
            self.assertFalse(out["root_subject_binding_authority"])
            self.assertFalse(out["terminal_authority"])

    def test_forged_subject_hash_fails_closed(self):
        td, root, subject, _, sp = self._repo()
        with td:
            subject["subject_sha256"] = "0" * 64
            sp.write_text(json.dumps(subject), encoding="utf-8")
            out = v.verify(repo_root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertEqual(out["reason"], "SUBJECT_HASH_MISMATCH")

    def test_stale_component_blob_fails_closed(self):
        td, root, _, comp, _ = self._repo()
        with td:
            comp.write_text("print('changed')\n", encoding="utf-8")
            out = v.verify(repo_root=root)
            self.assertEqual(out["reason"], "COMPONENT_BLOB_STALE")

    def test_path_escape_fails_closed(self):
        td, root, subject, _, sp = self._repo()
        with td:
            subject["system_material"]["components"][0]["path"] = "canonical/../../escape"
            subject["subject_sha256"] = sha256(canon(subject["system_material"])).hexdigest()
            sp.write_text(json.dumps(subject), encoding="utf-8")
            out = v.verify(repo_root=root)
            self.assertEqual(out["reason"], "COMPONENT_FILE_INVALID")

    def test_component_membership_cannot_grant_root_authority(self):
        td, root, subject, _, sp = self._repo()
        with td:
            subject["identity_semantics"]["component_inclusion_does_not_imply_root_satisfaction"] = False
            subject["subject_sha256"] = sha256(canon(subject["system_material"])).hexdigest()
            sp.write_text(json.dumps(subject), encoding="utf-8")
            out = v.verify(repo_root=root)
            self.assertEqual(out["reason"], "ROOT_SATISFACTION_NONAUTHORITY_REQUIRED")


if __name__ == "__main__":
    unittest.main()

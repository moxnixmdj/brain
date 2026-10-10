from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import escape_progress_shared_gap_audit_v5 as v5


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class EscapeProgressAuditV5CurrentnessTests(unittest.TestCase):
    def test_mutable_current_source_revalidates_required_strings_against_current_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/governance/CURRENT_EXAMPLE.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"status":"NEW_STATE","next":"NEW_ACTION"}))
            row={
                "obligation_id":"ROW",
                "evidence":["canonical/governance/CURRENT_EXAMPLE.json","deadbeef"],
                "required_strings":["NEW_STATE","NEW_ACTION"],
            }
            out=v5._resolve_row_current_evidence(row, repo_root=root)
            self.assertTrue(out["pass"])
            self.assertEqual(out["binding_mode"],"MUTABLE_CURRENT_PATH")
            self.assertEqual(out["git_blob_sha"],_blob(p.read_bytes()))

            stale=dict(row, required_strings=["OLD_STATE"])
            out=v5._resolve_row_current_evidence(stale, repo_root=root)
            self.assertTrue(out["pass"])
            self.assertEqual(out["errors"], [])
            self.assertIn("MUTABLE_REQUIRED_STRING_DRIFT:OLD_STATE",out["warnings"])

    def test_immutable_source_requires_manifest_blob_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/governance/IMMUTABLE.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"status":"BOUND"}))
            good={
                "obligation_id":"ROW",
                "evidence":["canonical/governance/IMMUTABLE.json",_blob(p.read_bytes())],
                "required_strings":["BOUND"],
            }
            self.assertTrue(v5._resolve_row_current_evidence(good, repo_root=root)["pass"])
            bad=dict(good, evidence=[good["evidence"][0],"0"*40])
            out=v5._resolve_row_current_evidence(bad, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertIn("IMMUTABLE_EVIDENCE_BLOB_MISMATCH",out["errors"])

    def test_independent_verifier_must_bind_exact_current_evidence_subject(self):
        current={
            "path":"canonical/governance/CURRENT_EXAMPLE.json",
            "git_blob_sha":"a"*40,
            "byte_sha256":"b"*64,
        }
        verify={
            "current_route_semantics_verified": True,
            "current_evidence_subject":dict(current),
        }
        self.assertEqual(v5._current_evidence_verification_errors(verify,current),[])
        verify["current_evidence_subject"]["git_blob_sha"]="c"*40
        self.assertIn(
            "ROW_PROOF_CURRENT_EVIDENCE_SUBJECT_MISMATCH:git_blob_sha",
            v5._current_evidence_verification_errors(verify,current),
        )
        missing_semantics={
            "current_evidence_subject":dict(current),
        }
        self.assertIn(
            "ROW_PROOF_CURRENT_ROUTE_SEMANTICS_NOT_VERIFIED",
            v5._current_evidence_verification_errors(missing_semantics,current),
        )

    def test_current_resolution_follows_classification_to_binding_to_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            gov=root/"canonical/governance"
            gov.mkdir(parents=True)
            (gov/"CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").write_text(json.dumps({
                "classifications":[
                    {"residual_id":"ESCAPE_GAP_A_ACQUISITION_TOTALITY","existing_binding":"canonical/governance/BIND.json"},
                    {"residual_id":"ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS","existing_binding":"canonical/governance/BIND.json"},
                ]
            }))
            (gov/"BIND.json").write_text(json.dumps({
                "current_successor_manifest":{"path":"canonical/governance/MANIFEST.json"}
            }))
            (gov/"MANIFEST.json").write_text(json.dumps({"rows":[]}))
            resolved=v5._load_current_manifest_binding(repo_root=root)
            self.assertEqual(resolved["binding_path"],"canonical/governance/BIND.json")
            self.assertEqual(resolved["manifest_path"],"canonical/governance/MANIFEST.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)

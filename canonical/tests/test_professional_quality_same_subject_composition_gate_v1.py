from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_same_subject_composition_gate_v1 as gate
from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped_overlay

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"
ROOTS = sorted(gate.EXPECTED_ROOTS)


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _subject_sha(subject_kind: str, subject_id: str) -> str:
    return hashlib.sha256((subject_kind + "\0" + subject_id).encode("utf-8")).hexdigest()


class _V1ScopedAdapter:
    @staticmethod
    def evaluate(*, repo_root: Path = ROOT) -> dict:
        out = dict(scoped_overlay.evaluate(repo_root=repo_root))
        seen = set()
        dedup = []
        for row in out.get("admitted_scopes") or []:
            rid = row.get("root_id")
            if rid not in seen:
                seen.add(rid)
                dedup.append(row)
        out["admitted_scopes"] = dedup
        out["admitted_scope_count"] = len(dedup)
        return out


class ProfessionalQualitySameSubjectCompositionGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_scoped = gate.scoped
        gate.scoped = _V1ScopedAdapter

    def tearDown(self) -> None:
        gate.scoped = self._orig_scoped
    def _bindings(
        self,
        work: Path,
        *,
        overrides: dict[str, tuple[str, str]] | None = None,
        verify_authority: bool = True,
    ) -> list[dict]:
        overrides = overrides or {}
        rows: list[dict] = []
        for i, root_id in enumerate(ROOTS):
            subject_kind, subject_id = overrides.get(
                root_id,
                ("ARTIFACT", "artifact://professional-quality/example-v1"),
            )
            subject_sha = _subject_sha(subject_kind, subject_id)
            binding_doc = {
                "schema": gate.BINDING_SCHEMA,
                "root_id": root_id,
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "subject_sha256": subject_sha,
                "global_subject_identity_authority": False,
                "terminal_authority": False,
            }
            binding_path = work / f"binding_{i:02d}.json"
            _write_json(binding_path, binding_doc)
            binding_blob = gate._git_blob_sha(binding_path)

            verify_doc = {
                "schema": gate.VERIFY_SCHEMA,
                "pass": True,
                "root_id": root_id,
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "subject_sha256": subject_sha,
                "subject_binding_git_blob_sha": binding_blob,
                "root_subject_binding_authority": verify_authority,
                "global_subject_identity_authority": False,
                "terminal_authority": False,
            }
            verify_path = work / f"verify_{i:02d}.json"
            _write_json(verify_path, verify_doc)
            rows.append(
                {
                    "root_id": root_id,
                    "binding": {
                        "path": binding_path.relative_to(ROOT).as_posix(),
                        "git_blob_sha": binding_blob,
                    },
                    "verification": {
                        "path": verify_path.relative_to(ROOT).as_posix(),
                        "git_blob_sha": gate._git_blob_sha(verify_path),
                    },
                }
            )
        return rows

    def test_no_bindings_remains_open_and_grants_zero_authority(self):
        out = gate.evaluate({"root_subject_bindings": []})
        self.assertEqual(out["status"], "OPEN__SAME_SUBJECT_BINDINGS_REQUIRED", out)
        self.assertFalse(out["pass"])
        self.assertEqual(out["missing_root_ids"], ROOTS)
        self.assertFalse(out["composition_admissible"])
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_all_twelve_exact_same_verified_subject_are_composition_admissible_only(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td))
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE",
            out,
        )
        self.assertTrue(out["composition_admissible"])
        self.assertEqual(out["scoped_root_count"], 12)
        self.assertEqual(out["verified_root_subject_binding_count"], 12)
        self.assertEqual(out["composed_subject"]["subject_kind"], "ARTIFACT")
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_one_different_subject_keeps_root_conjunction_open(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(
                Path(td),
                overrides={
                    "R12_META_COMPOSITION_CLOSURE": (
                        "ARTIFACT",
                        "artifact://professional-quality/different-v2",
                    )
                },
            )
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__ROOT_SUBJECT_BINDINGS_NOT_IDENTICAL",
            out,
        )
        self.assertEqual(out["distinct_subject_count"], 2)
        self.assertFalse(out["composition_admissible"])
        self.assertFalse(out["professional_quality_closed"])

    def test_missing_one_root_binding_remains_open(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td))
            missing_root = rows[-1]["root_id"]
            out = gate.evaluate({"root_subject_bindings": rows[:-1]})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__SAME_SUBJECT_BINDINGS_INCOMPLETE", out)
        self.assertEqual(out["missing_root_ids"], [missing_root])

    def test_duplicate_root_binding_fails_closed(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td))
            rows.append(dict(rows[0]))
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "ROOT_SUBJECT_BINDING_ROOT_DUPLICATE")

    def test_stale_binding_blob_fails_closed(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td))
            rows[0]["binding"]["git_blob_sha"] = "0" * 40
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "SUBJECT_BINDING_BLOB_STALE")

    def test_verification_must_bind_exact_binding_blob(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            work = Path(td)
            rows = self._bindings(work)
            verify_path = ROOT / rows[0]["verification"]["path"]
            verify_doc = json.loads(verify_path.read_text(encoding="utf-8"))
            verify_doc["subject_binding_git_blob_sha"] = "0" * 40
            _write_json(verify_path, verify_doc)
            rows[0]["verification"]["git_blob_sha"] = gate._git_blob_sha(verify_path)
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "SUBJECT_BINDING_VERIFY_BLOB_MISMATCH")

    def test_root_subject_binding_authority_is_required_but_global_authority_is_forbidden(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td), verify_authority=False)
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED")

    def test_binding_cannot_self_grant_global_subject_identity(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP) as td:
            rows = self._bindings(Path(td))
            binding_path = ROOT / rows[0]["binding"]["path"]
            binding_doc = json.loads(binding_path.read_text(encoding="utf-8"))
            binding_doc["global_subject_identity_authority"] = True
            _write_json(binding_path, binding_doc)
            rows[0]["binding"]["git_blob_sha"] = gate._git_blob_sha(binding_path)
            verify_path = ROOT / rows[0]["verification"]["path"]
            verify_doc = json.loads(verify_path.read_text(encoding="utf-8"))
            verify_doc["subject_binding_git_blob_sha"] = rows[0]["binding"]["git_blob_sha"]
            _write_json(verify_path, verify_doc)
            rows[0]["verification"]["git_blob_sha"] = gate._git_blob_sha(verify_path)
            out = gate.evaluate({"root_subject_bindings": rows})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)

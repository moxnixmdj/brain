from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.current_authority_runtime_binding_census_refinement_checker_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "canonical/governance/CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_ABSTRACT_SPEC_20261010_V1.json"
SUBJECT_REL = Path("canonical/runtime/current_authority_runtime_binding_census_v1.py")


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = sha1()
    h.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    h.update(data)
    return h.hexdigest()


def _temp_subject(source: str) -> tuple[tempfile.TemporaryDirectory, Path]:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    path = root / SUBJECT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return td, root


class CurrentAuthorityRuntimeBindingCensusRefinementCheckerV1Tests(unittest.TestCase):
    def test_current_subject_passes_branch_surface_refinement(self):
        out = verify(_spec(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["refinement_verified"])
        self.assertEqual(out["error_kind_count"], 4)
        self.assertEqual(out["branch_case_count"], 11)
        self.assertEqual(out["exception_case_count"], 2)
        self.assertEqual(out["witness_count"], 13)
        self.assertFalse(out["repository_wide_refinement"])
        self.assertFalse(out["transitive_dependency_refinement"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_abstract_branch_case_is_rejected(self):
        spec = _spec()
        spec["branch_cases"] = [
            row for row in spec["branch_cases"]
            if row["id"] != "STALE_CURRENT_DRIFT"
        ]
        out = verify(spec, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BRANCH_CASE_SET_MISMATCH")

    def test_subject_blob_drift_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8") + "\n"
        td, root = _temp_subject(source)
        try:
            out = verify(_spec(), repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "SUBJECT_BLOB_DRIFT")
        finally:
            td.cleanup()

    def test_new_error_kind_without_spec_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8")
        source = source.replace(
            '"RUNTIME_BLOB_DRIFT"',
            '"RUNTIME_BLOB_DRIFT_V2"',
            1,
        )
        td, root = _temp_subject(source)
        try:
            spec = _spec()
            spec["subject"]["git_blob_sha"] = _git_blob_sha(root / SUBJECT_REL)
            out = verify(spec, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "ERROR_KIND_CENSUS_MISMATCH")
        finally:
            td.cleanup()

    def test_supersession_logic_mutation_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8")
        source = source.replace(
            'or "SUPERSEDED" in local_status.upper()',
            'and "SUPERSEDED" in local_status.upper()',
            1,
        )
        td, root = _temp_subject(source)
        try:
            spec = _spec()
            spec["subject"]["git_blob_sha"] = _git_blob_sha(root / SUBJECT_REL)
            out = verify(spec, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                out["reason"].startswith("BRANCH_PROJECTION_MISMATCH:"),
                out,
            )
        finally:
            td.cleanup()

    def test_success_status_mutation_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8")
        source = source.replace(
            '"PASS__CURRENT_RUNTIME_BYTE_BINDINGS_COHERENT"',
            '"PASS__BROKEN_RUNTIME_BINDING_SEMANTICS"',
            1,
        )
        td, root = _temp_subject(source)
        try:
            spec = _spec()
            spec["subject"]["git_blob_sha"] = _git_blob_sha(root / SUBJECT_REL)
            out = verify(spec, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                out["reason"].startswith("BRANCH_PROJECTION_MISMATCH:"),
                out,
            )
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.terminal_root_decision_gate_refinement_checker_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "canonical/governance/TERMINAL_ROOT_DECISION_GATE_ABSTRACT_SPEC_20261010_V1.json"
SUBJECT_REL = Path("canonical/runtime/terminal_root_decision_gate_v1.py")


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


class TerminalRootDecisionGateRefinementCheckerV1Tests(unittest.TestCase):
    def test_current_subject_passes_branch_surface_refinement(self):
        out = verify(_spec(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["refinement_verified"])
        self.assertEqual(out["fail_reason_count"], 17)
        self.assertEqual(out["success_case_count"], 4)
        self.assertEqual(out["witness_count"], 21)
        self.assertFalse(out["repository_wide_refinement"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_abstract_fail_branch_is_rejected(self):
        spec = _spec()
        spec["fail_reasons"].remove("PROOF_KIND_INVALID")
        out = verify(spec, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FAIL_REASON_CENSUS_MISMATCH")

    def test_subject_blob_drift_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8") + "\n"
        td, root = _temp_subject(source)
        try:
            out = verify(_spec(), repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "SUBJECT_BLOB_DRIFT")
        finally:
            td.cleanup()

    def test_new_concrete_fail_branch_without_spec_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8")
        source = source.replace(
            '"PAYLOAD_MAPPING_REQUIRED"',
            '"PAYLOAD_MAPPING_REQUIRED_V2"',
            1,
        )
        td, root = _temp_subject(source)
        try:
            spec = _spec()
            spec["subject"]["git_blob_sha"] = _git_blob_sha(root / SUBJECT_REL)
            out = verify(spec, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "FAIL_REASON_CENSUS_MISMATCH")
        finally:
            td.cleanup()

    def test_success_projection_mutation_is_rejected(self):
        source = (ROOT / SUBJECT_REL).read_text(encoding="utf-8")
        source = source.replace(
            '"PASS__TERMINAL_ROOT_NOT_X_PROVED"',
            '"PASS__BROKEN_REFINEMENT"',
            1,
        )
        td, root = _temp_subject(source)
        try:
            spec = _spec()
            spec["subject"]["git_blob_sha"] = _git_blob_sha(root / SUBJECT_REL)
            out = verify(spec, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["reason"].startswith("SUCCESS_PROJECTION_MISMATCH:"))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)

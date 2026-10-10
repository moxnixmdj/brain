from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.executable_refinement_verifier_v1 import (
    MAX_ARTIFACT_BYTES,
    MAX_CONCRETE_IMPLEMENTATIONS,
    MAX_PROOF_DEPENDENCIES,
    MAX_TRANSITION_CLASSES,
    SCHEMA,
    git_blob_sha,
    load_and_verify_certificate_file,
    verify_certificate,
)


class ExecutableRefinementResourceBoundsV1Tests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        abstract = root / "abstract.json"
        concrete = root / "impl.py"
        abstract.write_text("{}\n", encoding="utf-8")
        concrete.write_text("x=1\n", encoding="utf-8")
        return {
            "schema": SCHEMA,
            "proof_class": "DECLARATIVE_BOUNDING",
            "subject_id": "bounded-fixture",
            "abstract_spec": {
                "path": "abstract.json",
                "git_blob_sha": git_blob_sha(abstract),
                "semantic_version": "V1",
            },
            "concrete_implementation": [
                {"path": "impl.py", "git_blob_sha": git_blob_sha(concrete)}
            ],
            "state_mapping": {"proved": True, "mode": "STATELESS"},
            "input_binding": {"proved": True, "mode": "DIRECT_TYPED_MAPPING"},
            "transition_refinement": {
                "coverage_mode": "DECLARED_FINITE_PARTITION",
                "unsupported_behavior": "FAIL_CLOSED",
                "classes": [{"case_id": "PASS", "kind": "PASS"}],
            },
            "observation_refinement": {
                "proved": True,
                "mode": "EXACT_GOAL_PROJECTION",
            },
            "nondeterminism_contract": {"proved": True, "mode": "DETERMINISTIC"},
            "safety_refinement": {"proved": True},
            "liveness_refinement": {"required": False, "proved": False},
            "proof_dependencies": [],
            "terminal_credit_delta": 0,
        }

    def test_concrete_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._fixture(root)
            raw["concrete_implementation"] *= MAX_CONCRETE_IMPLEMENTATIONS + 1
            out = verify_certificate(raw, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CONCRETE_IMPLEMENTATION_COUNT_EXCEEDED")

    def test_dependency_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._fixture(root)
            raw["proof_dependencies"] = [
                dict(raw["concrete_implementation"][0])
                for _ in range(MAX_PROOF_DEPENDENCIES + 1)
            ]
            out = verify_certificate(raw, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "PROOF_DEPENDENCY_COUNT_EXCEEDED")

    def test_transition_class_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._fixture(root)
            raw["transition_refinement"]["classes"] = [
                {"case_id": f"C{i}", "kind": "PASS"}
                for i in range(MAX_TRANSITION_CLASSES + 1)
            ]
            out = verify_certificate(raw, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "TRANSITION_CLASS_COUNT_EXCEEDED")

    def test_oversized_bound_artifact_fails_before_hashing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._fixture(root)
            large = root / "large.py"
            with large.open("wb") as fh:
                fh.truncate(MAX_ARTIFACT_BYTES + 1)
            raw["concrete_implementation"] = [
                {"path": "large.py", "git_blob_sha": "0" * 40}
            ]
            out = verify_certificate(raw, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["reason"],
                "CONCRETE_IMPLEMENTATION_0_SIZE_LIMIT_EXCEEDED",
            )

    def test_file_entrypoint_rejects_oversized_certificate_before_json_parse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "certificate.json"
            with path.open("wb") as fh:
                fh.truncate(2_000_000)
            out = load_and_verify_certificate_file(path, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CERTIFICATE_FILE_SIZE_LIMIT_EXCEEDED")

    def test_bounded_fixture_still_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._fixture(root)
            cert = root / "certificate.json"
            cert.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
            out = load_and_verify_certificate_file(cert, repo_root=root)
            self.assertTrue(out["pass"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

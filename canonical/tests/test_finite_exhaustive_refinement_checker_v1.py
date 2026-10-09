from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.finite_exhaustive_refinement_checker_v1 import (
    ABSTRACT_SCHEMA,
    PROOF_CLASS,
    PROOF_SCHEMA,
    RECEIPT_SCHEMA,
    TRACE_SCHEMA,
    git_blob_sha,
    verify_finite_refinement,
)


class FiniteExhaustiveRefinementCheckerTests(unittest.TestCase):
    def fixture(self, root: Path):
        abstract = root / "canonical/governance/abstract.json"
        concrete = root / "canonical/runtime/subject.py"
        trace = root / "canonical/verification/trace.json"
        abstract.parent.mkdir(parents=True, exist_ok=True)
        concrete.parent.mkdir(parents=True, exist_ok=True)
        trace.parent.mkdir(parents=True, exist_ok=True)

        domain = [0, 1, 2, 3]
        expected = [
            {"input": x, "output": {"class": "EVEN" if x % 2 == 0 else "ODD"}}
            for x in domain
        ]
        abstract.write_text(
            json.dumps({
                "schema": ABSTRACT_SCHEMA,
                "closed_domain": True,
                "domain": domain,
                "expected": expected,
            }) + "\n",
            encoding="utf-8",
        )
        concrete.write_text(
            "def classify(x):\n    return {'class': 'EVEN' if x % 2 == 0 else 'ODD'}\n",
            encoding="utf-8",
        )
        trace.write_text(
            json.dumps({
                "schema": TRACE_SCHEMA,
                "subject_id": "fixture",
                "concrete_git_blob_sha": git_blob_sha(concrete),
                "callable": "classify",
                "independent_execution": True,
                "execution_complete": True,
                "execution_error_count": 0,
                "side_effect_class": "PURE_ISOLATED",
                "rows": expected,
            }) + "\n",
            encoding="utf-8",
        )
        proof = {
            "schema": PROOF_SCHEMA,
            "proof_class": PROOF_CLASS,
            "subject_id": "fixture",
            "abstract_spec": {
                "path": "canonical/governance/abstract.json",
                "git_blob_sha": git_blob_sha(abstract),
            },
            "concrete_implementation": {
                "path": "canonical/runtime/subject.py",
                "git_blob_sha": git_blob_sha(concrete),
                "callable": "classify",
            },
            "execution_trace": {
                "path": "canonical/verification/trace.json",
                "git_blob_sha": git_blob_sha(trace),
            },
            "terminal_credit_delta": 0,
        }
        return proof, abstract, concrete, trace

    def verify(self, proof, root):
        return verify_finite_refinement(proof, repo_root=root)

    def test_unknown_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, *_ = self.fixture(root)
            proof["schema"] = "UNKNOWN"
            self.assertEqual(self.verify(proof, root)["reason"], "PROOF_SCHEMA_INVALID")

    def test_concrete_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, concrete, _ = self.fixture(root)
            concrete.write_text("def classify(x):\n    return {}\n", encoding="utf-8")
            self.assertEqual(
                self.verify(proof, root)["reason"],
                "CONCRETE_IMPLEMENTATION_BLOB_DRIFT",
            )

    def test_trace_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            trace.write_text("{}\n", encoding="utf-8")
            self.assertEqual(self.verify(proof, root)["reason"], "EXECUTION_TRACE_BLOB_DRIFT")

    def test_open_domain_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, abstract, _, _ = self.fixture(root)
            obj = json.loads(abstract.read_text()); obj["closed_domain"] = False
            abstract.write_text(json.dumps(obj)+"\n")
            proof["abstract_spec"]["git_blob_sha"] = git_blob_sha(abstract)
            self.assertEqual(self.verify(proof, root)["reason"], "ABSTRACT_DOMAIN_NOT_CLOSED")

    def test_missing_trace_case_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["rows"].pop()
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertEqual(self.verify(proof, root)["reason"], "TRACE_DOMAIN_MISMATCH")

    def test_extra_trace_case_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["rows"].append({"input": 99, "output": {"class": "ODD"}})
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertEqual(self.verify(proof, root)["reason"], "TRACE_DOMAIN_MISMATCH")

    def test_duplicate_trace_case_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["rows"].append(copy.deepcopy(obj["rows"][0]))
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertTrue(self.verify(proof, root)["reason"].startswith("TRACE_DUPLICATE_INPUT"))

    def test_concrete_binding_inside_trace_must_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["concrete_git_blob_sha"] = "0"*40
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertEqual(
                self.verify(proof, root)["reason"],
                "EXECUTION_TRACE_CONCRETE_BLOB_MISMATCH",
            )

    def test_semantic_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["rows"][0]["output"] = {"class": "ODD"}
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertEqual(self.verify(proof, root)["reason"], "SEMANTIC_REFINEMENT_MISMATCH")

    def test_nonindependent_trace_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, _, _, trace = self.fixture(root)
            obj = json.loads(trace.read_text()); obj["independent_execution"] = False
            trace.write_text(json.dumps(obj)+"\n")
            proof["execution_trace"]["git_blob_sha"] = git_blob_sha(trace)
            self.assertEqual(self.verify(proof, root)["reason"], "INDEPENDENT_EXECUTION_REQUIRED")

    def test_nonzero_terminal_credit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, *_ = self.fixture(root)
            proof["terminal_credit_delta"] = 1
            self.assertEqual(self.verify(proof, root)["reason"], "NONZERO_TERMINAL_CREDIT_FORBIDDEN")

    def test_valid_exhaustive_finite_trace_mints_bounded_refinement_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); proof, *_ = self.fixture(root)
            out = self.verify(proof, root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["schema"], RECEIPT_SCHEMA)
            self.assertTrue(out["refinement_verified"])
            self.assertTrue(out["safety_refinement_verified"])
            self.assertFalse(out["liveness_refinement_verified"])
            self.assertEqual(out["finite_domain_case_count"], 4)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

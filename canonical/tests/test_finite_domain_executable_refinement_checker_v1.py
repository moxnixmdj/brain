from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.finite_domain_executable_refinement_checker_v1 import (
    SCHEMA,
    verify,
)


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


class FiniteDomainExecutableRefinementCheckerTests(unittest.TestCase):
    def fixture(self, *, cases=None, implementation=None):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/governance").mkdir(parents=True)
        (root / "canonical/runtime").mkdir(parents=True)
        if cases is None:
            cases = [
                {"input": "A", "expected_output": {"value": 1}},
                {"input": "B", "expected_output": {"value": 2}},
                {"input": "C", "expected_output": {"value": None}},
            ]
        if implementation is None:
            implementation = (
                'DOMAIN=("A","B","C")\n'
                'def run(value):\n'
                '    if value not in DOMAIN:\n'
                '        raise ValueError("OUT")\n'
                '    if value=="A": return {"value":1}\n'
                '    if value=="B": return {"value":2}\n'
                '    return {"value":None}\n'
            )
        spec = root / "canonical/governance/spec.json"
        impl = root / "canonical/runtime/impl.py"
        spec.write_text(json.dumps({
            "subject_id": "subject",
            "finite_domain_cases": cases,
        }), encoding="utf-8")
        impl.write_text(implementation, encoding="utf-8")
        proof = {
            "schema": SCHEMA,
            "subject_id": "subject",
            "abstract_spec": {
                "path": "canonical/governance/spec.json",
                "git_blob_sha": blob(spec),
            },
            "concrete_implementation": {
                "path": "canonical/runtime/impl.py",
                "git_blob_sha": blob(impl),
            },
            "callable": "run",
            "terminal_credit_delta": 0,
        }
        return td, root, proof, spec, impl

    def test_valid_domain_is_exhaustively_verified(self):
        td, root, proof, _, _ = self.fixture()
        try:
            out = verify(proof, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["refinement_verified"])
            self.assertEqual(out["assurance_level"], "EXHAUSTIVE_FINITE_DOMAIN")
            self.assertEqual(out["domain_case_count"], 3)
            self.assertEqual(out["terminal_credit_delta"], 0)
        finally:
            td.cleanup()

    def test_incomplete_abstract_domain_is_rejected(self):
        cases = [
            {"input": "A", "expected_output": {"value": 1}},
            {"input": "B", "expected_output": {"value": 2}},
        ]
        td, root, proof, _, _ = self.fixture(cases=cases)
        try:
            out = verify(proof, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "DOMAIN_SPEC_MISMATCH")
        finally:
            td.cleanup()

    def test_missing_nonmember_guard_is_rejected(self):
        implementation = (
            'DOMAIN=("A","B","C")\n'
            'def run(value):\n'
            '    if value=="A": return {"value":1}\n'
            '    if value=="B": return {"value":2}\n'
            '    return {"value":None}\n'
        )
        td, root, proof, _, _ = self.fixture(implementation=implementation)
        try:
            out = verify(proof, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "DOMAIN_GUARD_SHAPE_INVALID")
        finally:
            td.cleanup()

    def test_semantic_output_mismatch_is_rejected(self):
        implementation = (
            'DOMAIN=("A","B","C")\n'
            'def run(value):\n'
            '    if value not in DOMAIN:\n'
            '        raise ValueError("OUT")\n'
            '    if value=="A": return {"value":1}\n'
            '    if value=="B": return {"value":999}\n'
            '    return {"value":None}\n'
        )
        td, root, proof, _, _ = self.fixture(implementation=implementation)
        try:
            out = verify(proof, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "SEMANTIC_MISMATCH")
            self.assertEqual(out["index"], 1)
        finally:
            td.cleanup()

    def test_executable_byte_drift_is_rejected(self):
        td, root, proof, _, impl = self.fixture()
        try:
            impl.write_text(impl.read_text() + "\n# drift\n", encoding="utf-8")
            out = verify(proof, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CONCRETE_IMPLEMENTATION_BINDING_INVALID")
        finally:
            td.cleanup()

    def test_duplicate_abstract_input_is_rejected(self):
        cases = [
            {"input": "A", "expected_output": {"value": 1}},
            {"input": "A", "expected_output": {"value": 1}},
        ]
        implementation = (
            'DOMAIN=("A","A")\n'
            'def run(value):\n'
            '    if value not in DOMAIN:\n'
            '        raise ValueError("OUT")\n'
            '    return {"value":1}\n'
        )
        td, root, proof, _, _ = self.fixture(
            cases=cases, implementation=implementation
        )
        try:
            out = verify(proof, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "FINITE_DOMAIN_DUPLICATE")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.proof_dependency_cone_cache import evaluate


def git_blob_sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class ProofDependencyConeCacheTests(unittest.TestCase):
    def manifest(self, path: str, blob: str):
        return {
            "schema": "PROJECT_BRAIN_PROOF_DEPENDENCY_CONE_CACHE_INPUT_V1",
            "proof_id": "TEST_PROOF",
            "independent_receipt": "canonical/verification/TEST.json",
            "dynamic_dependencies_complete": True,
            "opaque_runtime_dependency": False,
            "proof_semantics_changed": False,
            "dependencies": [{"path": path, "blob_sha": blob}],
        }

    def test_unchanged_dependency_reuses_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "canonical/runtime/x.py"
            p = root / rel
            p.parent.mkdir(parents=True)
            data = b"print('x')\n"
            p.write_bytes(data)
            out = evaluate(root, self.manifest(rel, git_blob_sha(data)))
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["proof_reusable"])
            self.assertFalse(out["revalidation_required"])

    def test_changed_dependency_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "canonical/runtime/x.py"
            p = root / rel
            p.parent.mkdir(parents=True)
            old = b"print('old')\n"
            p.write_bytes(b"print('new')\n")
            out = evaluate(root, self.manifest(rel, git_blob_sha(old)))
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["proof_reusable"])
            self.assertTrue(out["revalidation_required"])
            self.assertEqual(out["changed_dependencies"][0]["reason"], "BLOB_CHANGED")

    def test_unrelated_file_change_does_not_matter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "canonical/runtime/x.py"
            p = root / rel
            p.parent.mkdir(parents=True)
            data = b"x=1\n"
            p.write_bytes(data)
            other = root / "canonical/runtime/unrelated.py"
            other.write_text("changed=True\n", encoding="utf-8")
            out = evaluate(root, self.manifest(rel, git_blob_sha(data)))
            self.assertTrue(out["proof_reusable"], out)

    def test_incomplete_dynamic_dependency_accounting_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "x"
            p = root / rel
            data = b"x"
            p.write_bytes(data)
            m = self.manifest(rel, git_blob_sha(data))
            m["dynamic_dependencies_complete"] = False
            out = evaluate(root, m)
            self.assertFalse(out["pass"])
            self.assertFalse(out["proof_reusable"])
            self.assertIn("DYNAMIC_DEPENDENCY_COMPLETENESS_NOT_PROVEN", out["errors"])

    def test_semantic_change_always_invalidates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "x"
            p = root / rel
            data = b"x"
            p.write_bytes(data)
            m = self.manifest(rel, git_blob_sha(data))
            m["proof_semantics_changed"] = True
            out = evaluate(root, m)
            self.assertFalse(out["pass"])
            self.assertFalse(out["proof_reusable"])
            self.assertIn("PROOF_SEMANTICS_CHANGED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

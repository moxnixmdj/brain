import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.effect_broker_receipt_resolver_v1 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
    verify_receipt_pair_bytes,
)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\\0".encode("ascii") + data).hexdigest()


class ReceiptResolverTests(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj: dict):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(obj, sort_keys=True) + "\n").encode()
        p.write_bytes(data)
        return {"path": rel, "git_blob_sha": git_blob_sha1(data)}

    def test_exact_bytes_resolve(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = self._write(root, "canonical/verification/r.json", {"schema": "X", "ok": True})
            out = resolve_receipt_bytes(ref, repo_root=root)
            self.assertEqual(out["git_blob_sha"], ref["git_blob_sha"])
            self.assertEqual(out["schema"], "X")

    def test_nonexistent_forged_reference_fails(self):
        with tempfile.TemporaryDirectory() as td:
            ref = {"path": "does/not/exist.json", "git_blob_sha": "a" * 40}
            with self.assertRaisesRegex(ReceiptResolutionError, "RECEIPT_PATH_NOT_FOUND"):
                resolve_receipt_bytes(ref, repo_root=td)

    def test_blob_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = self._write(root, "canonical/verification/r.json", {"schema": "X"})
            ref["git_blob_sha"] = "b" * 40
            with self.assertRaisesRegex(ReceiptResolutionError, "RECEIPT_GIT_BLOB_MISMATCH"):
                resolve_receipt_bytes(ref, repo_root=root)

    def test_traversal_fails(self):
        with tempfile.TemporaryDirectory() as td:
            ref = {"path": "../outside.json", "git_blob_sha": "a" * 40}
            with self.assertRaisesRegex(ReceiptResolutionError, "RECEIPT_PATH_NOT_CANONICAL_RELATIVE"):
                resolve_receipt_bytes(ref, repo_root=td)

    def test_pair_requires_both_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = self._write(root, "canonical/verification/a.json", {"schema": "A"})
            c = self._write(root, "canonical/verification/c.json", {"schema": "C"})
            out = verify_receipt_pair_bytes({"authority_receipt": a, "composition_receipt": c}, repo_root=root)
            self.assertEqual(out["status"], "RECEIPT_BYTES_VERIFIED")
            self.assertTrue(out["semantic_verification_still_required"])


if __name__ == "__main__":
    unittest.main()

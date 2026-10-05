import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    git_blob_id,
    resolve_receipt_bytes,
    verify_receipt_pair_bytes,
)


class ReceiptResolverV2Tests(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj: dict):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(obj, sort_keys=True) + "\n").encode()
        p.write_bytes(data)
        return p, data, {"path": rel, "git_blob_sha": git_blob_id(data, object_format="sha1")}

    def test_git_blob_id_matches_independent_git_fixture(self):
        data = b'{"ok": true, "schema": "X"}\n'
        self.assertEqual(
            git_blob_id(data, object_format="sha1"),
            "618d53676c563ee5b0d2fb312e2e512103e4e4e0",
        )

    def test_exact_bytes_resolve(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, _, ref = self._write(root, "canonical/verification/r.json", {"schema": "X", "ok": True})
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
            _, _, ref = self._write(root, "canonical/verification/r.json", {"schema": "X"})
            ref["git_blob_sha"] = "b" * 40
            with self.assertRaisesRegex(ReceiptResolutionError, "RECEIPT_GIT_BLOB_MISMATCH"):
                resolve_receipt_bytes(ref, repo_root=root)

    def test_traversal_and_backslash_fail(self):
        with tempfile.TemporaryDirectory() as td:
            for path in ("../outside.json", "canonical\\verification\\r.json"):
                ref = {"path": path, "git_blob_sha": "a" * 40}
                with self.assertRaises(ReceiptResolutionError):
                    resolve_receipt_bytes(ref, repo_root=td)

    def test_pair_requires_both_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, _, a = self._write(root, "canonical/verification/a.json", {"schema": "A"})
            _, _, c = self._write(root, "canonical/verification/c.json", {"schema": "C"})
            out = verify_receipt_pair_bytes({"authority_receipt": a, "composition_receipt": c}, repo_root=root)
            self.assertEqual(out["status"], "RECEIPT_BYTES_VERIFIED")
            self.assertTrue(out["semantic_verification_still_required"])


if __name__ == "__main__":
    unittest.main()

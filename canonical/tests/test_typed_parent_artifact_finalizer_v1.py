import hashlib
import io
import json
import pathlib
import struct
import tempfile
import unittest

from canonical.runtime.typed_parent_artifact_finalizer_v1 import (
    Declaration,
    FinalizerError,
    FRAME_SCHEMA,
    finalize_one,
)

def frame(artifact_id, payload, media="application/octet-stream", effect="e" * 64, extra=None):
    header = {
        "schema": FRAME_SCHEMA,
        "artifact_id": artifact_id,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "media_type": media,
        "effect_request_sha256": effect,
    }
    if extra:
        header.update(extra)
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    return struct.pack(">I", len(raw)) + raw + payload

def auth(effect="e" * 64):
    return {
        "allowed": True,
        "status": "ALLOW_FINAL_AUTHORIZATION",
        "canonical_request_sha256": effect,
        "authorization_sha256": "a" * 64,
    }

class TypedParentFinalizerTests(unittest.TestCase):
    def test_commit(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out.bin")
            decl = Declaration("a", dest, 100, "application/octet-stream")
            out = finalize_one(io.BytesIO(frame("a", b"hello")), {"a": decl}, auth())
            self.assertEqual(pathlib.Path(dest).read_bytes(), b"hello")
            self.assertEqual(out["status"], "COMMITTED_TYPED_ARTIFACT")

    def test_child_cannot_choose_destination(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out")
            decl = Declaration("a", dest, 100, "application/octet-stream")
            with self.assertRaisesRegex(FinalizerError, "HEADER_FIELD_SET_INVALID"):
                finalize_one(
                    io.BytesIO(frame("a", b"x", extra={"destination": "/tmp/evil"})),
                    {"a": decl},
                    auth(),
                )

    def test_bad_authorization_denies_without_file(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out")
            decl = Declaration("a", dest, 100, "application/octet-stream")
            with self.assertRaisesRegex(FinalizerError, "FINAL_AUTHORIZATION_INVALID"):
                finalize_one(io.BytesIO(frame("a", b"x")), {"a": decl}, {})
            self.assertFalse(pathlib.Path(dest).exists())

    def test_hash_mismatch_denies(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out")
            decl = Declaration("a", dest, 100, "application/octet-stream")
            data = bytearray(frame("a", b"x"))
            data[-1] ^= 1
            with self.assertRaisesRegex(FinalizerError, "PAYLOAD_SHA256_MISMATCH"):
                finalize_one(io.BytesIO(bytes(data)), {"a": decl}, auth())
            self.assertFalse(pathlib.Path(dest).exists())

    def test_oversize_denies(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out")
            decl = Declaration("a", dest, 1, "application/octet-stream")
            with self.assertRaisesRegex(FinalizerError, "SIZE_INVALID"):
                finalize_one(io.BytesIO(frame("a", b"xx")), {"a": decl}, auth())

    def test_trailing_bytes_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = str(pathlib.Path(td) / "out")
            decl = Declaration("a", dest, 100, "application/octet-stream")
            with self.assertRaisesRegex(FinalizerError, "TRAILING_BYTES_FORBIDDEN"):
                finalize_one(io.BytesIO(frame("a", b"x") + b"z"), {"a": decl}, auth())
            self.assertFalse(pathlib.Path(dest).exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)

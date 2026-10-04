from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.release_chunk_archive_v1 import (
    MAX_GITHUB_RELEASE_ASSET_BYTES,
    ReleaseChunkArchiveError,
    planned_chunk_count,
    reconstruct,
    split_file,
)


class ReleaseChunkArchiveTests(unittest.TestCase):
    def test_split_and_reconstruct_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "model.gguf"
            raw = b"abcdef1234567890" * 200_000 + b"tail"
            source.write_bytes(raw)
            chunks = root / "chunks"
            manifest = split_file(source, chunks, chunk_bytes=1_000_000)
            self.assertEqual(manifest["chunk_count"], 4)
            self.assertEqual(
                manifest["whole_sha256"], hashlib.sha256(raw).hexdigest()
            )
            rebuilt = root / "rebuilt.gguf"
            result = reconstruct(
                chunks / "model.gguf.manifest.json", chunks, rebuilt
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(rebuilt.read_bytes(), raw)

    def test_tamper_fails_closed_and_no_partial_survives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "state.bin"
            source.write_bytes(b"A" * 2_500_001)
            chunks = root / "chunks"
            manifest = split_file(source, chunks, chunk_bytes=1_000_000)
            target = chunks / manifest["chunks"][1]["name"]
            damaged = bytearray(target.read_bytes())
            damaged[0] ^= 1
            target.write_bytes(damaged)
            output = root / "rebuilt.bin"
            with self.assertRaisesRegex(
                ReleaseChunkArchiveError, "CHUNK_SHA256_MISMATCH"
            ):
                reconstruct(chunks / "state.bin.manifest.json", chunks, output)
            self.assertFalse(output.exists())
            self.assertFalse((root / "rebuilt.bin.partial").exists())

    def test_path_traversal_chunk_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "state.bin"
            source.write_bytes(b"x" * 1024)
            chunks = root / "chunks"
            split_file(source, chunks, chunk_bytes=512)
            manifest_path = chunks / "state.bin.manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["chunks"][0]["name"] = "../escape"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseChunkArchiveError, "CHUNK_NAME_INVALID"):
                reconstruct(manifest_path, chunks, root / "rebuilt.bin")

    def test_asset_limit_is_strictly_respected(self):
        with self.assertRaisesRegex(ReleaseChunkArchiveError, "CHUNK_BYTES_OUT_OF_RANGE"):
            planned_chunk_count(100, MAX_GITHUB_RELEASE_ASSET_BYTES + 1)
        self.assertEqual(planned_chunk_count(55_563_006_776), 30)

    def test_empty_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "empty.bin"
            source.write_bytes(b"")
            with self.assertRaisesRegex(ReleaseChunkArchiveError, "SOURCE_FILE_EMPTY"):
                split_file(source, root / "chunks", chunk_bytes=100)


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations
import pathlib
import tempfile
import unittest

from canonical.runtime.declared_artifact_extractor_v1 import (
    ArtifactExtractionError,
    DeclaredArtifact,
    extract_declared_artifacts,
)

class DeclaredArtifactExtractorTests(unittest.TestCase):
    def test_only_declared_file_is_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"wanted.bin").write_bytes(b"abc")
            (root/"secret.tmp").write_bytes(b"must-not-export")
            out=extract_declared_artifacts(
                root,
                {"a":DeclaredArtifact("a","wanted.bin","application/octet-stream",10)},
            )
            self.assertEqual(out["artifact_count"],1)
            self.assertEqual(out["artifacts"][0]["relative_path"],"wanted.bin")
            self.assertEqual(
                out["filesystem_policy"],
                "ALL_NONDECLARED_PRIVATE_OVERLAY_CHANGES_DISCARDED",
            )

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ArtifactExtractionError):
                extract_declared_artifacts(
                    td,
                    {"a":DeclaredArtifact("a","../escape","text/plain",10)},
                )

    def test_missing_declared_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                ArtifactExtractionError,
                "DECLARED_ARTIFACT_NOT_REGULAR_FILE",
            ):
                extract_declared_artifacts(
                    td,
                    {"a":DeclaredArtifact("a","missing","text/plain",10)},
                )

    def test_oversize_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"x").write_bytes(b"xx")
            with self.assertRaisesRegex(
                ArtifactExtractionError,
                "DECLARED_ARTIFACT_SIZE_INVALID",
            ):
                extract_declared_artifacts(
                    root,
                    {"a":DeclaredArtifact("a","x","application/octet-stream",1)},
                )


if __name__=="__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime.quiescent_declared_artifact_extractor_v2 import (
    ArtifactExtractionError,
    DeclaredArtifact,
    extract_declared_artifacts,
)


class QuiescentArtifactExtractorTests(unittest.TestCase):
    def test_only_declared_regular_file_is_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "wanted.bin").write_bytes(b"abc")
            (root / "secret.tmp").write_bytes(b"discard-me")
            out = extract_declared_artifacts(
                root,
                {
                    "a": DeclaredArtifact(
                        "a", "wanted.bin", "application/octet-stream", 10
                    )
                },
            )
            self.assertEqual(out["artifact_count"], 1)
            self.assertEqual(out["artifacts"][0]["relative_path"], "wanted.bin")
            self.assertEqual(
                out["filesystem_policy"],
                "ALL_UNDECLARED_OVERLAY_STATE_DISCARDED",
            )
            self.assertFalse(out["durable_commit_authority_created"])

    def test_final_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "target").write_bytes(b"x")
            (root / "alias").symlink_to("target")
            with self.assertRaisesRegex(
                ArtifactExtractionError, "ARTIFACT_SYMLINK_REJECTED"
            ):
                extract_declared_artifacts(
                    root,
                    {"a": DeclaredArtifact("a", "alias", "text/plain", 10)},
                )

    def test_parent_symlink_rejected_even_when_target_inside_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            real = root / "real"
            real.mkdir()
            (real / "x").write_bytes(b"x")
            (root / "alias").symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(
                ArtifactExtractionError, "ARTIFACT_SYMLINK_REJECTED"
            ):
                extract_declared_artifacts(
                    root,
                    {"a": DeclaredArtifact("a", "alias/x", "text/plain", 10)},
                )

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                ArtifactExtractionError, "ARTIFACT_PATH_INVALID"
            ):
                extract_declared_artifacts(
                    td,
                    {"a": DeclaredArtifact("a", "../escape", "text/plain", 10)},
                )

    def test_directory_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "dir").mkdir()
            with self.assertRaisesRegex(
                ArtifactExtractionError,
                "DECLARED_ARTIFACT_NOT_REGULAR_FILE",
            ):
                extract_declared_artifacts(
                    root,
                    {"a": DeclaredArtifact("a", "dir", "text/plain", 10)},
                )

    def test_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "x").write_bytes(b"xx")
            with self.assertRaisesRegex(
                ArtifactExtractionError,
                "DECLARED_ARTIFACT_SIZE_INVALID",
            ):
                extract_declared_artifacts(
                    root,
                    {
                        "a": DeclaredArtifact(
                            "a", "x", "application/octet-stream", 1
                        )
                    },
                )

    def test_duplicate_declared_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "x").write_bytes(b"x")
            with self.assertRaisesRegex(
                ArtifactExtractionError, "DUPLICATE_ARTIFACT_PATH"
            ):
                extract_declared_artifacts(
                    root,
                    {
                        "a": DeclaredArtifact("a", "x", "text/plain", 10),
                        "b": DeclaredArtifact("b", "x", "text/plain", 10),
                    },
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

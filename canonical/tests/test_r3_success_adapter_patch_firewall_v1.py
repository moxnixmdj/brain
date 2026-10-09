from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_success_adapter_patch_firewall_v1 as fw


def _write(root: Path, relative: str, text: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()


def _single_patch(path: str, old: str = "old", new: str = "new") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


class R3SuccessAdapterPatchFirewallV1Tests(unittest.TestCase):
    def test_exact_bound_adapter_patch_is_candidate_only(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            path = fw.MUTABLE_ADAPTER_PATHS[0]
            base = _write(root, path, "old\n")
            out = fw.evaluate(
                {
                    "patch_text": _single_patch(path),
                    "base_sha256_by_path": {path: base},
                },
                repo_root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["touched_paths"], [path])
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["patch_application_authority"])
        self.assertFalse(out["source_write_authority"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_stale_base_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            path = fw.MUTABLE_ADAPTER_PATHS[0]
            _write(root, path, "old\n")
            out = fw.evaluate(
                {
                    "patch_text": _single_patch(path),
                    "base_sha256_by_path": {path: "0" * 64},
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertIn("BASE_SOURCE_DRIFT", out["reason"])

    def test_verification_authority_file_is_not_admitted(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            path = fw.IMMUTABLE_AUTHORITY_PATHS[0]
            base = _write(root, path, "old\n")
            out = fw.evaluate(
                {
                    "patch_text": _single_patch(path),
                    "base_sha256_by_path": {path: base},
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertIn("PATCH_PATH_NOT_ADMITTED", out["reason"])

    def test_rename_new_delete_and_binary_metadata_fail_closed(self):
        cases = [
            "rename from canonical/runtime/r3_bound_success_adapter_v1.py\n",
            "new file mode 100644\n",
            "deleted file mode 100644\n",
            "GIT binary patch\n",
        ]
        with TemporaryDirectory() as td:
            root = Path(td)
            path = fw.MUTABLE_ADAPTER_PATHS[0]
            base = _write(root, path, "old\n")
            for metadata in cases:
                patch = (
                    f"diff --git a/{path} b/{path}\n"
                    + metadata
                    + f"--- a/{path}\n"
                    + f"+++ b/{path}\n"
                    + "@@ -1 +1 @@\n-old\n+new\n"
                )
                out = fw.evaluate(
                    {
                        "patch_text": patch,
                        "base_sha256_by_path": {path: base},
                    },
                    repo_root=root,
                )
                self.assertFalse(out["pass"], (metadata, out))
                self.assertIn("FORBIDDEN_PATCH_METADATA", out["reason"])

    def test_path_traversal_and_cross_file_header_mismatch_fail_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            path = fw.MUTABLE_ADAPTER_PATHS[0]
            base = _write(root, path, "old\n")
            traversal = _single_patch("../" + path)
            out = fw.evaluate(
                {
                    "patch_text": traversal,
                    "base_sha256_by_path": {path: base},
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])

            mismatch = (
                f"diff --git a/{path} b/{path}\n"
                f"--- a/{path}\n"
                f"+++ b/{fw.MUTABLE_ADAPTER_PATHS[1]}\n"
                "@@ -1 +1 @@\n-old\n+new\n"
            )
            out = fw.evaluate(
                {
                    "patch_text": mismatch,
                    "base_sha256_by_path": {path: base},
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertIn("NEW_HEADER_PATH_MISMATCH", out["reason"])

    def test_two_allowed_adapter_files_can_be_bound_in_one_candidate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            p1, p2 = fw.MUTABLE_ADAPTER_PATHS
            b1 = _write(root, p1, "old1\n")
            b2 = _write(root, p2, "old2\n")
            patch = _single_patch(p1, "old1", "new1") + _single_patch(
                p2, "old2", "new2"
            )
            out = fw.evaluate(
                {
                    "patch_text": patch,
                    "base_sha256_by_path": {p1: b1, p2: b2},
                },
                repo_root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["touched_paths"], [p1, p2])
        self.assertEqual(out["hunk_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

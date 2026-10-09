from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_root1_adapter_gap_witness_v1 as gap_witness
from canonical.runtime import r3_success_adapter_patch_author_wrapper_v1 as wrapper
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(root: Path) -> None:
    _write(root, firewall.MUTABLE_ADAPTER_PATHS[0], "old bound\n")
    _write(root, firewall.MUTABLE_ADAPTER_PATHS[1], "old raw\n")
    for path in gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS:
        target = root / path
        if not target.exists():
            _write(root, path, "frontier auxiliary\n")
    for path in gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS:
        _write(root, path, "IMMUTABLE_VERIFIER_SECRET_MARKER\n")


def _gap(root: Path) -> dict:
    adapter_sha = gap_witness._frontier_sha256(
        gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS,
        repo_root=root,
    )
    authority_sha = gap_witness._frontier_sha256(
        gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS,
        repo_root=root,
    )
    return {
        "schema": gap_witness.SCHEMA,
        "status": (
            "PASS__ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP_ESTABLISHED__"
            "NO_CURRENT_BOUND_ACQUISITION_ROUTE"
        ),
        "pass": True,
        "root1_positive_gap_established": True,
        "required_primitive": gap_witness.REQUIRED_PRIMITIVE,
        "witness_id": "r3-root1-adapter-gap:test",
        "witness": {
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
        },
        "gap_evidence": {
            "required_behavior": (
                "Author one candidate success-adapter patch while preserving "
                "independent verification authority."
            )
        },
        "adapter_frontier_sha256": adapter_sha,
        "verification_authority_sha256": authority_sha,
    }


def _patch(path: str, old: str, new: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


class R3SuccessAdapterPatchAuthorWrapperV1Tests(unittest.TestCase):
    def test_packet_exposes_only_mutable_adapter_source(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            out = wrapper.build_author_packet(_gap(root), repo_root=root)
        self.assertTrue(out["pass"], out)
        packet = out["author_packet"]
        self.assertEqual(
            [row["path"] for row in packet["mutable_sources"]],
            list(firewall.MUTABLE_ADAPTER_PATHS),
        )
        rendered = repr(packet)
        self.assertIn("old bound", rendered)
        self.assertIn("old raw", rendered)
        self.assertNotIn("IMMUTABLE_VERIFIER_SECRET_MARKER", rendered)
        self.assertEqual(
            packet["immutable_verification_paths"],
            list(gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS),
        )
        self.assertFalse(packet["patch_application_authority"])
        self.assertFalse(packet["source_write_authority"])
        self.assertFalse(packet["verification_authority"])

    def test_stale_adapter_frontier_fails_before_authoring(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            gap = _gap(root)
            gap["adapter_frontier_sha256"] = "0" * 64
            out = wrapper.build_author_packet(gap, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "COMPILED_GAP_ADAPTER_FRONTIER_STALE")

    def test_stale_verification_authority_fails_before_authoring(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            gap = _gap(root)
            gap["verification_authority_sha256"] = "0" * 64
            out = wrapper.build_author_packet(gap, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "COMPILED_GAP_VERIFICATION_AUTHORITY_STALE",
        )

    def test_single_mutable_file_patch_is_firewall_validated_candidate_only(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            path = firewall.MUTABLE_ADAPTER_PATHS[0]
            out = wrapper.validate_author_output(
                packet,
                {"patch_text": _patch(path, "old bound", "new bound")},
                repo_root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["touched_paths"], [path])
        self.assertEqual(set(out["base_sha256_by_path"]), {path})
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["patch_application_authority"])
        self.assertFalse(out["source_write_authority"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_verifier_path_patch_is_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            verifier = gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS[0]
            out = wrapper.validate_author_output(
                packet,
                {
                    "patch_text": _patch(
                        verifier,
                        "IMMUTABLE_VERIFIER_SECRET_MARKER",
                        "mutated verifier",
                    )
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertIn("PATCH_PATH_NOT_ADMITTED", out["reason"])

    def test_provider_receives_bounded_packet_and_candidate_is_not_applied(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            path = firewall.MUTABLE_ADAPTER_PATHS[1]
            before = (root / path).read_text(encoding="utf-8")
            seen = {}

            def author(packet):
                seen.update(packet)
                return {"patch_text": _patch(path, "old raw", "new raw")}

            out = wrapper.request_candidate(
                _gap(root),
                repo_root=root,
                author_provider=author,
                author_provider_id="TEST_CANDIDATE_AUTHOR",
            )
            after = (root / path).read_text(encoding="utf-8")

        self.assertTrue(out["pass"], out)
        self.assertEqual(out["author_provider_id"], "TEST_CANDIDATE_AUTHOR")
        self.assertEqual(before, after)
        self.assertEqual(seen["schema"], wrapper.AUTHOR_PACKET_SCHEMA)
        self.assertFalse(seen["source_write_authority"])
        self.assertNotIn("IMMUTABLE_VERIFIER_SECRET_MARKER", repr(seen))


if __name__ == "__main__":
    unittest.main(verbosity=2)

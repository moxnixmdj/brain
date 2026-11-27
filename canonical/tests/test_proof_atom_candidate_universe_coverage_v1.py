from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_candidate_universe_coverage_v1 import (
    MAX_FILE_BYTES,
    audit_coverage,
)


def init_roots(root: Path) -> None:
    for rel in (
        "canonical/verification",
        "canonical/capabilities",
        "canonical/governance",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)


class Tests(unittest.TestCase):
    def test_clean_supported_text_universe_is_exhaustive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_roots(root)
            (root / "canonical/verification/r.json").write_text(
                '{"claim":"R1"}\n', encoding="utf-8"
            )
            out = audit_coverage(root=root)
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertTrue(out["candidate_selection_parity"])
            self.assertTrue(
                out["negative_literal_exhaustive_within_configured_candidate_set"]
            )
            self.assertTrue(
                out["negative_literal_exhaustive_over_supported_text_in_search_roots"]
            )
            self.assertTrue(
                out["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"]
            )

    def test_oversize_supported_text_blocks_supported_text_exhaustiveness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_roots(root)
            p = root / "canonical/verification/large.json"
            p.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            out = audit_coverage(root=root)
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertEqual(out["oversized_supported_text_count"], 1)
            self.assertTrue(
                out["negative_literal_exhaustive_within_configured_candidate_set"]
            )
            self.assertFalse(
                out["negative_literal_exhaustive_over_supported_text_in_search_roots"]
            )
            self.assertFalse(
                out["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"]
            )

    def test_unsupported_suffix_is_visible_and_blocks_full_root_exhaustiveness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_roots(root)
            (root / "canonical/verification/r.json").write_text(
                '{"claim":"R1"}\n', encoding="utf-8"
            )
            (root / "canonical/verification/raw.bin").write_bytes(b"R1")
            out = audit_coverage(root=root)
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertEqual(out["unsupported_suffix_count"], 1)
            self.assertTrue(
                out["negative_literal_exhaustive_over_supported_text_in_search_roots"]
            )
            self.assertFalse(
                out["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"]
            )

    def test_non_utf8_supported_text_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_roots(root)
            (root / "canonical/verification/r.json").write_bytes(b"\xff\xfe\x00")
            out = audit_coverage(root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertEqual(out["scan_gap_count"], 1)
            self.assertFalse(
                out["negative_literal_exhaustive_within_configured_candidate_set"]
            )

    def test_explicit_self_reflection_exclusion_does_not_count_as_unseen_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_roots(root)
            (root / "canonical/governance/DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_V1_PART_9.json").write_text(
                '{"lexical_projection":"R1"}\n', encoding="utf-8"
            )
            out = audit_coverage(root=root)
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertEqual(out["explicit_provenance_exclusion_count"], 1)
            self.assertEqual(out["unsupported_suffix_count"], 0)
            self.assertTrue(
                out["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

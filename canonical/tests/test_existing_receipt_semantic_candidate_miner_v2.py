from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.existing_receipt_semantic_candidate_miner_v2 as m


def seed(root: Path, *, witness_path: str = "canonical/verification/witness.json"):
    (root / "canonical/verification").mkdir(parents=True)
    (root / "canonical/capabilities").mkdir(parents=True)
    (root / "canonical/governance").mkdir(parents=True)
    (root / "canonical/runtime").mkdir(parents=True)
    (root / "canonical/tests").mkdir(parents=True)
    (root / "canonical/reasoning").mkdir(parents=True)

    target = {
        "targets": [{
            "predicate_id": "T1",
            "atom_sources": [{"atom": "A1", "sources": [{"literal": "R1"}]}],
            "metric_requirement_sources": [],
        }]
    }
    witness = {
        "witnesses": [{
            "witness_id": "W1",
            "source_path": witness_path,
        }]
    }
    target_path = root / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
    witness_doc_path = root / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
    target_path.write_text(json.dumps(target), encoding="utf-8")
    witness_doc_path.write_text(json.dumps(witness), encoding="utf-8")
    return target_path, witness_doc_path


def run_miner(root: Path):
    old = (m.ROOT, m.TARGET, m.WITNESSES)
    m.ROOT = root
    m.TARGET = root / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
    m.WITNESSES = root / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main()
        return rc, json.loads(buf.getvalue())
    finally:
        m.ROOT, m.TARGET, m.WITNESSES = old


class Tests(unittest.TestCase):
    def test_self_reflection_implementation_tests_and_superstrings_are_not_global_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed(root)
            good = root / "canonical/verification/witness.json"
            good.write_text('{"claim":"R1"}\n', encoding="utf-8")
            (root / "canonical/verification/super.json").write_text('{"claim":"R1_EXTENDED"}\n', encoding="utf-8")
            (root / "canonical/runtime/implementation.py").write_text("R1\n", encoding="utf-8")
            (root / "canonical/tests/test_echo.py").write_text("R1\n", encoding="utf-8")
            (root / "canonical/reasoning/EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINING_20261002_V1.json").write_text(
                '{"echo":"R1"}\n', encoding="utf-8"
            )

            rc, out = run_miner(root)
            self.assertEqual(rc, 0)
            paths = [x["path"] for x in out["global_reuse_candidates"]]
            self.assertEqual(paths, ["canonical/verification/witness.json"])
            self.assertEqual(
                out["global_reuse_candidates"][0]["git_blob_sha"],
                m.git_blob_sha(good),
            )

    def test_manifest_is_content_sensitive_and_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed(root)
            p = root / "canonical/verification/witness.json"
            p.write_text('{"claim":"R1"}\n', encoding="utf-8")
            _, a = run_miner(root)
            _, b = run_miner(root)
            self.assertEqual(a["scanned_corpus_manifest_sha256"], b["scanned_corpus_manifest_sha256"])
            p.write_text('{"claim":"R1","extra":1}\n', encoding="utf-8")
            _, c = run_miner(root)
            self.assertNotEqual(a["scanned_corpus_manifest_sha256"], c["scanned_corpus_manifest_sha256"])

    def test_match_cap_reports_truncation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed(root)
            for i in range(m.MAX_MATCHES_PER_LITERAL + 3):
                (root / f"canonical/verification/r{i:02d}.json").write_text(
                    '{"claim":"R1"}\n', encoding="utf-8"
                )
            (root / "canonical/verification/witness.json").write_text('{"claim":"R1"}\n', encoding="utf-8")
            _, out = run_miner(root)
            self.assertGreater(out["global_actual_reuse_candidate_count"], m.MAX_MATCHES_PER_LITERAL)
            self.assertEqual(out["global_stored_reuse_candidate_count"], m.MAX_MATCHES_PER_LITERAL)
            self.assertEqual(out["truncated_literal_search_count"], 1)

    def test_witness_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed(root, witness_path="../../outside.json")
            (root / "canonical/verification/witness.json").write_text('{"claim":"R1"}\n', encoding="utf-8")
            _, out = run_miner(root)
            self.assertEqual(out["exact_catalog_edge_candidate_count"], 0)

    def test_no_credit_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed(root)
            (root / "canonical/verification/witness.json").write_text(
                '{"claim":"R1","note":"clean-room"}\n', encoding="utf-8"
            )
            _, out = run_miner(root)
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["family_credit_delta"], 0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])
            self.assertEqual(out["contamination_pointer_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

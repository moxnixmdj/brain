from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.typed_witness_target_literal_crosswalk_v1 import build_crosswalk


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class TypedWitnessTargetLiteralCrosswalkV1Tests(unittest.TestCase):
    def test_exact_target_literal_hit_is_candidate_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/w.json"
            p.parent.mkdir(parents=True)
            data = b'{"claim":"terminal_task_success"}\n'
            p.write_bytes(data)
            target_doc = {
                "targets": [{
                    "predicate_id": "T",
                    "atom_sources": [{
                        "atom": "metric:terminal_task_success",
                        "sources": [{"document": "protocol", "literal": "terminal_task_success"}],
                    }],
                    "metric_requirement_sources": [],
                }]
            }
            witness_doc = {
                "witnesses": [{
                    "witness_id": "W",
                    "independent_or_objective": True,
                    "source_path": "canonical/verification/w.json",
                    "source_sha": blob_sha(data),
                    "supporting_sources": [],
                }]
            }
            out = build_crosswalk(target_doc, witness_doc, root=root)
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertEqual(out["pair_count"], 1)
            self.assertEqual(out["pairs_with_literal_hits"], 1)
            row = out["pairs"][0]
            self.assertEqual(row["exact_target_literal_hit_count"], 1)
            self.assertTrue(row["candidate_only"])
            self.assertFalse(row["semantic_binding_verified"])
            self.assertFalse(row["scope_relation_verified"])

    def test_nonmatching_text_does_not_create_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/w.json"
            p.parent.mkdir(parents=True)
            data = b'{"claim":"terminal_task"}\n'
            p.write_bytes(data)
            target_doc = {
                "targets": [{
                    "predicate_id": "T",
                    "atom_sources": [{
                        "atom": "metric:terminal_task_success",
                        "sources": [{"document": "protocol", "literal": "terminal_task_success"}],
                    }],
                    "metric_requirement_sources": [],
                }]
            }
            witness_doc = {
                "witnesses": [{
                    "witness_id": "W",
                    "independent_or_objective": True,
                    "source_path": "canonical/verification/w.json",
                    "source_sha": blob_sha(data),
                    "supporting_sources": [],
                }]
            }
            out = build_crosswalk(target_doc, witness_doc, root=root)
            self.assertEqual(out["pairs_with_literal_hits"], 0)
            self.assertEqual(out["pairs"][0]["exact_target_literal_hit_count"], 0)

    def test_blob_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/w.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"claim":"x"}\n', encoding="utf-8")
            target_doc = {
                "targets": [{
                    "predicate_id": "T",
                    "atom_sources": [{
                        "atom": "dimension:x",
                        "sources": [{"document": "protocol", "literal": "x"}],
                    }],
                    "metric_requirement_sources": [],
                }]
            }
            witness_doc = {
                "witnesses": [{
                    "witness_id": "W",
                    "independent_or_objective": True,
                    "source_path": "canonical/verification/w.json",
                    "source_sha": "deadbeef",
                    "supporting_sources": [],
                }]
            }
            out = build_crosswalk(target_doc, witness_doc, root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertTrue(any("WITNESS_SOURCE_BLOB_MISMATCH" in e for e in out["errors"]))

    def test_supporting_source_is_content_addressed_and_searchable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "canonical/verification/w.json"
            p2 = root / "canonical/runtime/support.py"
            p1.parent.mkdir(parents=True)
            p2.parent.mkdir(parents=True)
            d1 = b'{"claim":"other"}\n'
            d2 = b'# scope boundary\n'
            p1.write_bytes(d1)
            p2.write_bytes(d2)
            target_doc = {
                "targets": [{
                    "predicate_id": "T",
                    "atom_sources": [{
                        "atom": "dimension:scope",
                        "sources": [{"document": "protocol", "literal": "scope boundary"}],
                    }],
                    "metric_requirement_sources": [],
                }]
            }
            witness_doc = {
                "witnesses": [{
                    "witness_id": "W",
                    "independent_or_objective": True,
                    "source_path": "canonical/verification/w.json",
                    "source_sha": blob_sha(d1),
                    "supporting_sources": [{
                        "path": "canonical/runtime/support.py",
                        "sha": blob_sha(d2),
                    }],
                }]
            }
            out = build_crosswalk(target_doc, witness_doc, root=root)
            row = out["pairs"][0]
            self.assertEqual(row["exact_target_literal_hit_count"], 1)
            self.assertEqual(row["candidate_hits"][0]["source_role"], "SUPPORTING")

    def test_live_surface_remains_11_by_9_and_zero_credit(self):
        root = Path(__file__).resolve().parents[2]
        targets = json.loads(
            (root / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json").read_text()
        )
        witnesses = json.loads(
            (root / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json").read_text()
        )
        out = build_crosswalk(targets, witnesses, root=root)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["target_count"], 11)
        self.assertEqual(out["witness_count"], 9)
        self.assertEqual(out["pair_count"], 99)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

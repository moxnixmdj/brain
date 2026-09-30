#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"

def load():
    spec = importlib.util.spec_from_file_location("objective_evidence_generic_route", P)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class GenericBM25RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_generic_bm25_relevance_route_requires_no_authority_identity(self):
        objective = "Assess sqlite write ahead logging checkpoint behavior"
        candidate = {
            "url": "https://example.org/sqlite-wal",
            "title": "SQLite WAL checkpoint behavior",
            "snippet": "Write ahead logging and checkpoint modes",
        }
        provenance = {
            "status": "RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url": candidate["url"],
            "final_url": candidate["url"],
            "final_host": "example.org",
        }
        relevance = {
            "schema": "PROJECT_BRAIN_OBJECTIVE_RELEVANCE_BM25_V1",
            "objective": objective,
            "status": "LEXICAL_RELEVANCE_RANKED",
            "verification_method": "DETERMINISTIC_BM25",
            "output_verified": True,
            "top_candidate_original_index": 0,
            "ranked_candidates": [{
                "original_index": 0,
                "candidate": candidate,
                "lexical_relevance_score": 2.1,
                "matched_terms": ["sqlite", "checkpoint", "logging"],
                "term_contributions": {},
            }],
        }
        out = self.m.extract(
            objective,
            candidate,
            provenance,
            relevance,
            fetch=lambda url, timeout: (
                b"<html><body><h1>SQLite write ahead logging</h1>"
                b"<p>SQLite WAL checkpoint behavior controls when write ahead log frames are copied back to the database file.</p>"
                b"</body></html>",
                candidate["url"],
                "text/html",
                200,
            ),
        )
        self.assertEqual(out["status"], "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED", out)
        self.assertGreater(out["evidence_unit_count"], 0, out)
        self.assertNotIn("authority_identity", out)
        self.assertEqual(out["factual_correctness_status"], "UNVERIFIED", out)

    def test_bm25_receipt_must_select_the_same_candidate(self):
        objective = "Assess sqlite write ahead logging checkpoint behavior"
        candidate = {"url": "https://example.org/sqlite-wal"}
        provenance = {
            "status": "RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url": candidate["url"],
            "final_url": candidate["url"],
        }
        relevance = {
            "objective": objective,
            "status": "LEXICAL_RELEVANCE_RANKED",
            "verification_method": "DETERMINISTIC_BM25",
            "output_verified": True,
            "top_candidate_original_index": 0,
            "ranked_candidates": [{
                "original_index": 0,
                "candidate": {"url": "https://different.example.net/page"},
                "lexical_relevance_score": 1.0,
                "matched_terms": ["sqlite"],
            }],
        }
        out = self.m.extract(
            objective,
            candidate,
            provenance,
            relevance,
            fetch=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(out["reason"], "CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT", out)

if __name__ == "__main__":
    unittest.main(verbosity=2)

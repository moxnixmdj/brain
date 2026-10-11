from __future__ import annotations

import unittest

from canonical.runtime import r2_generic_authority_candidate_checker_adapter_v1 as a


class Tests(unittest.TestCase):
    def decision(self):
        return {
            "bound_relevance_cegar_loop": {
                "truth_payloads_by_predicate_id": {
                    "p": {
                        "predicate_id": "p",
                        "target_claim_id": "c",
                        "source_text": "old",
                        "source_id": "old",
                        "fact_source": "{}",
                        "fact_source_id": "facts",
                        "claims": [{"claim_id": "c", "kind": "X"}],
                    }
                }
            }
        }

    def materialized(self):
        return {
            "schema": a.MATERIALIZATION_SCHEMA,
            "pass": True,
            "status": "PASS__AUTHORITY_CANDIDATE_MATERIALIZED_FOR_EXISTING_CHECKER",
            "semantic_truth_authority": False,
            "checker_material": {
                "source_text": "new authority text",
                "source_id": "authority-candidate-sha256:" + "a" * 64,
                "raw_sha256": "a" * 64,
                "raw_size_bytes": 18,
                "final_url": "https://docs.example.org/policy",
                "authority_domains": ["example.org"],
            },
        }

    def test_reuses_existing_checker_template_only(self):
        out = a.adapt(self.decision(), "p", {}, self.materialized())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_count"], 1)
        row = out["truth_payload_candidates"][0]
        self.assertEqual(row["source_text"], "new authority text")
        self.assertTrue(row["source_id"].startswith("authority-candidate-sha256:"))
        self.assertEqual(row["fact_source_id"], "facts")
        self.assertFalse(out["semantic_truth_authority"])
        self.assertTrue(out["downstream_checker_must_recompute_predicate_identity_and_truth"])

    def test_no_checker_template_does_not_invent_one(self):
        d = self.decision()
        d["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"]["p"] = {
            "truth_kind": "UNMODELED"
        }
        out = a.adapt(d, "p", {}, self.materialized())
        self.assertFalse(out["pass"])
        self.assertTrue(out["status"].startswith("NOT_APPLICABLE__"))
        self.assertFalse(out["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

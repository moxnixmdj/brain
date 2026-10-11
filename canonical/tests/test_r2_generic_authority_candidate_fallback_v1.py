from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_regcap_authority_candidate_adapter_v1 as a


class Tests(unittest.TestCase):
    def test_non_regcap_request_reuses_generic_materialization_and_checker(self):
        decision = {
            "bound_relevance_cegar_loop": {
                "truth_payloads_by_predicate_id": {
                    "p": {
                        "target_claim_id": "c",
                        "claims": [{"claim_id": "c", "kind": "X"}],
                    }
                }
            }
        }
        request = {
            "source_scope": {
                "kind": "UNBOUND_SOURCE",
                "authority_domains": ["example.org"],
                "query": "x",
            }
        }
        candidate = {
            "schema": a.discovery.SCHEMA,
            "pass": True,
            "candidate_only": True,
            "semantic_truth_authority": False,
        }
        materialized = {
            "schema": a.generic_materialization.SCHEMA,
            "pass": True,
            "status": "PASS",
            "semantic_truth_authority": False,
            "raw_sha256": "a" * 64,
            "checker_material": {
                "source_text": "authority",
                "source_id": "authority-candidate-sha256:" + "a" * 64,
            },
        }
        generic = {
            "pass": True,
            "status": "PASS",
            "truth_payload_candidates": [{"predicate_id": "p"}],
            "downstream_checker_must_recompute_predicate_identity_and_truth": True,
        }
        with patch.object(
            a.generic_materialization, "materialize", return_value=materialized
        ), patch.object(
            a.generic_checker_adapter, "adapt", return_value=generic
        ):
            out = a.adapt(decision, "p", request, candidate)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_count"], 1)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["original_predicate_identity_preserved"])
        self.assertTrue(out["downstream_checker_recomputes_predicate_identity_and_truth"])

    def test_generic_materialization_failure_stays_fail_closed(self):
        decision = {
            "bound_relevance_cegar_loop": {
                "truth_payloads_by_predicate_id": {}
            }
        }
        request = {"source_scope": {"kind": "UNBOUND_SOURCE"}}
        candidate = {
            "schema": a.discovery.SCHEMA,
            "pass": True,
            "candidate_only": True,
            "semantic_truth_authority": False,
        }
        with patch.object(
            a.generic_materialization,
            "materialize",
            return_value={"pass": False, "status": "FAIL_CLOSED", "reason": "DRIFT"},
        ):
            out = a.adapt(decision, "p", request, candidate)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DRIFT", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

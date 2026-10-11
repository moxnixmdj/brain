from __future__ import annotations

import unittest

from canonical.runtime import r2_regcap_authority_candidate_adapter_v1 as a
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four
from canonical.runtime import r2_authority_domain_discovery_provider_v1 as discovery


PID = "regcap-loss-cushion-sha256:original"


def payload():
    return {
        "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
        "predicate_id": PID,
        "claim_kind": "RELATIVE_RIVAL_SELECTION",
        "source_text": "The loss-absorbing cushion is unresolved.",
        "source_id": "doc:original",
        "start": 4,
        "end": 26,
        "target_concept_id": "REGCAP::MREL",
    }


def decision():
    return {
        "bound_relevance_cegar_loop": {
            "truth_payloads_by_predicate_id": {PID: payload()}
        }
    }


def request():
    return {
        "truth_next_information_request": {
            "request_kind": a.REQUEST_KIND,
            "scope_id": four.SCOPE_ID,
            "observation_id": four.OBSERVATION_ID,
            "candidate_concept_ids": list(four.DOMAIN),
            "allowed_outcomes": dict(four.OUTCOMES),
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        },
        "source_scope": {
            "kind": discovery.SCOPE_KIND,
            "query": "official regulatory requirement",
            "authority_domains": ["example.org"],
            "timeout_s": 20,
            "max_bytes": 1500000,
        },
    }


def candidate():
    return {
        "schema": discovery.SCHEMA,
        "pass": True,
        "candidate_only": True,
        "semantic_truth_authority": False,
        "chosen_url": "https://data.example.org/requirement",
        "chosen_host": "data.example.org",
        "query": "official regulatory requirement",
        "authority_domains": ["example.org"],
        "discovery_evidence_path": "canonical/astra_runtime/tmp/evidence.json",
    }


class Tests(unittest.TestCase):
    def test_exact_four_way_request_attaches_candidate_without_replacing_predicate(self):
        out = a.adapt(decision(), PID, request(), candidate())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_truth_authority"])
        rows = out["truth_payload_candidates"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["predicate_id"], PID)
        self.assertEqual(rows[0]["source_id"], "doc:original")
        self.assertEqual(
            rows[0]["governing_requirement_candidate"]["chosen_url"],
            candidate()["chosen_url"],
        )
        self.assertTrue(out["original_predicate_identity_preserved"])

    def test_generic_non_regcap_truth_is_not_rewritten(self):
        d = decision()
        d["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"][PID][
            "truth_kind"
        ] = "DOMAIN_MAPPING_RELATION"
        out = a.adapt(d, PID, request(), candidate())
        self.assertFalse(out["pass"])
        self.assertTrue(out["status"].startswith("NOT_APPLICABLE__"))

    def test_four_way_outcome_drift_fails_closed(self):
        req = request()
        req["truth_next_information_request"]["allowed_outcomes"]["REGCAP::MREL"] = "DRIFT"
        out = a.adapt(decision(), PID, req, candidate())
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OUTCOME_DRIFT", out["reason"])

    def test_identical_candidate_cannot_be_appended_forever(self):
        first = a.adapt(decision(), PID, request(), candidate())
        d = decision()
        d["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"][PID] = [
            payload(),
            first["truth_payload_candidates"][0],
        ]
        out = a.adapt(d, PID, request(), candidate())
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__IDENTICAL_AUTHORITY_CANDIDATE_ALREADY_ATTEMPTED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

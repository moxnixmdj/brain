from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_four_way_authority_candidate_observation_v1 as o
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four


def candidate():
    return {
        "chosen_url": "https://data.example.org/requirement",
        "chosen_host": "data.example.org",
        "query": "official requirement",
        "authority_domains": ["example.org"],
        "timeout_s": 20,
        "max_bytes": 1500000,
        "discovery_evidence_path": "canonical/astra_runtime/tmp/evidence.json",
    }


def fetch(url, *, domains, max_bytes, timeout_s):
    return (
        b"The governing requirement is stated here.",
        "https://data.example.org/requirement",
        "text/plain; charset=utf-8",
    )


def authority():
    return {
        "pass": True,
        "semantic_truth_authority": True,
        "outcomes": dict(four.OUTCOMES),
        "authority_sha256": "a" * 64,
    }


class Tests(unittest.TestCase):
    def test_checker_owned_refetch_can_certify_one_existing_four_way_outcome(self):
        with patch.object(
            o,
            "_matrix_candidates",
            return_value=[{
                "candidate_id": "REGCAP::CCOB",
                "evidence_kind": "REGCAP_CONTEXTUAL_OBSERVATION",
            }],
        ), patch.object(
            o.tlac_mrel,
            "compile_context",
            return_value={"pass": False, "status": "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR"},
        ), patch.object(o.four, "verify_authority", return_value=authority()):
            out = o.observe(candidate(), fetcher=fetch)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], "REGCAP::CCOB")
        self.assertEqual(out["observation_id"], four.OBSERVATION_ID)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_conflicting_existing_compilers_fail_closed(self):
        with patch.object(
            o,
            "_matrix_candidates",
            return_value=[{"candidate_id": "REGCAP::CCOB"}],
        ), patch.object(
            o.tlac_mrel,
            "compile_context",
            return_value={
                "pass": True,
                "status": "PASS__BOUND_TLAC_MREL_CONTEXT_SIGNATURE",
                "selected_candidate_hint": "REGCAP::MREL",
                "observation_id": "GOVERNING_REQUIREMENT_CLASS",
                "observed_outcome": "EU_MREL",
                "matches": [],
            },
        ):
            out = o.observe(candidate(), fetcher=fetch)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONFLICTING", out["reason"])

    def test_redirect_outside_declared_authority_fails_closed(self):
        def bad_fetch(url, *, domains, max_bytes, timeout_s):
            return (
                b"text",
                "https://evil.example/redirect",
                "text/plain",
            )
        out = o.observe(candidate(), fetcher=bad_fetch)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OUTSIDE_DECLARED_AUTHORITY", out["reason"])

    def test_candidate_host_must_match_candidate_url_host(self):
        row = candidate()
        row["chosen_host"] = "other.example.org"
        out = o.observe(row, fetcher=fetch)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("HOST_URL_HOST_MISMATCH", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

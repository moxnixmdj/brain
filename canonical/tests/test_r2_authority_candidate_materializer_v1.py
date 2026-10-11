from __future__ import annotations

import unittest

from canonical.runtime import r2_authority_candidate_materializer_v1 as m


def request(**scope_updates):
    scope = {
        "kind": m.SCOPE_KIND,
        "query": "official indicator",
        "authority_domains": ["example.com"],
        "timeout_s": 10,
        "max_bytes": 1024,
    }
    scope.update(scope_updates)
    return {
        "schema": m.REQUEST_SCHEMA,
        "external_research_authorized": True,
        "acquisition_plan": {
            "action": m.ACTION,
            "external_research_authorized": True,
        },
        "source_scope": scope,
    }


def candidate(**updates):
    out = {
        "schema": m.DISCOVERY_SCHEMA,
        "pass": True,
        "candidate_only": True,
        "chosen_url": "https://data.example.com/source",
        "chosen_host": "data.example.com",
        "candidate_count": 1,
        "discovery_evidence_path": "canonical/astra_runtime/tmp/discovery.json",
        "semantic_truth_authority": False,
    }
    out.update(updates)
    return out


class Tests(unittest.TestCase):
    def test_materializes_exact_authority_bytes_without_truth_authority(self):
        out = m.materialize(
            request(),
            candidate(),
            fetcher=lambda url, **kwargs: (
                b"authoritative bytes",
                "https://data.example.com/source",
            ),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["retrieval_materialization_verified"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["provider_authority"])
        self.assertEqual(out["source_text"], "authoritative bytes")
        self.assertEqual(
            out["next_required_edge"],
            "CHECKER_SPECIFIC_AUTHENTICATED_SOURCE_INTERPRETATION",
        )

    def test_cross_authority_redirect_fails_closed(self):
        out = m.materialize(
            request(),
            candidate(),
            fetcher=lambda url, **kwargs: (
                b"x",
                "https://evil.example/source",
            ),
        )
        self.assertFalse(out["pass"])
        self.assertIn("REDIRECT_OUTSIDE_AUTHORITY", out["reason"])

    def test_discovery_candidate_outside_authority_fails_closed(self):
        out = m.materialize(
            request(),
            candidate(
                chosen_url="https://evil.example/source",
                chosen_host="evil.example",
            ),
            fetcher=lambda url, **kwargs: (b"x", url),
        )
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_AUTHORITY", out["reason"])

    def test_candidate_host_mismatch_fails_closed(self):
        out = m.materialize(
            request(),
            candidate(chosen_host="other.example.com"),
            fetcher=lambda url, **kwargs: (b"x", url),
        )
        self.assertFalse(out["pass"])
        self.assertIn("HOST_MISMATCH", out["reason"])

    def test_oversize_source_fails_closed(self):
        out = m.materialize(
            request(max_bytes=1),
            candidate(),
            fetcher=lambda url, **kwargs: (
                b"xx",
                "https://data.example.com/source",
            ),
        )
        self.assertFalse(out["pass"])
        self.assertIn("SIZE_LIMIT", out["reason"])

    def test_non_utf8_source_fails_closed(self):
        out = m.materialize(
            request(),
            candidate(),
            fetcher=lambda url, **kwargs: (
                b"\xff",
                "https://data.example.com/source",
            ),
        )
        self.assertFalse(out["pass"])
        self.assertIn("UnicodeDecodeError", out["reason"])

    def test_provider_cannot_claim_truth_authority(self):
        c = candidate(semantic_truth_authority=True)
        out = m.materialize(
            request(),
            c,
            fetcher=lambda url, **kwargs: (b"x", url),
        )
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_INFLATION", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

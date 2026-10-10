from __future__ import annotations

import unittest

from canonical.runtime import r2_authority_domain_discovery_provider_v1 as p


def _request():
    return {
        "schema": p.REQUEST_SCHEMA,
        "predicate_id": "source-condition-sha256:critical",
        "external_research_authorized": True,
        "acquisition_plan": {
            "pass": True,
            "action": p.ACTION,
            "external_research_authorized": True,
        },
        "source_scope": {
            "kind": p.SCOPE_KIND,
            "query": "World Bank SP.POP.TOTL official indicator",
            "authority_domains": ["worldbank.org"],
            "timeout_s": 20,
            "max_bytes": 1500000,
        },
    }


class Tests(unittest.TestCase):
    def test_verified_authority_candidate_remains_candidate_only(self):
        seen = {}

        def discover(action):
            seen.update(action)
            return {
                "verified": True,
                "chosen_url": "https://data.worldbank.org/indicator/SP.POP.TOTL",
                "chosen_host": "data.worldbank.org",
                "candidate_count": 3,
                "output_path": "canonical/astra_runtime/tmp/evidence.json",
            }

        out = p.provide(_request(), discoverer=discover)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["materialization_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertEqual(
            out["next_required_edge"],
            "CHECKER_CONSUMABLE_MATERIALIZATION_FROM_AUTHORITY_CANDIDATE",
        )
        self.assertEqual(seen["type"], "discover_authoritative_web_source")
        self.assertEqual(
            seen["args"]["authority_domains"],
            ["worldbank.org"],
        )

    def test_external_research_must_be_explicitly_authorized(self):
        req = _request()
        req["external_research_authorized"] = False
        out = p.provide(req, discoverer=lambda action: {})
        self.assertFalse(out["pass"])
        self.assertIn("NOT_AUTHORIZED", out["reason"])

    def test_candidate_outside_authority_fails_closed(self):
        def discover(action):
            return {
                "verified": True,
                "chosen_url": "https://evil.example/fake",
                "chosen_host": "evil.example",
            }

        out = p.provide(_request(), discoverer=discover)
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_AUTHORITY", out["reason"])

    def test_discovery_miss_stays_open_without_truth_authority(self):
        out = p.provide(
            _request(),
            discoverer=lambda action: {
                "verified": False,
                "error": "AUTHORITATIVE_SOURCE_NOT_DISCOVERED",
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_AUTHORITY_DOMAIN_CANDIDATE_DISCOVERED",
        )
        self.assertFalse(out["semantic_truth_authority"])

    def test_non_research_action_is_not_handled(self):
        req = _request()
        req["acquisition_plan"]["action"] = "OBSERVE_BOUND_SOURCE_ONLY"
        self.assertIsNone(p.provide(req, discoverer=lambda action: {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)

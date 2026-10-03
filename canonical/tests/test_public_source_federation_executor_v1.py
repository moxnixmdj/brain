from __future__ import annotations

import copy
import unittest

from canonical.runtime import public_source_federation_v1 as federation
from canonical.runtime import public_source_federation_executor_v1 as executor


def fake_discover(query, limit=8, timeout=15, query_override=None):
    q = query_override or query
    if "gitlab.com" in q:
        return {
            "status": "CANDIDATES_DISCOVERED",
            "candidates": [
                {"url": "https://gitlab.com/acme/codec", "title": "codec"},
                {"url": "https://github.com/wrong/host", "title": "off-domain"},
            ],
            "retrieval_provenance": [{"backend": "FAKE", "candidate_count": 2}],
            "backend_errors": [],
        }
    if "gitee.com" in q:
        return {
            "status": "DISCOVERY_UNAVAILABLE",
            "candidates": [],
            "retrieval_provenance": [{"backend": "FAKE", "candidate_count": 0}],
            "backend_errors": [],
        }
    if "codeberg.org" in q:
        raise RuntimeError("temporary outage")
    return {
        "status": "CANDIDATES_DISCOVERED",
        "candidates": [{"url": "https://example.com/off-domain"}],
        "retrieval_provenance": [{"backend": "FAKE", "candidate_count": 1}],
        "backend_errors": [],
    }


class PublicSourceFederationExecutorV1Tests(unittest.TestCase):
    def fed(self):
        return federation.compile_federation(
            ["UBJSON serializer"], max_queries_per_source=1
        )

    def test_executes_real_source_cells_and_filters_off_domain(self):
        out = executor.execute(
            self.fed(), max_requests=2, discover_fn=fake_discover
        )
        self.assertEqual(out["executed_request_count"], 2, out)
        self.assertEqual(out["candidate_count"], 1, out)
        self.assertEqual(out["candidates"][0]["federation_domain"], "gitlab.com")
        self.assertEqual(out["candidates"][0]["sufficiency_status"], "UNVERIFIED")
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_empty_successful_cell_is_consumed_but_not_nonexistence(self):
        fed = self.fed()
        fed["requests"] = [
            x for x in fed["requests"] if x["domain"] == "gitee.com"
        ]
        out = executor.execute(fed, discover_fn=fake_discover)
        self.assertEqual(out["cells"][0]["status"], "QUERIED_NO_CANDIDATE", out)
        self.assertEqual(len(out["newly_consumed_request_ids"]), 1, out)
        self.assertFalse(out["cells"][0]["nonexistence_claim_authorized"])
        self.assertFalse(out["complete"])

    def test_transient_failure_stays_retryable_and_unconsumed(self):
        fed = self.fed()
        fed["requests"] = [
            x for x in fed["requests"] if x["domain"] == "codeberg.org"
        ]
        out = executor.execute(fed, discover_fn=fake_discover)
        self.assertEqual(out["cells"][0]["status"], "FAILED_TRANSIENT", out)
        self.assertTrue(out["cells"][0]["retryable"])
        self.assertEqual(out["newly_consumed_request_ids"], [])
        self.assertEqual(out["failed_transient_request_count"], 1)

    def test_consumed_cell_is_not_executed_twice(self):
        fed = self.fed()
        first = executor.execute(fed, max_requests=1, discover_fn=fake_discover)
        second = executor.execute(
            fed,
            consumed_request_ids=first["consumed_request_ids_after"],
            max_requests=1,
            discover_fn=fake_discover,
        )
        self.assertGreaterEqual(second["skipped_consumed_request_count"], 1, second)
        self.assertNotEqual(
            first["newly_consumed_request_ids"],
            second["newly_consumed_request_ids"],
        )

    def test_candidate_authority_smuggling_fails_closed(self):
        fed = self.fed()
        fed["requests"] = [
            x for x in fed["requests"] if x["domain"] == "gitlab.com"
        ]
        def bad(query, limit=8, timeout=15, query_override=None):
            return {
                "status": "CANDIDATES_DISCOVERED",
                "candidates": [{
                    "url": "https://gitlab.com/acme/codec",
                    "verified_sufficient": True,
                }],
                "retrieval_provenance": [{"backend": "BAD"}],
                "backend_errors": [],
            }
        out = executor.execute(fed, discover_fn=bad)
        self.assertEqual(out["cells"][0]["status"], "FAILED_TRANSIENT", out)
        self.assertEqual(out["candidate_count"], 0)
        self.assertEqual(out["acceptance_credit"], 0)

    def test_epoch_hash_is_deterministic(self):
        fed = self.fed()
        a = executor.execute(fed, max_requests=3, discover_fn=fake_discover)
        b = executor.execute(copy.deepcopy(fed), max_requests=3, discover_fn=fake_discover)
        self.assertEqual(a["source_epoch_sha256"], b["source_epoch_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import r2_authority_candidate_materialization_v1 as m


def request():
    return {
        "source_scope": {
            "kind": "UNBOUND_SOURCE",
            "query": "governing requirement",
            "authority_domains": ["example.org"],
            "timeout_s": 10,
            "max_bytes": 10000,
        }
    }


def candidate():
    return {
        "schema": m.DISCOVERY_SCHEMA,
        "pass": True,
        "candidate_only": True,
        "semantic_truth_authority": False,
        "chosen_url": "https://docs.example.org/policy",
        "chosen_host": "docs.example.org",
        "authority_domains": ["example.org"],
        "query": "governing requirement",
    }


class Tests(unittest.TestCase):
    def test_materializes_exact_bytes_without_truth_authority(self):
        raw = b"<html><body><p>Total exposure means exposure_amount.</p></body></html>"

        def fetch(url, *, domains, max_bytes, timeout_s):
            self.assertEqual(domains, ["example.org"])
            return raw, url, "text/html; charset=utf-8"

        out = m.materialize(request(), candidate(), fetcher=fetch)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["raw_sha256"], sha256(raw).hexdigest())
        self.assertIn("Total exposure", out["checker_material"]["source_text"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_redirect_or_candidate_outside_declared_domain_fails_closed(self):
        c = candidate()
        c["chosen_url"] = "https://evil.example.net/policy"
        c["chosen_host"] = "evil.example.net"
        out = m.materialize(
            request(),
            c,
            fetcher=lambda *a, **k: (b"x", c["chosen_url"], "text/plain"),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OUTSIDE_DECLARED_AUTHORITY", out["reason"])

    def test_non_utf8_is_materialized_but_not_promoted_to_text_truth(self):
        def fetch(url, *, domains, max_bytes, timeout_s):
            return b"\xff\xfe", url, "application/octet-stream"

        out = m.materialize(request(), candidate(), fetcher=fetch)
        self.assertFalse(out["pass"])
        self.assertTrue(out["materialized"])
        self.assertIn("NON_UTF8", out["status"])
        self.assertFalse(out["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

from email.message import Message
from hashlib import sha256
import unittest

from canonical.runtime.pinned_https_source_fragment_authority_v1 import (
    PACK_SCHEMA,
    verify_pack,
)


RAW = b"""<!doctype html><html><body>
<p>A capital conservation buffer of 2.5%, comprised of Common Equity Tier 1 (CET1), is established above the regulatory minimum capital requirement.</p>
<p>The requirement will be released when system-wide risk crystallises or dissipates.</p>
</body></html>"""


class Response:
    def __init__(self, raw=RAW, url="https://example.test/source"):
        self._raw = raw
        self._url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def read(self):
        return self._raw

    def geturl(self):
        return self._url


def opener_for(response):
    def open_(_request, timeout=30):
        del timeout
        return response

    return open_


def pack(**overrides):
    row = {
        "schema": PACK_SCHEMA,
        "source_id": "source:test",
        "url": "https://example.test/source",
        "expected_raw_sha256": sha256(RAW).hexdigest(),
        "expected_byte_count": len(RAW),
        "retrieval_user_agent": "ProjectBrainPinnedSourceVerifier/1.0",
        "fragments": [
            {
                "fragment_id": "CCOB_CET1_ABOVE_MINIMUM",
                "text": (
                    "A capital conservation buffer of 2.5%, comprised of "
                    "Common Equity Tier 1 (CET1), is established above the "
                    "regulatory minimum capital requirement."
                ),
            },
            {
                "fragment_id": "CCYB_RELEASE",
                "text": (
                    "The requirement will be released when system-wide risk "
                    "crystallises or dissipates."
                ),
            },
        ],
    }
    row.update(overrides)
    return row


class Tests(unittest.TestCase):
    def test_exact_pinned_source_and_fragments_pass(self):
        out = verify_pack(pack(), opener=opener_for(Response()))
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["source_fragment_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(
            set(out["receipt"]["fragment_ids"]),
            {"CCOB_CET1_ABOVE_MINIMUM", "CCYB_RELEASE"},
        )

    def test_raw_byte_drift_fails_closed(self):
        out = verify_pack(
            pack(),
            opener=opener_for(Response(RAW + b" drift")),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "RAW_SOURCE_SHA256_MISMATCH")

    def test_missing_fragment_fails_closed(self):
        row = pack(
            fragments=[{
                "fragment_id": "NOPE",
                "text": "This sentence does not exist in the pinned source.",
            }]
        )
        out = verify_pack(row, opener=opener_for(Response()))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PINNED_FRAGMENT_NOT_FOUND_IN_SOURCE")

    def test_non_https_source_fails_closed(self):
        out = verify_pack(
            pack(url="http://example.test/source"),
            opener=opener_for(Response()),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "HTTPS_URL_REQUIRED")

    def test_unmodeled_pack_field_fails_closed(self):
        out = verify_pack(
            pack(extra="caller-smuggled-semantics"),
            opener=opener_for(Response()),
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_PACK_FIELDS", out["reason"])

    def test_normalization_allows_html_whitespace_only(self):
        row = pack(
            fragments=[{
                "fragment_id": "CCYB_RELEASE",
                "text": (
                    "The requirement will be released when system-wide risk "
                    "crystallises or dissipates."
                ),
            }]
        )
        out = verify_pack(row, opener=opener_for(Response()))
        self.assertTrue(out["pass"], out)

    def test_source_authentication_never_self_promotes_to_semantic_truth(self):
        out = verify_pack(pack(), opener=opener_for(Response()))
        self.assertTrue(out["pass"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

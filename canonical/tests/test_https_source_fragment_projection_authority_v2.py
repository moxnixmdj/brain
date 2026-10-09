from __future__ import annotations

from email.message import Message
import unittest

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    PACK_SCHEMA,
    verify_projection_pack,
)


BASE = b"""<!doctype html><html><body>
<h2>Capital conservation buffer</h2>
<p>A capital conservation buffer of 2.5%, comprised of Common Equity Tier 1 (CET1), is established above the regulatory minimum capital requirement.</p>
<h2>Countercyclical buffer</h2>
<p>The requirement will be released when system-wide risk crystallises or dissipates.</p>
</body></html>"""


class Response:
    def __init__(self, raw=BASE, url="https://example.test/source"):
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
        "retrieval_user_agent": "ProjectBrainSourceProjectionVerifier/2.0",
        "fragments": [
            {
                "fragment_id": "CCOB",
                "section_anchor": "Capital conservation buffer",
                "text": (
                    "A capital conservation buffer of 2.5%, comprised of "
                    "Common Equity Tier 1 (CET1), is established above the "
                    "regulatory minimum capital requirement."
                ),
                "max_chars_after_anchor": 1000,
            },
            {
                "fragment_id": "CCYB",
                "section_anchor": "Countercyclical buffer",
                "text": (
                    "The requirement will be released when system-wide risk "
                    "crystallises or dissipates."
                ),
                "max_chars_after_anchor": 1000,
            },
        ],
    }
    row.update(overrides)
    return row


class Tests(unittest.TestCase):
    def test_exact_projection_passes(self):
        out = verify_projection_pack(
            pack(),
            opener=opener_for(Response()),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["source_fragment_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["raw_byte_identity_required"])
        self.assertEqual(
            set(out["receipt"]["fragment_ids"]),
            {"CCOB", "CCYB"},
        )

    def test_irrelevant_raw_byte_drift_does_not_break_projection(self):
        drifted = BASE.replace(
            b"<body>",
            b"<body><div>unrelated navigation changed by two bytes ++</div>",
        )
        out = verify_projection_pack(
            pack(),
            opener=opener_for(Response(drifted)),
        )
        self.assertTrue(out["pass"], out)
        self.assertNotEqual(
            out["observed_raw_byte_count"],
            len(BASE),
        )

    def test_changed_fragment_fails_closed(self):
        changed = BASE.replace(
            b"released when system-wide risk crystallises or dissipates",
            b"released at some other time",
        )
        out = verify_projection_pack(
            pack(),
            opener=opener_for(Response(changed)),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SOURCE_FRAGMENT_PROJECTION_NOT_FOUND",
        )

    def test_wrong_section_anchor_fails_closed(self):
        row = pack()
        row["fragments"][0]["section_anchor"] = "Some other section"
        out = verify_projection_pack(
            row,
            opener=opener_for(Response()),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SOURCE_FRAGMENT_PROJECTION_NOT_FOUND",
        )

    def test_fragment_too_far_from_anchor_fails_closed(self):
        row = pack()
        row["fragments"][0]["max_chars_after_anchor"] = 5
        out = verify_projection_pack(
            row,
            opener=opener_for(Response()),
        )
        self.assertFalse(out["pass"])

    def test_final_url_mismatch_fails_closed(self):
        out = verify_projection_pack(
            pack(),
            opener=opener_for(
                Response(url="https://evil.example/source")
            ),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FINAL_URL_MISMATCH")

    def test_http_url_rejected(self):
        out = verify_projection_pack(
            pack(url="http://example.test/source"),
            opener=opener_for(Response()),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "HTTPS_URL_REQUIRED")

    def test_projection_does_not_grant_semantic_or_terminal_authority(self):
        out = verify_projection_pack(
            pack(),
            opener=opener_for(Response()),
        )
        self.assertTrue(out["pass"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

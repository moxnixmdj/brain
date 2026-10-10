from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import margin_contextual_term_identity_v1 as margin

ROOT = Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(x["fragment_id"]) for x in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_net_interest_margin_exact_term_resolves(self):
        text = "The bank's net interest margin increased."
        start = text.index("net interest margin")
        end = start + len("net interest margin")
        out = margin.resolve_span(
            text,
            start=start,
            end=end,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], margin.NET_INTEREST_MARGIN)
        self.assertTrue(out["occurrence_identity_authority"])
        self.assertFalse(out["bare_margin_sense_authority"])
        self.assertEqual(
            text[out["margin_head_span"][0]:out["margin_head_span"][1]].casefold(),
            "margin",
        )

    def test_initial_margin_exact_term_resolves(self):
        text = "Initial margin increased after the position was opened."
        start = text.index("Initial margin")
        end = start + len("Initial margin")
        out = margin.resolve_span(
            text,
            start=start,
            end=end,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], margin.INITIAL_MARGIN)
        self.assertTrue(out["occurrence_identity_authority"])
        self.assertFalse(out["bare_margin_sense_authority"])

    def test_bare_margin_remains_unresolved(self):
        text = "Margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__OUTSIDE_BOUND_CONTEXTUAL_MARGIN_TERMS",
        )
        self.assertFalse(out["bare_margin_sense_authority"])

    def test_interest_margin_without_net_remains_unresolved(self):
        text = "Interest margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Interest margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])

    def test_gross_margin_remains_unresolved(self):
        text = "Gross margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Gross margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])

    def test_wrong_span_does_not_leak_sentence_context(self):
        text = "The bank's net interest margin increased."
        start = text.index("interest margin")
        end = start + len("interest margin")
        out = margin.resolve_span(
            text,
            start=start,
            end=end,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])

    def test_two_terms_have_distinct_occurrence_concepts(self):
        a_text = "Net interest margin increased."
        b_text = "Initial margin increased."
        a = margin.resolve_span(
            a_text,
            start=0,
            end=len("Net interest margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        b = margin.resolve_span(
            b_text,
            start=0,
            end=len("Initial margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(a["pass"], a)
        self.assertTrue(b["pass"], b)
        self.assertNotEqual(a["concept_id"], b["concept_id"])
        self.assertNotEqual(a["occurrence_id"], b["occurrence_id"])

    def test_source_authentication_failure_fails_closed(self):
        text = "Initial margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Initial margin"),
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PINNED_TERM_SOURCE_AUTHORITY_FAILED")

    def test_missing_fragment_fails_closed(self):
        text = "Net interest margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Net interest margin"),
            repo_root=ROOT,
            projection_verifier=lambda _pack: {
                "pass": True,
                "receipt": {
                    "fragment_ids": [],
                    "receipt_sha256": "b" * 64,
                },
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "REQUIRED_TERM_FRAGMENT_NOT_AUTHENTICATED",
        )

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / margin.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / margin.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
            out = margin.resolve_span(
                "Initial margin increased.",
                start=0,
                end=len("Initial margin"),
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_terminal_or_global_bare_margin_authority(self):
        text = "Net interest margin increased."
        out = margin.resolve_span(
            text,
            start=0,
            end=len("Net interest margin"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["bare_margin_sense_authority"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

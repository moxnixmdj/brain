import unittest

from canonical.runtime.aa_briefcase_authority_convention_sweep_v1 import (
    REVIEW_SCHEMA,
    AuthoritySweepError,
    discover_candidates,
    verify_review,
)


def parse_manifest():
    return {
        "status": "PASS__ALL_DECLARED_SOURCES_PARSED",
        "parse_manifest_sha256": "p" * 64,
        "receipts": [
            {
                "source_path": "shared/standards.docx",
                "source_sha256": "a" * 64,
                "parsed": {
                    "format": "docx",
                    "parts": [
                        {"part": "word/document.xml", "text": "Firm standard: all financial figures must use USD and include source vintage."}
                    ],
                },
            },
            {
                "source_path": "week/slack.json",
                "source_sha256": "b" * 64,
                "parsed": {
                    "format": "json",
                    "canonical": {
                        "msg": "Current instruction overrides the old case: use three transition scenarios and reconcile top-down to bottom-up."
                    },
                },
            },
            {
                "source_path": "week/scenario_note.txt",
                "source_sha256": "c" * 64,
                "parsed": {
                    "format": "txt",
                    "text": "Scenario sensitivity note for planning."
                },
            },
        ],
    }


def review_for(sweep):
    rows = []
    for c in sweep["candidates"]:
        action = "AUTHORITY" if c["high_signal"] else "DIMENSION"
        rows.append({
            "candidate_id": c["candidate_id"],
            "action": action,
            "target_ids": ["x"],
        })
    return {
        "schema": REVIEW_SCHEMA,
        "sweep_sha256": sweep["sweep_sha256"],
        "rows": rows,
    }


class T(unittest.TestCase):
    def test_discovers_standard_override_currency_scenario_and_reconciliation(self):
        out = discover_candidates(parse_manifest())
        classes = {c for row in out["candidates"] for c in row["classes"]}
        self.assertIn("STANDARD_POLICY", classes)
        self.assertIn("AUTHORITY_OVERRIDE", classes)
        self.assertIn("ASSUMPTION_CONTROL", classes)
        self.assertIn("PROFESSIONAL_CONVENTION", classes)
        self.assertIn("SCENARIO_STRUCTURE", classes)
        self.assertIn("RECONCILIATION_STRUCTURE", classes)
        self.assertGreater(out["high_signal_count"], 0)

    def test_complete_review_passes(self):
        sweep = discover_candidates(parse_manifest())
        out = verify_review(sweep, review_for(sweep))
        self.assertTrue(out["pass"])

    def test_unreviewed_candidate_blocks(self):
        sweep = discover_candidates(parse_manifest())
        review = review_for(sweep)
        review["rows"] = review["rows"][:-1]
        out = verify_review(sweep, review)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("UNREVIEWED_CANDIDATE:") for x in out["errors"]))

    def test_high_signal_cannot_be_dismissed_as_context(self):
        sweep = discover_candidates(parse_manifest())
        review = review_for(sweep)
        row = next(r for r in review["rows"] if sweep["candidates"][review["rows"].index(r)]["high_signal"])
        row["action"] = "CONTEXT_ONLY"
        row["context_only_justification_receipt"] = "why"
        row.pop("target_ids", None)
        out = verify_review(sweep, review)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("HIGH_SIGNAL_AUTHORITY_NOT_BOUND:") for x in out["errors"]))

    def test_context_only_requires_justification(self):
        sweep = discover_candidates(parse_manifest())
        review = review_for(sweep)
        low = next((c for c in sweep["candidates"] if not c["high_signal"]), None)
        self.assertIsNotNone(low)
        row = next(r for r in review["rows"] if r["candidate_id"] == low["candidate_id"])
        row["action"] = "CONTEXT_ONLY"
        row.pop("target_ids", None)
        out = verify_review(sweep, review)
        self.assertFalse(out["pass"])
        self.assertIn("CONTEXT_ONLY_JUSTIFICATION_MISSING:" + low["candidate_id"], out["errors"])

    def test_sweep_binding_drift_blocks(self):
        sweep = discover_candidates(parse_manifest())
        review = review_for(sweep)
        review["sweep_sha256"] = "0" * 64
        with self.assertRaisesRegex(AuthoritySweepError, "SWEEP_BINDING_MISMATCH"):
            verify_review(sweep, review)

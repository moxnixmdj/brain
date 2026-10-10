from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import semantic_truth_dispatch_v1 as dispatch
from canonical.runtime import spread_relation_context_identity_v1 as identity
from canonical.runtime import spread_relation_identity_truth_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass": True,
        "status": "PASS__FAKE_PROJECTION",
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"]) for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def nth_span(text: str, needle: str, occurrence: int = 0) -> tuple[int, int]:
    low = text.casefold()
    needle_low = needle.casefold()
    starts = []
    pos = 0
    while True:
        i = low.find(needle_low, pos)
        if i < 0:
            break
        starts.append(i)
        pos = i + len(needle_low)
    start = starts[occurrence]
    return start, start + len(needle)


def resolve(text: str, *, needle: str = "spread", occurrence: int = 0):
    start, end = nth_span(text, needle, occurrence)
    return identity.resolve_occurrence(
        text,
        start=start,
        end=end,
        repo_root=ROOT,
        projection_verifier=fake_projection,
    )


class SpreadRelationContextIdentityV1Tests(unittest.TestCase):
    def test_bid_ask_endpoint_relation_resolves(self):
        out = resolve(
            "The spread between the bid price and the ask price widened."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.BID_ASK)
        self.assertEqual(out["relation_signature"], "BID_ASK_ENDPOINTS")
        self.assertTrue(out["occurrence_identity_authority"])
        self.assertFalse(out["global_spread_sense_authority"])

    def test_bid_ask_hyphenated_term_resolves(self):
        out = resolve("The bid-ask spread widened.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.BID_ASK)

    def test_official_bid_ask_definition_shape_resolves(self):
        out = resolve(
            "The difference between the bid price and the ask price is called "
            "the spread."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.BID_ASK)

    def test_corporate_treasury_endpoint_relation_resolves(self):
        out = resolve(
            "The spread between corporate bond yields and comparable-maturity "
            "Treasury yields widened."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.CORP_TSY)
        self.assertEqual(
            out["relation_signature"],
            "CORPORATE_BOND_TREASURY_YIELD_ENDPOINTS",
        )

    def test_official_corporate_spread_definition_shape_resolves(self):
        out = resolve(
            "Corporate bond spreads, measured as the difference in yields "
            "between corporate bonds and comparable-maturity Treasury "
            "securities, narrowed.",
            needle="spreads",
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.CORP_TSY)

    def test_corporate_bond_spread_over_treasury_yields_resolves(self):
        out = resolve(
            "The corporate bond spread over comparable-maturity Treasury "
            "yields widened."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], identity.CORP_TSY)

    def test_bare_spread_remains_unresolved(self):
        out = resolve("The spread widened.")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_AUTHENTICATED_SPREAD_RELATION_SIGNATURE",
        )

    def test_nearby_bid_ask_words_do_not_donate_meaning(self):
        out = resolve(
            "Bid and ask prices moved while the spread widened."
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_AUTHENTICATED_SPREAD_RELATION_SIGNATURE",
        )

    def test_second_unrelated_spread_in_same_sentence_is_not_stolen(self):
        text = (
            "The spread between the bid price and the ask price widened, "
            "while another spread widened."
        )
        out = resolve(text, occurrence=1)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_AUTHENTICATED_SPREAD_RELATION_SIGNATURE",
        )

    def test_conflicting_endpoint_signatures_remain_unresolved(self):
        text = (
            "Corporate bond spread between the bid price and the ask price, "
            "measured as the difference in yields between corporate bonds and "
            "comparable-maturity Treasury securities, widened."
        )
        out = resolve(text)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__CONFLICTING_SPREAD_RELATION_SIGNATURES",
        )

    def test_negated_local_context_remains_unresolved(self):
        out = resolve(
            "The spread is not between the bid price and the ask price."
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
        )

    def test_target_span_must_be_spread(self):
        text = "The spread between the bid price and the ask price widened."
        start = text.index("bid")
        out = identity.resolve_occurrence(
            text,
            start=start,
            end=start + len("bid"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__TARGET_OCCURRENCE_IS_NOT_SPREAD",
        )

    def test_source_authentication_failure_fails_closed(self):
        text = "The bid-ask spread widened."
        start, end = nth_span(text, "spread")
        out = identity.resolve_occurrence(
            text,
            start=start,
            end=end,
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PINNED_SPREAD_SOURCE_AUTHORITY_FAILED")

    def test_missing_required_fragment_fails_closed(self):
        text = "The bid-ask spread widened."
        start, end = nth_span(text, "spread")
        out = identity.resolve_occurrence(
            text,
            start=start,
            end=end,
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
            "SPREAD_SOURCE_FRAGMENT_NOT_AUTHENTICATED",
        )

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / identity.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / identity.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
            text = "The bid-ask spread widened."
            start, end = nth_span(text, "spread")
            out = identity.resolve_occurrence(
                text,
                start=start,
                end=end,
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_policy_execution_or_terminal_authority(self):
        out = resolve("The bid-ask spread widened.")
        self.assertTrue(out["pass"], out)
        for key in (
            "global_spread_sense_authority",
            "open_world_finance_semantics_complete",
            "policy_adequacy_authority",
            "execution_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key], (key, out))
        self.assertEqual(out["terminal_credit_delta"], 0)


def truth_payload(text: str, target: str, *, needle: str = "spread"):
    start, end = nth_span(text, needle)
    return {
        "truth_kind": cert.TRUTH_KIND,
        "predicate_id": "caller-label",
        "source_text": text,
        "source_id": "doc:A",
        "start": start,
        "end": end,
        "target_concept_id": target,
    }


class SpreadRelationTruthCertificateV1Tests(unittest.TestCase):
    def test_matching_proved_identity_is_true(self):
        selected = {
            "pass": True,
            "status": "PASS__SPREAD_RELATION_CONTEXT_IDENTITY_AUTHENTICATED",
            "concept_id": identity.BID_ASK,
            "semantic_truth_authority": True,
            "terminal_authority": False,
        }
        with patch.object(identity, "resolve_occurrence", return_value=selected):
            out = cert.evaluate(
                truth_payload(
                    "The bid-ask spread widened.",
                    identity.BID_ASK,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])

    def test_different_proved_identity_remains_unknown_not_false(self):
        selected = {
            "pass": True,
            "status": "PASS__SPREAD_RELATION_CONTEXT_IDENTITY_AUTHENTICATED",
            "concept_id": identity.BID_ASK,
            "semantic_truth_authority": True,
            "terminal_authority": False,
        }
        with patch.object(identity, "resolve_occurrence", return_value=selected):
            out = cert.evaluate(
                truth_payload(
                    "The bid-ask spread widened.",
                    identity.CORP_TSY,
                )
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["reason"],
            "DIFFERENT_PROVED_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION",
        )

    def test_unresolved_identity_remains_unknown(self):
        unresolved = {
            "pass": False,
            "status": "UNRESOLVED__NO_AUTHENTICATED_SPREAD_RELATION_SIGNATURE",
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
        with patch.object(identity, "resolve_occurrence", return_value=unresolved):
            out = cert.evaluate(
                truth_payload("The spread widened.", identity.BID_ASK)
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_fail_closed_identity_does_not_fall_through(self):
        failed = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_DRIFT",
        }
        with patch.object(identity, "resolve_occurrence", return_value=failed):
            out = cert.evaluate(
                truth_payload("The spread widened.", identity.BID_ASK)
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "SPREAD_RELATION_AUTHORITY_FAIL_CLOSED")

    def test_unsupported_target_fails_closed(self):
        out = cert.evaluate(
            truth_payload("The spread widened.", "FINANCE::MAGIC_SPREAD")
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_CONCEPT_UNSUPPORTED", out["reason"])

    def test_dispatch_routes_spread_relation_truth_kind(self):
        expected = {"pass": True, "predicate_truth": "TRUE"}
        with patch.object(
            dispatch,
            "evaluate_spread_relation_identity",
            return_value=expected,
        ) as fn:
            out = dispatch.evaluate(
                {
                    "truth_kind": "SPREAD_RELATION_IDENTITY",
                    "predicate_id": "x",
                }
            )
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_existing_margin_route_is_unchanged(self):
        expected = {"pass": False, "predicate_truth": "UNKNOWN"}
        with patch.object(
            dispatch,
            "evaluate_margin_context_identity",
            return_value=expected,
        ) as fn:
            out = dispatch.evaluate(
                {
                    "truth_kind": "MARGIN_CONTEXT_IDENTITY",
                    "predicate_id": "x",
                }
            )
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_true_result_never_grants_policy_or_terminal_authority(self):
        selected = {
            "pass": True,
            "status": "PASS__SPREAD_RELATION_CONTEXT_IDENTITY_AUTHENTICATED",
            "concept_id": identity.CORP_TSY,
            "semantic_truth_authority": True,
            "terminal_authority": False,
        }
        with patch.object(identity, "resolve_occurrence", return_value=selected):
            out = cert.evaluate(
                truth_payload(
                    "The corporate bond spread over Treasury yields widened.",
                    identity.CORP_TSY,
                )
            )
        self.assertTrue(out["pass"], out)
        for key in (
            "global_identity_authority",
            "open_world_finance_semantics_complete",
            "policy_adequacy_authority",
            "execution_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key], (key, out))
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

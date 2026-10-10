from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import margin_context_identity_truth_certificate_v1 as cert
from canonical.runtime import margin_contextual_term_identity_v1 as term
from canonical.runtime import arm_margin_context_identity_v1 as arm
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch


def payload(text, start, end, target):
    return {
        "truth_kind": cert.TRUTH_KIND,
        "predicate_id": "caller-label",
        "source_text": text,
        "source_id": "doc:A",
        "start": start,
        "end": end,
        "target_concept_id": target,
    }


def proved(concept):
    return {
        "pass": True,
        "status": "PASS__BOUND_IDENTITY",
        "concept_id": concept,
        "semantic_truth_authority": True,
        "occurrence_identity_authority": True,
        "terminal_authority": False,
    }


def unresolved(reason="unresolved"):
    return {
        "pass": False,
        "status": "UNRESOLVED__TEST",
        "reason": reason,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_exact_net_interest_margin_proves_true(self):
        text = "Net interest margin increased."
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value=proved(term.NET_INTEREST_MARGIN),
        ) as term_fn, patch.object(
            cert.arm_identity,
            "resolve_occurrence",
        ) as arm_fn:
            out = cert.evaluate(
                payload(text, 0, len("Net interest margin"), term.NET_INTEREST_MARGIN)
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])
        term_fn.assert_called_once()
        arm_fn.assert_not_called()

    def test_margin_head_inside_net_interest_margin_uses_containing_term(self):
        text = "The bank's net interest margin increased."
        start = text.index("margin")
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value=proved(term.NET_INTEREST_MARGIN),
        ) as term_fn, patch.object(
            cert.arm_identity,
            "resolve_occurrence",
        ) as arm_fn:
            out = cert.evaluate(
                payload(text, start, start + len("margin"), term.NET_INTEREST_MARGIN)
            )
        self.assertTrue(out["pass"], out)
        called = term_fn.call_args.kwargs
        self.assertEqual(
            text[called["start"]:called["end"]].casefold(),
            "net interest margin",
        )
        arm_fn.assert_not_called()

    def test_margin_head_inside_initial_margin_uses_containing_term(self):
        text = "Initial margin increased."
        start = text.index("margin")
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value=proved(term.INITIAL_MARGIN),
        ) as term_fn:
            out = cert.evaluate(
                payload(text, start, start + len("margin"), term.INITIAL_MARGIN)
            )
        self.assertTrue(out["pass"], out)
        called = term_fn.call_args.kwargs
        self.assertEqual(
            text[called["start"]:called["end"]].casefold(),
            "initial margin",
        )

    def test_arm_relation_runs_after_no_containing_multiword_term(self):
        text = "The ARM's margin increased while the index was unchanged."
        start = text.index("margin")
        with patch.object(
            cert.term_identity,
            "resolve_span",
        ) as term_fn, patch.object(
            cert.arm_identity,
            "resolve_occurrence",
            return_value=proved(arm.CONCEPT_ID),
        ) as arm_fn:
            out = cert.evaluate(
                payload(text, start, start + len("margin"), arm.CONCEPT_ID)
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        term_fn.assert_not_called()
        arm_fn.assert_called_once()

    def test_different_proved_identity_remains_unknown_not_false(self):
        text = "Initial margin increased."
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value=proved(term.INITIAL_MARGIN),
        ):
            out = cert.evaluate(
                payload(text, 0, len("Initial margin"), term.NET_INTEREST_MARGIN)
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertIn("DIFFERENT_PROVED_CONTEXT_IDENTITY", out["reason"])

    def test_bare_margin_without_route_remains_unknown(self):
        text = "Margin increased."
        with patch.object(
            cert.arm_identity,
            "resolve_occurrence",
            return_value=unresolved(),
        ):
            out = cert.evaluate(
                payload(text, 0, len("Margin"), arm.CONCEPT_ID)
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["reason"],
            "NO_AUTHENTICATED_CONTEXT_IDENTITY_ROUTE_PROVED",
        )

    def test_source_authority_fail_closed_does_not_fall_through(self):
        text = "Initial margin increased."
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value={
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "SOURCE_DRIFT",
            },
        ), patch.object(cert.arm_identity, "resolve_occurrence") as arm_fn:
            out = cert.evaluate(
                payload(text, 0, len("Initial margin"), term.INITIAL_MARGIN)
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "MULTIWORD_TERM_AUTHORITY_FAIL_CLOSED")
        arm_fn.assert_not_called()

    def test_unsupported_target_fails_closed(self):
        out = cert.evaluate(
            payload("Margin increased.", 0, len("Margin"), "FINANCE::MAGIC_MARGIN")
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_CONCEPT_UNSUPPORTED", out["reason"])

    def test_dispatcher_routes_margin_context_kind(self):
        expected = {"pass": True, "predicate_truth": "TRUE"}
        with patch.object(
            dispatch,
            "evaluate_margin_context_identity",
            return_value=expected,
        ) as fn:
            out = dispatch.evaluate({
                "truth_kind": "MARGIN_CONTEXT_IDENTITY",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_true_result_never_has_terminal_or_policy_authority(self):
        text = "Initial margin increased."
        with patch.object(
            cert.term_identity,
            "resolve_span",
            return_value=proved(term.INITIAL_MARGIN),
        ):
            out = cert.evaluate(
                payload(text, 0, len("Initial margin"), term.INITIAL_MARGIN)
            )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

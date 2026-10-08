from __future__ import annotations

import unittest

from canonical.runtime.source_bound_shared_modal_and_v1 import bind_shared_modal_and


class SourceBoundSharedModalAndV1Tests(unittest.TestCase):
    def test_binds_two_exact_source_backed_obligations(self):
        text = "The report must include revenue and include expenses."
        out = bind_shared_modal_and(text)
        self.assertEqual(out["status"], "BOUND_SHARED_MODAL_AND")
        self.assertEqual(out["obligation_count"], 2)
        self.assertEqual(
            text[slice(*out["shared_prefix"]["span"])],
            out["shared_prefix"]["text"],
        )
        for row in out["obligations"]:
            self.assertEqual(
                text[slice(*row["predicate_span"])],
                row["predicate_text"],
            )
        self.assertEqual(out["obligations"][0]["predicate_text"], "include revenue")
        self.assertEqual(out["obligations"][1]["predicate_text"], "include expenses")
        self.assertTrue(out["source_span_binding_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_shared_subject_is_preserved_in_prefix(self):
        text = "The final workbook shall contain totals and contain source links."
        out = bind_shared_modal_and(text)
        self.assertEqual(out["status"], "BOUND_SHARED_MODAL_AND")
        self.assertEqual(out["shared_prefix"]["text"], "The final workbook shall")
        self.assertEqual(out["obligations"][0]["predicate_text"], "contain totals")
        self.assertEqual(out["obligations"][1]["predicate_text"], "contain source links")

    def test_or_fails_closed(self):
        out = bind_shared_modal_and("The report must include revenue or expenses.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "OR_COORDINATION_UNSUPPORTED")

    def test_multiple_and_fails_closed(self):
        out = bind_shared_modal_and(
            "The report must include revenue and include expenses and include margin."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "EXACTLY_ONE_FLAT_AND_REQUIRED")

    def test_comma_fails_closed(self):
        out = bind_shared_modal_and(
            "The report must include revenue, expenses and margin."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PUNCTUATION_COORDINATION_UNSUPPORTED")

    def test_ambiguous_pronoun_fails_closed(self):
        out = bind_shared_modal_and(
            "The report must include revenue and explain it."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "AMBIGUOUS_REFERENCE_OR_SCOPE")

    def test_nested_modal_fails_closed(self):
        out = bind_shared_modal_and(
            "The report must include revenue and should include expenses."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "EXACTLY_ONE_MODAL_REQUIRED")

    def test_semicolon_fails_closed(self):
        out = bind_shared_modal_and(
            "The report must include revenue; and include expenses."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PUNCTUATION_COORDINATION_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

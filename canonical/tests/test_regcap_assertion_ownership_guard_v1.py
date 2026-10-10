from __future__ import annotations

import unittest

from canonical.runtime.source_assertion_ownership_guard_v1 import (
    check_direct_assertion,
)
from canonical.runtime.regcap_contextual_observation_compiler_v1 import (
    compile_span,
)
from canonical.runtime import regcap_context_signature_v1 as signature
from canonical.runtime import source_aligned_regcap_context_proof_v1 as proof


DIRECT = "The cushion can be drawn down as losses are incurred."


class Tests(unittest.TestCase):
    def test_direct_complete_sentence_passes_guard(self):
        out = check_direct_assertion(
            DIRECT,
            start=0,
            end=len(DIRECT),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["safe_for_direct_semantic_projection"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_cropped_attributed_clause_is_blocked(self):
        text = "The analyst said the cushion can be drawn down as losses are incurred."
        clause = "the cushion can be drawn down as losses are incurred."
        start = text.index(clause)
        out = check_direct_assertion(
            text,
            start=start,
            end=start + len(clause),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ASSERTION_COMPLETE_SPAN_UNPROVED",
        )

    def test_quoted_sentence_is_blocked(self):
        text = '"The cushion can be drawn down as losses are incurred."'
        out = check_direct_assertion(
            text,
            start=0,
            end=len(text),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNRESOLVED__QUOTED_SCOPE")

    def test_denial_is_blocked(self):
        text = "The report denies that the cushion can be drawn down as losses are incurred."
        out = check_direct_assertion(
            text,
            start=0,
            end=len(text),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ATTRIBUTED_OR_STANCE_SCOPE",
        )

    def test_hypothetical_is_blocked(self):
        text = "If the cushion can be drawn down as losses are incurred, the policy would change."
        out = check_direct_assertion(
            text,
            start=0,
            end=len(text),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNRESOLVED__HYPOTHETICAL_OR_CONDITIONAL_SCOPE",
        )

    def test_interrogative_is_blocked(self):
        text = "Can the cushion be drawn down as losses are incurred?"
        out = check_direct_assertion(
            text,
            start=0,
            end=len(text),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNRESOLVED__INTERROGATIVE_SCOPE")

    def test_canonical_compiler_still_accepts_direct_fact(self):
        out = compile_span(DIRECT, start=0, end=len(DIRECT))
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_truth_authority"])

    def test_canonical_compiler_rejects_cropped_attribution(self):
        text = "The analyst said " + DIRECT
        start = text.index(DIRECT)
        out = compile_span(
            text,
            start=start,
            end=start + len(DIRECT),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ASSERTION_OWNERSHIP_NOT_PROVED",
        )
        self.assertFalse(out["semantic_truth_authority"])

    def test_descriptor_context_rejects_quoted_signature(self):
        text = (
            'The analyst said "the loss-absorbing cushion can be drawn down '
            'as losses are incurred."'
        )
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.compile_context(
            text,
            source_id="doc:quoted",
            start=start,
            end=start + len(phrase),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__ASSERTION_OWNERSHIP_NOT_PROVED",
        )
        self.assertFalse(out["semantic_truth_authority"])

    def test_descriptor_context_rejects_denial_signature(self):
        text = (
            "The report denies that the loss-absorbing cushion can be drawn "
            "down as losses are incurred."
        )
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.compile_context(
            text,
            source_id="doc:denied",
            start=start,
            end=start + len(phrase),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__ASSERTION_OWNERSHIP_NOT_PROVED",
        )

    def test_descriptor_context_rejects_hypothetical_signature(self):
        text = (
            "If the loss-absorbing cushion can be drawn down as losses are "
            "incurred, the policy would change."
        )
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.compile_context(
            text,
            source_id="doc:hypo",
            start=start,
            end=start + len(phrase),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__ASSERTION_OWNERSHIP_NOT_PROVED",
        )

    def test_descriptor_context_direct_signature_still_passes(self):
        text = "The loss-absorbing cushion can be drawn down as losses are incurred."
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.compile_context(
            text,
            source_id="doc:direct",
            start=start,
            end=start + len(phrase),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_truth_authority"])

    def test_source_aligned_proof_rejects_cropped_attribution(self):
        text = "The analyst said 2.5% CET1 above the regulatory minimum."
        clause = "2.5% CET1 above the regulatory minimum."
        start = text.index(clause)
        out = proof.verify_proof(
            text,
            source_id="doc:source-proof",
            claims=[{
                "claim_id": "c1",
                "kind": proof.CCOB_KIND,
                "start": start,
                "end": start + len(clause),
            }],
        )
        self.assertFalse(out["semantic_truth_authority"])
        self.assertEqual(out["accepted_claims"], [])
        self.assertEqual(
            out["rejected_claims"][0]["reason"],
            "ASSERTION_OWNERSHIP_NOT_PROVED",
        )

    def test_source_aligned_direct_fact_still_passes(self):
        text = "2.5% CET1 above the regulatory minimum."
        out = proof.verify_proof(
            text,
            source_id="doc:source-proof",
            claims=[{
                "claim_id": "c1",
                "kind": proof.CCOB_KIND,
                "start": 0,
                "end": len(text),
            }],
        )
        self.assertTrue(out["semantic_truth_authority"], out)
        self.assertEqual(len(out["accepted_claims"]), 1)

    def test_descriptor_context_unknown_wrapper_does_not_launder(self):
        text = (
            "Rumor has it that the loss-absorbing cushion can be drawn down "
            "as losses are incurred."
        )
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.compile_context(
            text,
            source_id="doc:rumor",
            start=start,
            end=start + len(phrase),
        )
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["semantic_truth_authority"])

    def test_source_aligned_unknown_wrapper_does_not_launder(self):
        text = (
            "Rumor has it that a 2.5% buffer comprised of CET1 "
            "above the regulatory minimum capital requirement."
        )
        out = proof.verify_proof(
            text,
            source_id="doc:rumor",
            claims=[{
                "claim_id": "c1",
                "kind": proof.CCOB_KIND,
                "start": 0,
                "end": len(text),
            }],
        )
        self.assertFalse(out["semantic_truth_authority"], out)
        self.assertEqual(out["accepted_claims"], [])

    def test_unsafe_context_cannot_trigger_relative_selection(self):
        text = (
            'The analyst said "the loss-absorbing cushion can be drawn down '
            'as losses are incurred."'
        )
        phrase = "loss-absorbing cushion"
        start = text.index(phrase)
        out = signature.resolve_relative(
            text,
            source_id="doc:quoted-selection",
            start=start,
            end=start + len(phrase),
            candidate_concept_ids=[
                "REGCAP::CCOB",
                "REGCAP::CCYB",
                "REGCAP::TLAC",
            ],
        )
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["relative_selection_authority"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_guard_never_grants_terminal_authority(self):
        out = check_direct_assertion(
            DIRECT,
            start=0,
            end=len(DIRECT),
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

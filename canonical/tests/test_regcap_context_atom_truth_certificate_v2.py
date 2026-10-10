import unittest

from canonical.runtime import source_aligned_regcap_context_proof_v2 as context
from canonical.runtime.regcap_context_atom_truth_certificate_v2 import (
    checked_predicate_id,
    evaluate,
)


class Tests(unittest.TestCase):
    def payload(self, text, kind, atom):
        return {
            "truth_kind": "REGCAP_CONTEXT_ATOM",
            "predicate_id": "caller-label",
            "source_text": text,
            "source_id": "doc:A",
            "start": 0,
            "end": len(text),
            "context_kind": kind,
            "target_atom_id": atom,
        }

    def test_ccob_existing_positive_phrase_still_passes(self):
        text = (
            "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
            "above the regulatory minimum capital requirement"
        )
        out = evaluate(self.payload(text, context.CCOB_KIND, context.ATOM_2_5))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_ccyb_existing_positive_phrase_still_passes(self):
        text = "the cushion is released when system-wide risk crystallises or dissipates"
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_ccyb_dissipates_only_existing_positive_phrase_still_passes(self):
        text = "this buffer is released when system wide risk dissipates"
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_tlac_existing_positive_phrase_still_passes(self):
        text = (
            "sufficient loss-absorbing and recapitalisation capacity "
            "available in resolution"
        )
        out = evaluate(self.payload(text, context.TLAC_KIND, context.ATOM_LOSS))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_explicit_gsib_existing_positive_phrase_still_passes(self):
        text = (
            "a failing G-SIB has sufficient loss-absorbing and "
            "recapitalization capacity available in resolution"
        )
        out = evaluate(self.payload(text, context.TLAC_KIND, context.ATOM_GSIB))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_negated_release_is_unknown_not_true(self):
        text = "the cushion is not released when system-wide risk dissipates"
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "BOUND_CONTEXT_NOT_CERTIFIED")

    def test_attributed_release_is_unknown_not_true(self):
        text = "analysts claim the cushion is released when system-wide risk dissipates"
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_quoted_release_is_unknown_not_true(self):
        text = '"the cushion is released when system-wide risk dissipates"'
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_hypothetical_release_is_unknown_not_true(self):
        text = "the cushion might be released when system-wide risk dissipates"
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_incomplete_context_remains_unknown(self):
        text = "a 2.5% CET1 buffer"
        out = evaluate(self.payload(text, context.CCOB_KIND, context.ATOM_2_5))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_unknown_atom_fails_closed(self):
        text = (
            "a 2.5% buffer comprised of CET1 above the regulatory minimum "
            "capital requirement"
        )
        out = evaluate(self.payload(text, context.CCOB_KIND, "CONCEPT::CCOB"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_checked_id_binds_v2_checker_and_ignores_caller_label(self):
        text = "the cushion is released when system-wide risk dissipates"
        expected = checked_predicate_id(
            source_id="doc:A",
            source_text=text,
            start=0,
            end=len(text),
            context_kind=context.CCYB_KIND,
            target_atom_id=context.ATOM_RELEASE,
        )
        out = evaluate(self.payload(text, context.CCYB_KIND, context.ATOM_RELEASE))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_id"], expected)
        self.assertEqual(out["requested_predicate_id"], "caller-label")
        self.assertFalse(out["requested_predicate_id_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

import unittest

from canonical.runtime import regcap_context_atom_truth_certificate_v2 as c


class Tests(unittest.TestCase):
    def payload(self, text, kind, atom, start=0, end=None):
        return {
            "truth_kind": "REGCAP_CONTEXT_ATOM",
            "predicate_id": "caller-label",
            "source_text": text,
            "source_id": "doc:A",
            "start": start,
            "end": len(text) if end is None else end,
            "context_kind": kind,
            "target_atom_id": atom,
        }

    def test_three_canonical_positive_families(self):
        cases = [
            (
                "This cushion is 2.5% CET1 above the regulatory minimum.",
                c.CCOB_KIND,
                c.ATOM_2_5,
            ),
            (
                "This cushion is released when system-wide risk crystallizes or dissipates.",
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
            (
                "This capacity provides loss-absorbing and recapitalization capacity "
                "available in resolution for a failing G-SIB.",
                c.TLAC_KIND,
                c.ATOM_GSIB,
            ),
        ]
        for text, kind, atom in cases:
            with self.subTest(kind=kind):
                out = c.evaluate(self.payload(text, kind, atom))
                self.assertTrue(out["pass"], out)
                self.assertEqual(out["predicate_truth"], "TRUE")
                self.assertTrue(out["semantic_truth_authority"])
                self.assertFalse(out["semantic_identity_authority"])
                self.assertFalse(out["policy_adequacy_authority"])
                self.assertFalse(out["terminal_authority"])

    def test_exact_selected_span_inside_larger_document_still_passes(self):
        clause = (
            "This capacity provides loss-absorbing and recapitalization capacity "
            "available in resolution for a failing G-SIB."
        )
        text = "prefix. " + clause + " suffix."
        start = text.index(clause)
        out = c.evaluate(
            self.payload(
                text,
                c.TLAC_KIND,
                c.ATOM_RESOLUTION,
                start=start,
                end=start + len(clause),
            )
        )
        self.assertTrue(out["pass"], out)

    def test_canonical_rejected_forms_remain_unknown(self):
        cases = [
            (
                "The cushion is released when system-wide risk dissipates.",
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
            (
                "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
                "above the regulatory minimum capital requirement",
                c.CCOB_KIND,
                c.ATOM_2_5,
            ),
            (
                "sufficient loss-absorbing and recapitalisation capacity available in resolution",
                c.TLAC_KIND,
                c.ATOM_LOSS,
            ),
            (
                "The cushion is not released when system-wide risk crystallises or dissipates.",
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
            (
                "Analysts claim the cushion is released when system-wide risk crystallises or dissipates.",
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
            (
                '"The cushion is released when system-wide risk crystallises or dissipates."',
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
            (
                "The cushion might be released when system-wide risk crystallises or dissipates.",
                c.CCYB_KIND,
                c.ATOM_RELEASE,
            ),
        ]
        for text, kind, atom in cases:
            with self.subTest(text=text):
                out = c.evaluate(self.payload(text, kind, atom))
                self.assertFalse(out["pass"], out)
                self.assertEqual(out["predicate_truth"], "UNKNOWN")
                self.assertFalse(out["semantic_truth_authority"])

    def test_context_kind_mismatch_remains_unknown(self):
        text = "This cushion is 2.5% CET1 above the regulatory minimum."
        out = c.evaluate(self.payload(text, c.CCYB_KIND, c.ATOM_RELEASE))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "CANONICAL_OBSERVATION_CONTEXT_KIND_MISMATCH")

    def test_unknown_atom_fails_closed(self):
        text = "This cushion is 2.5% CET1 above the regulatory minimum."
        out = c.evaluate(self.payload(text, c.CCOB_KIND, "CONCEPT::CCOB"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_checked_id_uses_canonical_checker_and_ignores_caller_label(self):
        text = "This cushion is released when system-wide risk crystallises or dissipates."
        expected = c.checked_predicate_id(
            source_id="doc:A",
            source_text=text,
            start=0,
            end=len(text),
            context_kind=c.CCYB_KIND,
            target_atom_id=c.ATOM_RELEASE,
        )
        out = c.evaluate(self.payload(text, c.CCYB_KIND, c.ATOM_RELEASE))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_id"], expected)
        self.assertEqual(out["requested_predicate_id"], "caller-label")
        self.assertFalse(out["requested_predicate_id_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

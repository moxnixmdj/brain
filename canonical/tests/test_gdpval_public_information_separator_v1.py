import unittest

from canonical.runtime.gdpval_public_information_separator_v1 import (
    classify_escape,
    public_projection_identifies_brain_vs_opus,
    two_publicly_indistinguishable_completions,
    verify_current_public_information_cut,
)


class Tests(unittest.TestCase):
    def test_two_worlds_share_public_projection(self):
        a, b = two_publicly_indistinguishable_completions()
        self.assertEqual(a.public_signature, b.public_signature)

    def test_two_worlds_reverse_unseen_target_order(self):
        a, b = two_publicly_indistinguishable_completions()
        self.assertEqual(a.brain_vs_opus_outcome, "BRAIN_WIN")
        self.assertEqual(b.brain_vs_opus_outcome, "OPUS_WIN")

    def test_public_projection_does_not_identify_target(self):
        self.assertFalse(public_projection_identifies_brain_vs_opus())

    def test_no_separator_keeps_cut_open(self):
        out = classify_escape()
        self.assertFalse(out["current_public_cut_broken_or_bypassed"])
        self.assertEqual(out["general_metadata_search_without_new_separator"], "NON_IDENTIFYING")

    def test_e_explicit_relation_breaks_cut(self):
        out = classify_escape(explicit_owner_relation_bound=True)
        self.assertIn("E_EXPLICIT_OWNER_RELATION", out["selected_escape_classes"])

    def test_m_restricted_class_breaks_cut_only_when_proved(self):
        open_out = classify_escape(proved_owner_class_excludes_opus_world=False)
        closed_out = classify_escape(proved_owner_class_excludes_opus_world=True)
        self.assertFalse(open_out["current_public_cut_broken_or_bypassed"])
        self.assertIn("M_PROVED_RESTRICTED_OWNER_CLASS", closed_out["selected_escape_classes"])

    def test_u_exact_exchangeability_bypasses_hidden_relation(self):
        out = classify_escape(exact_exchangeable_owner_visible_input_law=True)
        self.assertIn("U_EXACT_EXCHANGEABLE_INPUT_LAW_BYPASS", out["selected_escape_classes"])

    def test_future_stronger_sound_bypass_is_not_forbidden(self):
        out = classify_escape(stronger_sound_bypass_bound=True)
        self.assertIn("S_FUTURE_STRONGER_SOUND_BYPASS", out["selected_escape_classes"])

    def test_current_cut_verifier(self):
        out = verify_current_public_information_cut()
        self.assertTrue(out["current_public_facts_non_identifying"])
        self.assertTrue(out["same_public_projection"])
        self.assertTrue(out["opposite_unseen_brain_vs_opus_order"])

    def test_never_grants_terminal_credit(self):
        self.assertEqual(verify_current_public_information_cut()["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()

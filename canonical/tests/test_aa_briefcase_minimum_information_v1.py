from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_minimum_information_v1 as m


SUBJECT = "a" * 64


def cert(cid, components, cost=1, subject=SUBJECT, relation="CONSERVATIVE_DOMINANCE"):
    return {
        "id": cid,
        "verified": True,
        "causal": True,
        "generalization_bound": True,
        "subject_bound": True,
        "brain_owned_donor_free": True,
        "reference_evidence_bound": True,
        "terminal_predicate_entailment_bound": True,
        "relation_scope_complete": True,
        "target_authority_blob_sha": m.TARGET_AUTHORITY_BLOB_SHA,
        "terminal_predicate": m.TERMINAL_PREDICATE,
        "typed_relation": relation,
        "subject_sha256": subject,
        "covers_components": components,
        "action_cost": cost,
    }


class AABriefcaseMinimumInformationV1Tests(unittest.TestCase):
    def test_integrated_certificate_closes_capability_relation(self):
        out = m.minimum_proof_carrying_information_set([
            cert("ALL", sorted(m.CAPABILITY_COMPONENTS), 1)
        ])
        self.assertTrue(out["capability_relation_proved"])
        self.assertEqual(out["selected_certificate_ids"], ["ALL"])
        self.assertFalse(out["literal_aa_briefcase_elo_ge_1822_proved"])

    def test_minimum_action_cost_basis_selected(self):
        out = m.minimum_proof_carrying_information_set([
            cert("EXPENSIVE", sorted(m.CAPABILITY_COMPONENTS), 9),
            cert("QUALITY", [
                "TASK_SPECIFIC_REQUIREMENT_AND_RUBRIC_SATISFACTION",
                "ANALYTICAL_QUALITY",
                "PRESENTATION_QUALITY",
            ], 1),
            cert("RELIABILITY", ["RELIABILITY_ACROSS_THE_RELEVANT_PROFESSIONAL_WORK_SCOPE"], 1),
        ])
        self.assertEqual(out["selected_certificate_ids"], ["QUALITY", "RELIABILITY"])
        self.assertEqual(out["total_action_cost"], 2)

    def test_mixed_subject_evidence_cannot_compose(self):
        out = m.minimum_proof_carrying_information_set([
            cert("QUALITY", [
                "TASK_SPECIFIC_REQUIREMENT_AND_RUBRIC_SATISFACTION",
                "ANALYTICAL_QUALITY",
                "PRESENTATION_QUALITY",
            ], 1, "a" * 64),
            cert("RELIABILITY", ["RELIABILITY_ACROSS_THE_RELEVANT_PROFESSIONAL_WORK_SCOPE"], 1, "b" * 64),
        ])
        self.assertFalse(out["capability_relation_proved"])

    def test_scheduling_heuristic_relation_rejected(self):
        out = m.minimum_proof_carrying_information_set([
            cert("HEURISTIC", sorted(m.CAPABILITY_COMPONENTS), 0, relation="SCHEDULING_HEURISTIC_ONLY")
        ])
        self.assertFalse(out["capability_relation_proved"])
        self.assertIn("NONCREDIT_RELATION", out["rejected_candidates"][0]["reason"])

    def test_target_authority_mismatch_rejected(self):
        bad = cert("BAD_TARGET", sorted(m.CAPABILITY_COMPONENTS), 0)
        bad["target_authority_blob_sha"] = "0" * 40
        out = m.minimum_proof_carrying_information_set([bad])
        self.assertFalse(out["capability_relation_proved"])
        self.assertIn("TARGET_AUTHORITY_MISMATCH", out["rejected_candidates"][0]["reason"])

    def test_external_runtime_cognition_cannot_receive_brain_credit(self):
        bad = cert("OUTSOURCED", sorted(m.CAPABILITY_COMPONENTS), 0)
        bad["brain_owned_donor_free"] = False
        out = m.minimum_proof_carrying_information_set([bad])
        self.assertFalse(out["capability_relation_proved"])

    def test_terminal_entailment_is_mandatory(self):
        bad = cert("NO_ENTAILMENT", sorted(m.CAPABILITY_COMPONENTS), 0)
        bad["terminal_predicate_entailment_bound"] = False
        out = m.minimum_proof_carrying_information_set([bad])
        self.assertFalse(out["capability_relation_proved"])

    def test_incomplete_component_basis_remains_open(self):
        out = m.minimum_proof_carrying_information_set([
            cert("ONLY_ANALYSIS", ["ANALYTICAL_QUALITY"], 0)
        ])
        self.assertFalse(out["capability_relation_proved"])
        self.assertIn("PRESENTATION_QUALITY", out["missing_components"])

    def test_current_high_authority_probe_fails_closed(self):
        out = m.current_authority_probe()
        self.assertEqual(out["status"], "OPEN__NO_COMPLETE_SAME_SUBJECT_PROOF_INFORMATION_SET")
        self.assertFalse(out["capability_relation_proved"])
        self.assertFalse(out["literal_aa_briefcase_elo_ge_1822_proved"])

    def test_capability_relation_never_backpropagates_literal_score(self):
        out = m.minimum_proof_carrying_information_set([
            cert("ALL", sorted(m.CAPABILITY_COMPONENTS), 0, relation="EXACT_EQUIVALENCE")
        ])
        self.assertTrue(out["capability_relation_proved"])
        self.assertFalse(out["literal_aa_briefcase_elo_ge_1822_proved"])
        self.assertIn("DOES_NOT_CREATE_AN_OFFICIAL_AA_BRIEFCASE_SCORE", out["hard_nonclaim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

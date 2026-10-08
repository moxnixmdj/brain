import unittest

from canonical.runtime.gdpval_necessary_preference_certificate_v1 import verify

H = "a" * 64


def envelope(**overrides):
    out = {
        "published_owner_contract_bound": True,
        "same_task_pairwise_semantics_bound": True,
        "anonymized_ab_semantics_bound": True,
        "all_reference_and_submission_context_bound": True,
        "presentation_transform_bound_or_sound_overapproximation": True,
        "true_owner_relation_contained_in_envelope": True,
        "owner_contract_evidence_sha256": H,
        "envelope_containment_evidence_sha256": H,
        "containment_proof_class": "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
        "containment_independent_verification_sha256": H,
    }
    out.update(overrides)
    return out


def task(i, outcome="BRAIN_WEAKLY_DOMINATES", cover=True, evidence=H):
    return {
        "task_id": f"task-{i}",
        "task_relevant_dimension_cover_sound": cover,
        "dimension_cover_evidence_sha256": H,
        "dominance_entails_noninferiority_over_envelope": True,
        "entailment_evidence_sha256": H,
        "dimensions": [
            {
                "dimension_id": "task_response",
                "outcome": outcome,
                "evidence_sha256": evidence,
            }
        ],
    }


def manifest():
    return {
        "task_count": 220,
        "preference_envelope": envelope(),
        "tasks": [task(i) for i in range(220)],
    }


class GDPValNecessaryPreferenceCertificateV1Tests(unittest.TestCase):
    def test_complete_scope_passes_as_logic_certificate_only(self):
        out = verify(manifest())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["passed_tasks"], 220)
        self.assertFalse(out["exact_owner_prompt_required"])
        self.assertEqual(out["gdpval_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_envelope_containment_fails_closed(self):
        m = manifest()
        m["preference_envelope"]["true_owner_relation_contained_in_envelope"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "OWNER_COMPATIBLE_PREFERENCE_ENVELOPE_NOT_SOUNDLY_BOUND",
        )

    def test_missing_envelope_evidence_fails_closed(self):
        m = manifest()
        m["preference_envelope"]["envelope_containment_evidence_sha256"] = None
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "OWNER_COMPATIBLE_PREFERENCE_ENVELOPE_EVIDENCE_MISSING",
        )

    def test_public_methodology_only_cannot_certify_containment(self):
        m = manifest()
        m["preference_envelope"]["containment_proof_class"] = "PUBLIC_METHODOLOGY_ONLY"
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ENVELOPE_CONTAINMENT_PROOF_CLASS_INADMISSIBLE")

    def test_historical_v1_prompt_cannot_be_carried_forward(self):
        m = manifest()
        m["preference_envelope"]["containment_proof_class"] = "HISTORICAL_V1_PROMPT_CARRYFORWARD"
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ENVELOPE_CONTAINMENT_PROOF_CLASS_INADMISSIBLE")

    def test_unverified_reconstructed_grader_cannot_certify_containment(self):
        m = manifest()
        m["preference_envelope"]["containment_proof_class"] = "UNVERIFIED_RECONSTRUCTED_GRADER"
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ENVELOPE_CONTAINMENT_PROOF_CLASS_INADMISSIBLE")

    def test_unknown_proof_class_fails_closed(self):
        m = manifest()
        m["preference_envelope"]["containment_proof_class"] = "MAGIC"
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ENVELOPE_CONTAINMENT_PROOF_CLASS_UNBOUND")

    def test_independent_containment_verification_is_required(self):
        m = manifest()
        m["preference_envelope"]["containment_independent_verification_sha256"] = None
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "ENVELOPE_CONTAINMENT_INDEPENDENT_VERIFICATION_MISSING",
        )

    def test_one_surviving_preference_discriminator_blocks(self):
        m = manifest()
        m["tasks"][17]["dimensions"][0]["outcome"] = "UNRESOLVED"
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "NECESSARY_PREFERENCE_NOT_PROVED_FOR_FULL_SCOPE",
        )
        self.assertEqual(out["unresolved_task_count"], 1)
        self.assertEqual(out["unresolved"][0]["task_id"], "task-17")

    def test_top_certificate_is_accepted(self):
        m = manifest()
        m["tasks"][5]["dimensions"][0]["outcome"] = "BRAIN_TOP"
        out = verify(m)
        self.assertTrue(out["pass"], out)

    def test_missing_dimension_cover_blocks_only_that_task(self):
        m = manifest()
        m["tasks"][9]["task_relevant_dimension_cover_sound"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["unresolved_task_count"], 1)
        self.assertEqual(out["unresolved"][0]["kind"], "DIMENSION_COVER_NOT_PROVED")

    def test_missing_entailment_blocks_only_that_task(self):
        m = manifest()
        m["tasks"][7]["dominance_entails_noninferiority_over_envelope"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["unresolved"][0]["kind"],
            "DOMINANCE_TO_OWNER_ENVELOPE_ENTAILMENT_NOT_PROVED",
        )

    def test_missing_dimension_evidence_blocks(self):
        m = manifest()
        m["tasks"][11]["dimensions"][0]["evidence_sha256"] = None
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["unresolved"][0]["kind"],
            "DOMINANCE_EVIDENCE_MISSING_OR_UNADDRESSED",
        )

    def test_not_exactly_220_tasks_is_rejected(self):
        m = manifest()
        m["tasks"] = m["tasks"][:-1]
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TASK_LIST_NOT_220")

    def test_duplicate_task_id_is_rejected(self):
        m = manifest()
        m["tasks"][1]["task_id"] = m["tasks"][0]["task_id"]
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TASK_ID_INVALID_OR_DUPLICATE")


if __name__ == "__main__":
    unittest.main()

import unittest
from canonical.runtime.gdpval_evaluator_facing_quotient_u_route_v1 import verify

H = "a" * 40


def quotient(**overrides):
    out = {
        "all_load_bearing_owner_evaluator_inputs_factor_through_quotient": True,
        "model_identity_not_available_outside_bound_quotient": True,
        "owner_randomization_and_judge_randomness_in_state_boundary": True,
        "random_ab_assignment_symmetric": True,
        "task_reference_context_bound": True,
        "owner_parsing_and_presentation_transform_bound": True,
        "quotient_completeness_evidence_sha": H,
        "anonymization_symmetry_evidence_sha": H,
        "presentation_transform_evidence_sha": H,
    }
    out.update(overrides)
    return out


def task(i, brain=None, opus=None):
    law = {"q0": "1/3", "q1": "2/3"}
    return {
        "task_id": f"task-{i}",
        "brain_quotient_law_exact": brain or law,
        "opus55_quotient_law_exact": opus or law,
    }


def manifest():
    return {
        "task_count": 220,
        "evaluator_facing_quotient": quotient(),
        "tasks": [task(i) for i in range(220)],
    }


class GDPValEvaluatorFacingQuotientURouteV1Tests(unittest.TestCase):
    def test_equal_220_quotient_laws_pass_conditionally(self):
        out = verify(manifest())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["full_private_trajectory_law_equality_required"])
        self.assertFalse(out["exact_hidden_grading_prompt_required_for_u_route"])
        self.assertEqual(out["gdpval_credit_delta"], 0)

    def test_missing_quotient_factorization_fails_closed(self):
        m = manifest()
        m["evaluator_facing_quotient"]["all_load_bearing_owner_evaluator_inputs_factor_through_quotient"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVALUATOR_FACING_QUOTIENT_NOT_PROVED_COMPLETE")

    def test_hidden_model_identity_channel_fails_closed(self):
        m = manifest()
        m["evaluator_facing_quotient"]["model_identity_not_available_outside_bound_quotient"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVALUATOR_FACING_QUOTIENT_NOT_PROVED_COMPLETE")

    def test_missing_symmetry_receipt_fails_closed(self):
        m = manifest()
        m["evaluator_facing_quotient"]["anonymization_symmetry_evidence_sha"] = None
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVALUATOR_FACING_QUOTIENT_EVIDENCE_MISSING")

    def test_one_task_law_shift_blocks(self):
        m = manifest()
        m["tasks"][17]["brain_quotient_law_exact"] = {"q0": "1/2", "q1": "1/2"}
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVALUATOR_FACING_QUOTIENT_LAWS_NOT_EQUAL")
        self.assertEqual(out["unequal_task_count"], 1)
        self.assertEqual(out["first_unequal"]["task_id"], "task-17")

    def test_invalid_probability_mass_rejected(self):
        m = manifest()
        m["tasks"][3]["opus55_quotient_law_exact"] = {"q0": "1/3"}
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "OPUS55_QUOTIENT_LAW_INVALID_OR_UNBOUND")

    def test_exactly_220_required(self):
        m = manifest()
        m["tasks"] = m["tasks"][:-1]
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TASK_LIST_NOT_220")

    def test_duplicate_task_id_rejected(self):
        m = manifest()
        m["tasks"][1]["task_id"] = m["tasks"][0]["task_id"]
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TASK_ID_INVALID_OR_DUPLICATE")

    def test_target_law_cannot_be_replaced_by_aggregate_elo(self):
        m = manifest()
        del m["tasks"][0]["opus55_quotient_law_exact"]
        m["tasks"][0]["opus55_aggregate_elo"] = 1866
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "OPUS55_QUOTIENT_LAW_INVALID_OR_UNBOUND")

    def test_randomization_must_be_inside_complete_state_boundary(self):
        m = manifest()
        m["evaluator_facing_quotient"]["owner_randomization_and_judge_randomness_in_state_boundary"] = False
        out = verify(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVALUATOR_FACING_QUOTIENT_NOT_PROVED_COMPLETE")


if __name__ == "__main__":
    unittest.main()

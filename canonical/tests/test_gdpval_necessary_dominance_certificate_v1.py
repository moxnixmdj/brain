import unittest

from canonical.runtime.gdpval_necessary_dominance_certificate_v1 import SCHEMA, verify_certificate


def task(i: int):
    return {
        "task_id": f"task-{i:03d}",
        "mode": "DIRECT_DOMINANCE",
        "owner_compatible_counterexample_exists": False,
        "owner_compatible_counterexample_search_complete": True,
        "counterexample_search_receipts": [f"receipt:ce:{i}"],
        "dimension_basis_scope_complete": True,
        "basis_completeness_receipts": [f"receipt:basis:{i}"],
        "necessary_preference_proved": True,
        "dimensions": [
            {
                "dimension_id": "task_response",
                "relation": "BRAIN_BETTER",
                "evidence_refs": [f"receipt:dom:{i}"],
            }
        ],
    }


def payload():
    return {
        "schema": SCHEMA,
        "owner_contract": {
            "evaluation": "GDPval-AA v2.1",
            "task_count": 220,
            "blind_pairwise": True,
            "same_task_for_both_submissions": True,
            "same_reference_files_for_both_submissions": True,
            "anonymized_submission_order": True,
            "judge_context_includes_initial_task": True,
            "judge_context_includes_all_reference_files": True,
            "judge_context_includes_all_submission_files": True,
            "document_files_parsed_as_text_and_images": True,
            "grading_question_semantics": "WHICH_SUBMISSION_BETTER_RESPONDS_TO_THE_TASK",
            "evidence_refs": ["owner-methodology-receipt"],
        },
        "owner_compatible_preference_envelope": {
            "status": "PROVED_SOUND_OVERAPPROXIMATION",
            "contains_true_owner_relation": True,
            "monotone_task_response_order": True,
            "proof_receipts": ["envelope-proof-receipt"],
            "falsifier_classes": [
                "hidden_non_task_response_criterion",
                "non_monotone_owner_preference",
            ],
        },
        "tasks": [task(i) for i in range(220)],
        "independent_verification": {
            "status": "PASS",
            "receipts": ["independent-replay-receipt"],
        },
    }


class Tests(unittest.TestCase):
    def test_complete_certificate_structurally_passes(self):
        out = verify_certificate(payload())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["hidden_owner_relation_required"])
        self.assertFalse(out["exact_owner_prompt_required"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_task_fails(self):
        p = payload()
        p["tasks"].pop()
        self.assertEqual(verify_certificate(p)["reason"], "TASK_POPULATION_NOT_220")

    def test_duplicate_task_fails(self):
        p = payload()
        p["tasks"][219]["task_id"] = p["tasks"][0]["task_id"]
        self.assertEqual(verify_certificate(p)["reason"], "DUPLICATE_TASK_ID")

    def test_owner_presentation_contract_is_load_bearing(self):
        p = payload()
        p["owner_contract"]["judge_context_includes_all_reference_files"] = False
        self.assertEqual(
            verify_certificate(p)["reason"],
            "OWNER_ALL_REFERENCE_FILES_CONTEXT_NOT_BOUND",
        )

    def test_unproved_envelope_fails(self):
        p = payload()
        p["owner_compatible_preference_envelope"]["contains_true_owner_relation"] = False
        self.assertEqual(
            verify_certificate(p)["reason"],
            "TRUE_OWNER_RELATION_CONTAINMENT_NOT_PROVED",
        )

    def test_one_opus_win_counterexample_fails(self):
        p = payload()
        p["tasks"][17]["owner_compatible_counterexample_exists"] = True
        self.assertIn(
            "OWNER_COMPATIBLE_OPUS_WIN_COUNTEREXAMPLE",
            verify_certificate(p)["reason"],
        )

    def test_open_counterexample_search_fails(self):
        p = payload()
        p["tasks"][17]["owner_compatible_counterexample_search_complete"] = False
        self.assertIn("COUNTEREXAMPLE_SEARCH_OPEN", verify_certificate(p)["reason"])

    def test_uncertified_dimension_fails(self):
        p = payload()
        p["tasks"][3]["dimensions"][0]["relation"] = "UNKNOWN"
        self.assertIn("RELATION_NOT_CERTIFIED", verify_certificate(p)["reason"])

    def test_top_requires_proved_attained_bound(self):
        p = payload()
        d = p["tasks"][4]["dimensions"][0]
        p["tasks"][4]["mode"] = "TOP_CERTIFICATE"
        d["relation"] = "TOP"
        d["upper_bound_proved"] = True
        d["brain_attains_upper_bound"] = False
        self.assertIn("TOP_NOT_ATTAINED", verify_certificate(p)["reason"])

    def test_basis_must_be_scope_complete(self):
        p = payload()
        p["tasks"][9]["dimension_basis_scope_complete"] = False
        self.assertIn(
            "DIMENSION_BASIS_NOT_SCOPE_COMPLETE",
            verify_certificate(p)["reason"],
        )

    def test_independent_verification_required(self):
        p = payload()
        p["independent_verification"]["status"] = "OPEN"
        self.assertEqual(
            verify_certificate(p)["reason"],
            "INDEPENDENT_VERIFICATION_NOT_PASS",
        )

    def test_runtime_never_grants_terminal_credit(self):
        out = verify_certificate(payload())
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()

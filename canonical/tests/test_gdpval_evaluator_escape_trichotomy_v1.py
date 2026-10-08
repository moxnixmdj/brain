import unittest

from canonical.runtime.gdpval_evaluator_escape_trichotomy_v1 import route


def base():
    return {"owner_contract": {"public_contract_bound": True, "task_count": 220}}


class Tests(unittest.TestCase):
    def test_open_is_unresolved(self):
        self.assertIn("UNRESOLVED", route(base())["status"])

    def test_e_explicit_relation_passes_only_with_220(self):
        p = base()
        p["explicit_relation"] = {
            "status": "PROVED_EXTENSIONALLY_EQUIVALENT",
            "proof_receipts": ["proof"],
            "task_outcome_receipts": [str(i) for i in range(220)],
            "any_opus_preferred_task": False,
            "all_tasks_brain_win_or_tie": True,
        }
        self.assertEqual(route(p)["selected_route"], "E_EXPLICIT_OWNER_RELATION")

    def test_e_counterexample_fails(self):
        p = base()
        p["explicit_relation"] = {
            "status": "PROVED_EXTENSIONALLY_EQUIVALENT",
            "proof_receipts": ["proof"],
            "task_outcome_receipts": [str(i) for i in range(220)],
            "any_opus_preferred_task": True,
            "all_tasks_brain_win_or_tie": True,
        }
        self.assertFalse(route(p)["pass"])

    def test_m_proved_monotone_class_passes(self):
        p = base()
        p["monotone_hidden_class"] = {
            "status": "PROVED_OWNER_RELATION_IN_MONOTONE_CLASS",
            "semantic_proof_receipts": ["proof"],
            "task_dominance_receipts": [str(i) for i in range(220)],
            "owner_compatible_counterexample_exists": False,
            "all_tasks_universal_monotone_noninferiority": True,
        }
        self.assertEqual(route(p)["selected_route"], "M_PROVED_MONOTONE_HIDDEN_CLASS")

    def test_m_cannot_be_inferred_from_public_wording(self):
        p = base()
        p["monotone_hidden_class"] = {
            "status": "PUBLIC_WORDING_SUGGESTS_MONOTONE",
            "semantic_proof_receipts": ["proof"],
            "task_dominance_receipts": [str(i) for i in range(220)],
            "all_tasks_universal_monotone_noninferiority": True,
        }
        self.assertFalse(route(p)["pass"])

    def test_u_exact_input_law_equality_passes_without_hidden_semantics(self):
        p = base()
        p["arbitrary_hidden_equality"] = {
            "status": "PROVED_EXACT_OWNER_VISIBLE_INPUT_LAW_EQUALITY",
            "equality_proof_receipts": ["proof"],
            "task_equality_receipts": [str(i) for i in range(220)],
            "same_task_and_references": True,
            "same_owner_parser_transform": True,
            "same_anonymization_law": True,
            "same_judge_sampling_law": True,
            "brain_opus_owner_visible_submission_law_equal": True,
        }
        self.assertEqual(
            route(p)["selected_route"],
            "U_ARBITRARY_HIDDEN_EXACT_INPUT_LAW_EQUALITY",
        )

    def test_u_partial_equality_fails(self):
        p = base()
        p["arbitrary_hidden_equality"] = {
            "status": "PROVED_EXACT_OWNER_VISIBLE_INPUT_LAW_EQUALITY",
            "equality_proof_receipts": ["proof"],
            "task_equality_receipts": [str(i) for i in range(220)],
            "same_task_and_references": True,
            "same_owner_parser_transform": True,
            "same_anonymization_law": True,
            "same_judge_sampling_law": True,
            "brain_opus_owner_visible_submission_law_equal": False,
        }
        self.assertFalse(route(p)["pass"])

    def test_219_receipts_fail(self):
        p = base()
        p["arbitrary_hidden_equality"] = {
            "status": "PROVED_EXACT_OWNER_VISIBLE_INPUT_LAW_EQUALITY",
            "equality_proof_receipts": ["proof"],
            "task_equality_receipts": [str(i) for i in range(219)],
            "same_task_and_references": True,
            "same_owner_parser_transform": True,
            "same_anonymization_law": True,
            "same_judge_sampling_law": True,
            "brain_opus_owner_visible_submission_law_equal": True,
        }
        self.assertEqual(route(p)["reason"], "U_TASK_EQUALITY_RECEIPTS_NOT_220")

    def test_router_never_grants_terminal_credit(self):
        self.assertEqual(route(base())["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()

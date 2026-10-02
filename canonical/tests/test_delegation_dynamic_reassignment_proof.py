from __future__ import annotations

import copy
import inspect
import json
import unittest

from canonical.runtime import delegation_dynamic_reassignment_candidate as candidate
from canonical.runtime import delegation_dynamic_reassignment_proof as proof


class DynamicDelegationReassignmentTests(unittest.TestCase):
    def test_oracle_is_never_candidate_visible(self):
        case = proof.generate_case(4242, 0)
        initial = proof.public_initial(case)
        update = proof.public_after_receipt(case)
        self.assertNotIn("_oracle", initial)
        self.assertNotIn("_oracle", update)
        self.assertNotIn("oracle", json.dumps(update).lower())
        self.assertNotIn("expected_assignment", json.dumps(update).lower())

    def test_candidate_does_not_import_evaluator(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("delegation_dynamic_reassignment_proof", src)
        self.assertNotIn("_oracle", src)

    def test_all_three_receipt_classes_pass(self):
        out = proof.run_batch(777, 30, candidate.solve_initial, candidate.solve_after_receipt)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(set(out["by_class"]), {
            "STEP_UNAVAILABLE", "WORKER_CAPABILITY_REMOVED", "WORKER_UNAVAILABLE"
        })

    def test_ignoring_worker_receipt_fails(self):
        case = proof.generate_case(888, 0)  # WORKER_UNAVAILABLE
        first = candidate.solve_initial(proof.public_initial(case))
        bad = copy.deepcopy(first)
        receipt = case["_oracle"]["receipt"]
        bad["receipt_id"] = receipt["receipt_id"]
        bad["revision_provenance"] = {
            "kind": receipt["kind"],
            "entity_id": receipt["entity_id"],
            "completed_task_ids": receipt["completed_task_ids"],
        }
        self.assertFalse(proof.score_episode(case, first, bad)["pass"])

    def test_replaying_completed_work_fails(self):
        case = proof.generate_case(999, 1)  # STEP_UNAVAILABLE
        first = candidate.solve_initial(proof.public_initial(case))
        revised = candidate.solve_after_receipt(proof.public_after_receipt(case), first)
        revised = copy.deepcopy(revised)
        revised["task_ids"].insert(0, case["_oracle"]["receipt"]["completed_task_ids"][0])
        self.assertEqual(proof.score_episode(case, first, revised)["reason"], "COMPLETED_WORK_REPLAYED")

    def test_missing_receipt_provenance_fails(self):
        case = proof.generate_case(1001, 2)
        first = candidate.solve_initial(proof.public_initial(case))
        revised = candidate.solve_after_receipt(proof.public_after_receipt(case), first)
        revised = copy.deepcopy(revised)
        revised["receipt_id"] = ""
        self.assertEqual(proof.score_episode(case, first, revised)["reason"], "RECEIPT_PROVENANCE_MISSING")

    def test_nonoptimal_backup_fails(self):
        case = proof.generate_case(1002, 1)  # STEP_UNAVAILABLE triggers B2 backup.
        first = candidate.solve_initial(proof.public_initial(case))
        revised = candidate.solve_after_receipt(proof.public_after_receipt(case), first)
        bad = copy.deepcopy(revised)
        bad["task_ids"] = list(reversed(bad["task_ids"]))
        self.assertFalse(proof.score_episode(case, first, bad)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

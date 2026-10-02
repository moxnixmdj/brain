from __future__ import annotations

import unittest

from canonical.runtime import delegation_whole_scope_candidate_v2 as v2
from canonical.runtime import delegation_whole_scope_proof_v2 as proof
from canonical.runtime import delegation_receipt_history_candidate_v3 as v3


CORE = (
    "status", "task_ids", "dependencies", "assignment", "waves", "wave_count",
    "total_cost", "evidence_owners", "fanin_evidence", "terminal_evidence",
    "resource_capacities",
)


def core(row):
    return {k: row.get(k) for k in CORE}


class DelegationReceiptHistoryV3Tests(unittest.TestCase):
    def test_v3_is_single_receipt_behavior_preserving_over_v2_preflight(self):
        for ordinal in range(180):
            case = proof.generate_case(81277, ordinal)
            initial_public = proof.public_initial(case)
            receipt_public = proof.public_after_receipt(case)

            v2_initial = v2.solve_initial(initial_public)
            v3_initial = v3.solve_initial(initial_public)
            self.assertEqual(core(v3_initial), core(v2_initial), ordinal)

            v2_revised = v2.solve_after_receipt(receipt_public, v2_initial)
            v3_revised = v3.solve_after_receipt(receipt_public, v3_initial)
            self.assertEqual(core(v3_revised), core(v2_revised), ordinal)
            self.assertTrue(proof.score_episode(case, v3_initial, v3_revised)["pass"], ordinal)

    def _task(self):
        return {
            "initial_facts": [],
            "required_outputs": ["DONE"],
            "resource_capacities": {},
            "steps": [{
                "id": "S",
                "requires": [],
                "produces": ["DONE"],
                "capability": "C",
                "cost": 1,
                "writes": [],
                "evidence_outputs": ["E"],
            }],
            "workers": [
                {"id": "W1", "capabilities": ["C"]},
                {"id": "W2", "capabilities": ["C"]},
                {"id": "W3", "capabilities": ["C"]},
            ],
        }

    def _receipt(self, rid, kind, entity, **extra):
        out = {
            "receipt_id": rid,
            "kind": kind,
            "entity_id": entity,
            "completed_task_ids": [],
        }
        out.update(extra)
        return out

    def test_two_worker_unavailability_receipts_do_not_resurrect_first_failure(self):
        task = self._task()
        initial = v3.solve_initial({"task": task})
        self.assertEqual(initial["assignment"]["S"], "W1")

        r1 = self._receipt("R1", "WORKER_UNAVAILABLE", "W1")
        p1 = v3.solve_after_receipt({"task": task, "receipt": r1}, initial)
        self.assertEqual(p1["assignment"]["S"], "W2")

        r2 = self._receipt("R2", "WORKER_UNAVAILABLE", "W2")
        p2 = v3.solve_after_receipt({"task": task, "receipt": r2}, p1)
        self.assertEqual(p2["assignment"]["S"], "W3")
        self.assertEqual(p2["receipt_history_ids"], ["R1", "R2"])

        # V2's single-current-receipt semantics resurrect W1 here. This is the
        # concrete counterexample that makes the V3 repair load-bearing.
        v2_p2 = v2.solve_after_receipt({"task": task, "receipt": r2}, p1)
        self.assertEqual(v2_p2["assignment"]["S"], "W1")

    def test_capability_removal_persists_across_later_unrelated_receipt(self):
        task = self._task()
        initial = v3.solve_initial({"task": task})
        r1 = self._receipt("R1", "WORKER_CAPABILITY_REMOVED", "W1", capability="C")
        p1 = v3.solve_after_receipt({"task": task, "receipt": r1}, initial)
        self.assertEqual(p1["assignment"]["S"], "W2")

        r2 = self._receipt("R2", "WORKER_UNAVAILABLE", "W2")
        p2 = v3.solve_after_receipt({"task": task, "receipt": r2}, p1)
        self.assertEqual(p2["assignment"]["S"], "W3")

    def test_unknown_receipt_kind_fails_closed(self):
        task = self._task()
        initial = v3.solve_initial({"task": task})
        bad = self._receipt("RX", "MAGIC_RECOVERY", "W1")
        with self.assertRaises(v3.DelegationReceiptHistoryError):
            v3.solve_after_receipt({"task": task, "receipt": bad}, initial)

    def test_duplicate_receipt_id_fails_closed(self):
        task = self._task()
        initial = v3.solve_initial({"task": task})
        r1 = self._receipt("R1", "WORKER_UNAVAILABLE", "W1")
        p1 = v3.solve_after_receipt({"task": task, "receipt": r1}, initial)
        with self.assertRaises(v3.DelegationReceiptHistoryError):
            v3.solve_after_receipt({"task": task, "receipt": r1}, p1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

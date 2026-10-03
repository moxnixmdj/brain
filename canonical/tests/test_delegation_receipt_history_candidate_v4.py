from __future__ import annotations

import unittest

from canonical.runtime import delegation_whole_scope_candidate_v2 as v2
from canonical.runtime import delegation_whole_scope_proof_v2 as proof
from canonical.runtime import delegation_receipt_history_candidate_v4 as v4


CORE = (
    "status", "task_ids", "dependencies", "assignment", "waves", "wave_count",
    "total_cost", "evidence_owners", "fanin_evidence", "terminal_evidence",
    "resource_capacities",
)


def core(row):
    return {k: row.get(k) for k in CORE}


def task():
    return {
        "initial_facts": [],
        "required_outputs": ["DONE"],
        "resource_capacities": {"R": 2},
        "steps": [{
            "id": "S",
            "requires": [],
            "produces": ["DONE"],
            "capability": "C",
            "cost": 1,
            "writes": ["R"],
            "evidence_outputs": ["E"],
        }],
        "workers": [
            {"id": "W1", "capabilities": ["C", "D"]},
            {"id": "W2", "capabilities": ["C"]},
            {"id": "W3", "capabilities": ["C"]},
        ],
    }


def receipt(rid, kind, entity, **extra):
    row = {
        "receipt_id": rid,
        "kind": kind,
        "entity_id": entity,
        "completed_task_ids": [],
    }
    row.update(extra)
    return row


class DelegationReceiptHistoryV4Tests(unittest.TestCase):
    def test_preserves_all_180_v2_single_receipt_cases(self):
        for ordinal in range(180):
            case = proof.generate_case(81277, ordinal)
            initial_public = proof.public_initial(case)
            update_public = proof.public_after_receipt(case)
            v2_initial = v2.solve_initial(initial_public)
            v4_initial = v4.solve_initial(initial_public)
            self.assertEqual(core(v4_initial), core(v2_initial), ordinal)
            v2_update = v2.solve_after_receipt(update_public, v2_initial)
            v4_update = v4.solve_after_receipt(update_public, v4_initial)
            self.assertEqual(core(v4_update), core(v2_update), ordinal)
            self.assertTrue(
                proof.score_episode(case, v4_initial, v4_update)["pass"], ordinal
            )

    def test_two_unavailability_receipts_never_resurrect_first_worker(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R1", "WORKER_UNAVAILABLE", "W1")},
            p0,
        )
        p2 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R2", "WORKER_UNAVAILABLE", "W2")},
            p1,
        )
        self.assertEqual(p1["assignment"]["S"], "W2")
        self.assertEqual(p2["assignment"]["S"], "W3")
        self.assertEqual(p2["receipt_history_ids"], ["R1", "R2"])

    def test_repeated_unavailability_is_idempotent(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R1", "WORKER_UNAVAILABLE", "W1")},
            p0,
        )
        p2 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R2", "WORKER_UNAVAILABLE", "W1")},
            p1,
        )
        self.assertEqual(p1["assignment"]["S"], "W2")
        self.assertEqual(p2["assignment"]["S"], "W2")

    def test_capability_removal_is_absorbing_even_after_worker_unavailable(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R1", "WORKER_UNAVAILABLE", "W1")},
            p0,
        )
        p2 = v4.solve_after_receipt(
            {
                "task": t,
                "receipt": receipt(
                    "R2", "WORKER_CAPABILITY_REMOVED", "W1", capability="C"
                ),
            },
            p1,
        )
        self.assertEqual(p2["assignment"]["S"], "W2")
        self.assertEqual(p2["receipt_history_ids"], ["R1", "R2"])

    def test_repeated_capability_removal_is_idempotent(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {
                "task": t,
                "receipt": receipt(
                    "R1", "WORKER_CAPABILITY_REMOVED", "W1", capability="C"
                ),
            },
            p0,
        )
        p2 = v4.solve_after_receipt(
            {
                "task": t,
                "receipt": receipt(
                    "R2", "WORKER_CAPABILITY_REMOVED", "W1", capability="C"
                ),
            },
            p1,
        )
        self.assertEqual(p1["assignment"]["S"], "W2")
        self.assertEqual(p2["assignment"]["S"], "W2")

    def test_resource_updates_are_persistent_ordered_last_write_wins(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {
                "task": t,
                "receipt": receipt("R1", "RESOURCE_CAPACITY_CHANGED", "R", capacity=1),
            },
            p0,
        )
        p2 = v4.solve_after_receipt(
            {
                "task": t,
                "receipt": receipt("R2", "RESOURCE_CAPACITY_CHANGED", "R", capacity=3),
            },
            p1,
        )
        self.assertEqual(p1["resource_capacities"]["R"], 1)
        self.assertEqual(p2["resource_capacities"]["R"], 3)

    def test_step_unavailability_is_idempotent_and_persistent(self):
        t = task()
        t["steps"].append({
            "id": "ALT",
            "requires": [],
            "produces": ["DONE"],
            "capability": "C",
            "cost": 2,
            "writes": ["R"],
            "evidence_outputs": ["E2"],
        })
        p0 = v4.solve_initial({"task": t})
        self.assertEqual(p0["task_ids"], ["S"])
        p1 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R1", "STEP_UNAVAILABLE", "S")}, p0
        )
        p2 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R2", "STEP_UNAVAILABLE", "S")}, p1
        )
        self.assertEqual(p1["task_ids"], ["ALT"])
        self.assertEqual(p2["task_ids"], ["ALT"])

    def test_unknown_entities_fail_closed(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        cases = [
            receipt("A", "WORKER_UNAVAILABLE", "NO_WORKER"),
            receipt("B", "STEP_UNAVAILABLE", "NO_STEP"),
            receipt("C", "WORKER_CAPABILITY_REMOVED", "W1", capability="NO_CAP"),
            receipt("D", "RESOURCE_CAPACITY_CHANGED", "NO_RESOURCE", capacity=1),
        ]
        for row in cases:
            with self.assertRaises(v4.DelegationReceiptHistoryV4Error):
                v4.solve_after_receipt({"task": t, "receipt": row}, p0)

    def test_previous_history_metadata_is_load_bearing(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        p1 = v4.solve_after_receipt(
            {"task": t, "receipt": receipt("R1", "WORKER_UNAVAILABLE", "W1")},
            p0,
        )
        bad = dict(p1)
        bad["receipt_history_ids"] = []
        with self.assertRaises(v4.DelegationReceiptHistoryV4Error):
            v4.solve_after_receipt(
                {"task": t, "receipt": receipt("R2", "WORKER_UNAVAILABLE", "W2")},
                bad,
            )

    def test_duplicate_receipt_id_fails_closed(self):
        t = task()
        p0 = v4.solve_initial({"task": t})
        r = receipt("R1", "WORKER_UNAVAILABLE", "W1")
        p1 = v4.solve_after_receipt({"task": t, "receipt": r}, p0)
        with self.assertRaises(v4.DelegationReceiptHistoryV4Error):
            v4.solve_after_receipt({"task": t, "receipt": r}, p1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

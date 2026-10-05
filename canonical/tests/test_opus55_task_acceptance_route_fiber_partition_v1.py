from __future__ import annotations
import unittest
from canonical.runtime.opus55_task_acceptance_route_fiber_partition_v1 import (
    ROUTES, build_partition, classify, truth_table,
)

class Tests(unittest.TestCase):
    def test_truth_table_total_and_single_valued(self):
        rows=truth_table()
        self.assertEqual(len(rows),8)
        self.assertEqual(len({(r["E"],r["M"],r["H"]) for r in rows}),8)
        self.assertTrue(all(r["route"] in ROUTES for r in rows))

    def test_priority(self):
        self.assertEqual(classify(True,True,True),"E_EXACT_SOLVED")
        self.assertEqual(classify(False,True,True),"M_RESTRICTED_SOLVED")
        self.assertEqual(classify(False,False,True),"H_SEPARATING")
        self.assertEqual(classify(False,False,False),"OTHER")

    def test_constructor_emits_bridge_partition_contract(self):
        v=build_partition(
            domain_id="T",
            domain_semantics_sha="1"*40,
            route_predicate_semantics_sha="2"*40,
            partition_proof_source_sha="3"*40,
            independent_or_objective=True,
        )
        self.assertEqual(v["status"],"PASS")
        self.assertEqual(set(v["universe_atoms"]),set(ROUTES))
        self.assertTrue(v["partition_certificate"]["pairwise_disjoint_proved"])
        self.assertTrue(v["partition_certificate"]["atoms_define_declared_omega_proved"])
        self.assertFalse(v["target_domain_coverage_proved"])

    def test_unknowns_conservatively_fall_to_other(self):
        self.assertEqual(classify(False,False,False),"OTHER")

    def test_nonindependent_proof_fails_closed(self):
        v=build_partition(
            domain_id="T",
            domain_semantics_sha="1"*40,
            route_predicate_semantics_sha="2"*40,
            partition_proof_source_sha="3"*40,
            independent_or_objective=False,
        )
        self.assertEqual(v["status"],"FAIL_CLOSED")

    def test_bad_content_address_fails_closed(self):
        v=build_partition(
            domain_id="T",
            domain_semantics_sha="bad",
            route_predicate_semantics_sha="2"*40,
            partition_proof_source_sha="3"*40,
            independent_or_objective=True,
        )
        self.assertEqual(v["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)

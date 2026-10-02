from __future__ import annotations
import copy, unittest
from canonical.runtime import p1_v6_universal_terminal_generator_refinement_v1 as r

class Tests(unittest.TestCase):
    def test_exact_frozen_generator_has_30_structural_classes(self):
        classes=r.structural_classes()
        self.assertEqual(len(classes),30)
        self.assertEqual(
            {d:sum(1 for x in classes if x[0]==d) for d in range(1,6)},
            {1:4,2:5,3:6,4:7,5:8},
        )

    def test_full_universal_refinement_passes(self):
        out=r.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["structural_equivalence_class_count"],30)
        self.assertEqual(out["refinement_checks"],30*3*6)
        self.assertEqual(out["forward_rescue_checks"],30*3*6)
        self.assertEqual(out["symptom_only_negative_checks"],30*3*6)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["historical_terminal_case_ids_read"],0)

    def test_repair_permutation_erasure_preserves_projection(self):
        for difficulty,n,cause in r.structural_classes():
            projections=[]
            for order in ("canonical","reverse","rotate"):
                case=r.abstract_old_case(difficulty,cause,repair_order=order)
                public=r.old_suite.public_task(case)
                lifted=r.lift_public(public,"CODE")
                out=r.v6_candidate.solve(lifted)
                projections.append((out["cause_action_id"],tuple(out["repair_targets"])))
                self.assertEqual(r.lower_to_old(public,out),r.old_candidate.solve(public))
            self.assertEqual(len(set(projections)),1)

    def test_downstream_repair_never_rescues_any_structural_class(self):
        for difficulty,n,cause in r.structural_classes():
            case=r.abstract_old_case(difficulty,cause)
            public=r.old_suite.public_task(case)
            lifted=r.lift_public(public,"TOOL_API")
            out=r.v6_candidate.solve(lifted)
            attacked=copy.deepcopy(out)
            attacked["repair_targets"]=[f"restore:A{cause+1}:INVARIANT"]
            iv=r.v6_proof.execute_intervention(lifted,attacked)
            self.assertFalse(iv["terminal_rescued"],(difficulty,cause,iv))

    def test_lift_uses_no_hidden_oracle(self):
        case=r.abstract_old_case(5,4)
        public=r.old_suite.public_task(case)
        before=r.lift_public(public,"RESEARCH")
        case["_oracle"]["cause_step"]=999
        case["_oracle"]["repair_id"]="evil"
        after=r.lift_public(r.old_suite.public_task(case),"RESEARCH")
        self.assertEqual(before,after)

    def test_duplicate_repair_target_fails_closed(self):
        case=r.abstract_old_case(3,2)
        public=r.old_suite.public_task(case)
        public["task"]["repair_candidates"].append(copy.deepcopy(public["task"]["repair_candidates"][0]))
        with self.assertRaises(ValueError):
            r.lift_public(public,"CODE")

if __name__=="__main__":
    unittest.main(verbosity=2)

from __future__ import annotations
from copy import deepcopy
import inspect
import unittest

from canonical.runtime import delegation_structural_variety_proof_v3 as proof
from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate

class DelegationStructuralVarietyV3Tests(unittest.TestCase):
    def test_information_boundary_and_population(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("delegation_structural_variety_proof_v3",src)
        out=proof.run_batch(20261002,250,candidate.solve_initial)
        self.assertTrue(out["all_pass"],out["failures"][:5])
        self.assertEqual(set(out["class_pass_counts"]),set(proof.CLASSES))
        for cls in proof.CLASSES:
            self.assertEqual(out["class_pass_counts"][cls],50)

    def test_topologies_are_structurally_distinct(self):
        signatures=set()
        for i in range(len(proof.CLASSES)):
            case=proof.generate_case(7,i)
            task=case["task"]
            edges=tuple(sorted((tuple(sorted(s["requires"])),tuple(sorted(s["produces"]))) for s in task["steps"] if not s["id"].startswith("DECOY_")))
            signatures.add(edges)
        self.assertEqual(len(signatures),len(proof.CLASSES))

    def test_nonoptimal_alternative_is_rejected(self):
        case=proof.generate_case(9,4)
        good=candidate.solve_initial(proof.public_case(case))
        self.assertTrue(proof.score_case(case,good)["pass"])
        bad=deepcopy(good)
        cheap=next(x for x in bad["task_ids"] if "S2_CHEAP_" in x)
        alt=cheap.replace("S2_CHEAP_","S2_ALT_")
        bad["task_ids"]=[alt if x==cheap else x for x in bad["task_ids"]]
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_missing_fanin_evidence_is_rejected(self):
        case=proof.generate_case(11,2)
        good=candidate.solve_initial(proof.public_case(case))
        self.assertTrue(proof.score_case(case,good)["pass"])
        bad=deepcopy(good)
        bad["terminal_evidence"]=bad["terminal_evidence"][:-1]
        self.assertFalse(proof.score_case(case,bad)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)

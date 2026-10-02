import copy
import inspect
import json
import unittest

from canonical.runtime import structured_method_information_safe_candidate_v2 as c
from canonical.runtime import structured_method_information_safe_proof_v2 as p

class StructuredMethodV2Tests(unittest.TestCase):
    def test_boundary_and_grid(self):
        case=p.generate_case(1,7)
        public=p.public_task(case)
        self.assertNotIn("_oracle",json.dumps(public))
        src=inspect.getsource(c)
        self.assertNotIn("_oracle",src)
        out=p.run_batch(20261002,1024,c.solve)
        self.assertTrue(out["pass"],out["failures"][:3])
        self.assertEqual(set(out["origins"]),set(p.ORIGINS))
        self.assertEqual(set(out["condition_ops"]),{"always","eq","neq","ge","gt","le","lt","in"})

    def test_order_branch_and_mutations(self):
        case=p.generate_case(2,9)
        public=p.public_task(case)
        out=c.solve(public)
        rev=copy.deepcopy(public)
        rev["task"]["rules"].reverse()
        self.assertEqual(out,c.solve(rev))
        changed=copy.deepcopy(public)
        changed["task"]["branch_values"]["flag"]=not changed["task"]["branch_values"]["flag"]
        self.assertNotEqual(out["applied_rule_ids"],c.solve(changed)["applied_rule_ids"])
        for key in ("edges","invariants","acceptance_checks","applied_rule_ids","required_outputs"):
            mutant=copy.deepcopy(out)
            mutant[key]=mutant[key][1:] if mutant[key] else [{"x":"mutant"}]
            self.assertFalse(p.score_case(case,mutant)["pass"],key)

    def test_declared_metadata_mismatch_fails_closed(self):
        public=p.public_task(p.generate_case(5,12))
        rule=next(x for x in public["task"]["rules"] if x["id"]=="R_RATE")
        rule["output_dimension"]={"L":1}
        with self.assertRaises(c.CandidateError):
            c.solve(public)

if __name__=="__main__":
    unittest.main(verbosity=2)

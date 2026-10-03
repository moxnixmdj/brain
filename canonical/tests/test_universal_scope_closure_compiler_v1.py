from __future__ import annotations
import copy, unittest
from canonical.runtime.universal_scope_closure_compiler_v1 import (
    UNIVERSAL, EXACT, SUPERSET, DECOMPOSITION, evaluate, compile_targets
)

def base(basis,scope="S"):
    return {"id":"C::"+scope,"basis":basis,"verified":True,"independent":True,
            "scope_relation":"EXACT","target_scope_id":scope}

class UniversalScopeClosureCompilerV1Tests(unittest.TestCase):
    def test_universal(self):
        c=base(UNIVERSAL); c.update(formal_completeness=True,
            all_admissible_target_inputs_proved=True,premise_set_id="P")
        self.assertTrue(evaluate(c)["scope_complete"])
    def test_exact(self):
        c=base(EXACT); c.update(complete_target_case_set=True,
            universe_identity_bound=True,case_universe_digest="sha256:x")
        self.assertTrue(evaluate(c)["scope_complete"])
    def test_superset(self):
        c=base(SUPERSET); c.update(exhaustive=True,target_subset_proved=True,
            superset_universe_digest="sha256:y")
        self.assertTrue(evaluate(c)["scope_complete"])
    def test_lossless_decomposition_and_bad_child(self):
        a=base(UNIVERSAL,"A"); a.update(formal_completeness=True,
            all_admissible_target_inputs_proved=True,premise_set_id="P")
        b=base(EXACT,"B"); b.update(complete_target_case_set=True,
            universe_identity_bound=True,case_universe_digest="sha256:b")
        root=base(DECOMPOSITION,"ROOT"); root.update(coverage_complete=True,
            coverage_relation="EXACT_UNION",coverage_proof_verified=True,children=[a,b])
        self.assertTrue(evaluate(root)["scope_complete"])
        bad=copy.deepcopy(root); bad["children"][1]["complete_target_case_set"]=False
        self.assertFalse(evaluate(bad)["scope_complete"])
    def test_perfect_sample_not_scope(self):
        c=base(EXACT); c.update(complete_target_case_set=False,
            universe_identity_bound=True,case_universe_digest="sha256:sample",
            sample_pass_rate=1.0)
        self.assertFalse(evaluate(c)["scope_complete"])
    def test_unverified_unknown_and_duplicate_fail(self):
        c=base(UNIVERSAL); c.update(formal_completeness=True,
            all_admissible_target_inputs_proved=True,premise_set_id="P",verified=False)
        self.assertFalse(evaluate(c)["scope_complete"])
        self.assertFalse(evaluate(base("MAGIC"))["scope_complete"])
        a=base(UNIVERSAL,"A"); a.update(formal_completeness=True,
            all_admissible_target_inputs_proved=True,premise_set_id="P")
        root=base(DECOMPOSITION,"ROOT"); root.update(coverage_complete=True,
            coverage_relation="EXACT_UNION",coverage_proof_verified=True,
            children=[a,copy.deepcopy(a)])
        self.assertFalse(evaluate(root)["scope_complete"])
    def test_scope_never_grants_performance_credit(self):
        c=base(UNIVERSAL); c.update(formal_completeness=True,
            all_admissible_target_inputs_proved=True,premise_set_id="P")
        out=compile_targets({"targets":[{"predicate_id":"X","scope_certificate":c}]})
        self.assertEqual(out["scope_complete_count"],1)
        self.assertEqual(out["targets"][0]["performance_state"],"SEPARATE_UNCHANGED")
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)

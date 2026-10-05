import unittest
from canonical.runtime import aa_briefcase_dual_predicate_result_bridge_v1 as m

def fx():
    reg={"predicates":[
      {"id":m.PREDICATES[0],"surface":"AA-Briefcase v1.1","acceptance":"AA-Briefcase v1.1 >= 1822 Elo"},
      {"id":m.PREDICATES[1],"surface":"AA-Briefcase v1.1","acceptance":"AA-Briefcase v1.1 >= 1822 Elo"},
    ]}
    base=dict(m.EXPECTED); base["score"]=1822
    binds={"bindings":[dict(base,predicate_id=p) for p in m.PREDICATES],"shared_target_tuple":{"predicates":list(m.PREDICATES)}}
    root={"predicates":[{"id":p,"class":"RELATIVE_RATING_THRESHOLD"} for p in m.PREDICATES]}
    result={
      "schema":"X","status":"VERIFIED_COMPARABLE_BRAIN_SCORE","independent_or_owner_verified":True,
      "benchmark":"AA-Briefcase","benchmark_version":"1.1","evaluator":"Artificial Analysis",
      "harness":m.EXPECTED["harness"],"fallback_policy":m.EXPECTED["fallback_policy"],"unit":"Elo",
      "brain_score":1822,"subject_sha256":"a"*64,
      "rating_epoch":m.FROZEN_RATING_EPOCH,"rating_epoch_verified":True,"opus55_reference_score":1822,
    }
    return reg,binds,root,result

class T(unittest.TestCase):
    def test_exact_frozen_epoch_passes_both(self):
        out=m.compile_bridge(*fx())
        self.assertEqual(out["predicate_results"],{p:True for p in m.PREDICATES})
    def test_below_threshold_fails_both(self):
        x=list(fx()); x[3]=dict(x[3],brain_score=1821.9)
        self.assertFalse(any(m.compile_bridge(*x)["predicate_results"].values()))
    def test_other_epoch_is_rejected(self):
        x=list(fx()); x[3]=dict(x[3],rating_epoch="OTHER_EPOCH",opus55_reference_score=1808)
        with self.assertRaises(m.BridgeError): m.compile_bridge(*x)
    def test_epoch_must_be_verified(self):
        x=list(fx()); x[3]=dict(x[3],rating_epoch_verified=False)
        with self.assertRaises(m.BridgeError): m.compile_bridge(*x)
    def test_reference_must_equal_frozen_target(self):
        x=list(fx()); x[3]=dict(x[3],opus55_reference_score=1808)
        with self.assertRaises(m.BridgeError): m.compile_bridge(*x)

if __name__=="__main__": unittest.main(verbosity=2)

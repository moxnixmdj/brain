import copy, unittest
from canonical.runtime import aa_briefcase_dual_predicate_result_bridge_v1 as m

def fixtures():
    reg={'predicates':[
      {'id':'PROWORK_AA_BRIEFCASE_GE_1822','surface':'AA-Briefcase v1.1','acceptance':'AA-Briefcase v1.1 >= 1822 Elo'},
      {'id':'ARTIFACT_AA_BRIEFCASE_GE_1822','surface':'AA-Briefcase v1.1','acceptance':'AA-Briefcase v1.1 >= 1822 Elo on comparable harness'},]}
    base=dict(m.EXPECTED); base['score']=1822
    binds={'bindings':[dict(base,predicate_id=p) for p in m.PREDICATES], 'shared_target_tuple':{'predicates':list(m.PREDICATES)}}
    root={'predicates':[{'id':p,'class':'RELATIVE_RATING_THRESHOLD'} for p in m.PREDICATES]}
    result={'schema':'X','status':'VERIFIED_COMPARABLE_BRAIN_SCORE','independent_or_owner_verified':True,
      'benchmark':'AA-Briefcase','benchmark_version':'1.1','evaluator':'Artificial Analysis','harness':m.EXPECTED['harness'],
      'fallback_policy':m.EXPECTED['fallback_policy'],'unit':'Elo','brain_score':1822,'subject_sha256':'a'*64}
    return reg,binds,root,result
class T(unittest.TestCase):
 def test_pass_fans_out_both(self):
  o=m.compile_bridge(*fixtures()); self.assertEqual(o['predicate_results'],{p:True for p in m.PREDICATES})
 def test_below_fails_both(self):
  x=list(fixtures()); x[3]=dict(x[3],brain_score=1821.99); o=m.compile_bridge(*x); self.assertFalse(any(o['predicate_results'].values()))
 def test_tuple_drift_denies(self):
  x=list(fixtures()); x[1]=copy.deepcopy(x[1]); x[1]['bindings'][1]['harness']='other'; self.assertRaises(m.BridgeError,m.compile_bridge,*x)
 def test_result_harness_drift_denies(self):
  x=list(fixtures()); x[3]=dict(x[3],harness='other'); self.assertRaises(m.BridgeError,m.compile_bridge,*x)
 def test_unverified_result_denies(self):
  x=list(fixtures()); x[3]=dict(x[3],independent_or_owner_verified=False); self.assertRaises(m.BridgeError,m.compile_bridge,*x)
 def test_registry_surface_drift_denies(self):
  x=list(fixtures()); x[0]=copy.deepcopy(x[0]); x[0]['predicates'][0]['surface']='other'; self.assertRaises(m.BridgeError,m.compile_bridge,*x)
if __name__=='__main__':unittest.main(verbosity=2)

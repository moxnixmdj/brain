from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as d
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

def _auth(domain,sha):
 return {"pass":True,"semantic_truth_authority":True,"candidate_domain":domain,"authority_sha256":sha}

def test_composes_exact_four_way_authority():
 def a(pair_id,repo_root=None):
  return _auth([regcap.CCOB,mrel.MREL],"a") if pair_id=="CCOB_MREL" else _auth([regcap.CCYB,mrel.MREL],"b")
 def c(repo_root=None):
  return _auth([regcap.TLAC,mrel.MREL],"c")
 out=d.verify_authority(ccob_mrel_authority=a,ccyb_mrel_authority=a,tlac_mrel_authority=c)
 assert out["pass"] is True,out
 assert out["semantic_truth_authority"] is True
 assert out["candidate_universe_complete"] is True
 assert sorted(out["candidate_domain"])==sorted(d.DOMAIN)
 assert len(set(out["outcomes"].values()))==4
 assert out["open_world_ontology_complete"] is False
 assert out["terminal_authority"] is False

def test_component_failure_fails_closed():
 def bad(pair_id,repo_root=None):
  return {"pass":False}
 def c(repo_root=None):
  return _auth([regcap.TLAC,mrel.MREL],"c")
 out=d.verify_authority(ccob_mrel_authority=bad,ccyb_mrel_authority=bad,tlac_mrel_authority=c)
 assert out["pass"] is False
 assert out["status"]=="FAIL_CLOSED"

def test_domain_drift_fails_closed():
 def a(pair_id,repo_root=None):
  return _auth([regcap.CCOB,mrel.MREL],"a")
 def b(pair_id,repo_root=None):
  return _auth([regcap.CCOB,mrel.MREL],"b")
 def c(repo_root=None):
  return _auth([regcap.TLAC,mrel.MREL],"c")
 out=d.verify_authority(ccob_mrel_authority=a,ccyb_mrel_authority=b,tlac_mrel_authority=c)
 assert out["pass"] is False
 assert "DOMAIN_DRIFT" in out["reason"]

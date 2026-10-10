"""Bounded four-way governing-requirement authority for CCoB, CCyB, TLAC, MREL."""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Any, Callable, Mapping
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac_mrel

SCHEMA="PROJECT_BRAIN_REGCAP_FOUR_WAY_GOVERNING_REQUIREMENT_DISCRIMINATOR_V1"
SCOPE_ID="REGCAP_CCOB_CCYB_TLAC_MREL_GOVERNING_REQUIREMENT_TASK_V1"
OBSERVATION_ID="FOUR_WAY_GOVERNING_REQUIREMENT_CLASS"
DOMAIN=(regcap.CCOB,regcap.CCYB,regcap.TLAC,mrel.MREL)
OUTCOMES={
 regcap.CCOB:"BASEL_CCOB_2_5_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
 regcap.CCYB:"BASEL_CCYB_SYSTEM_WIDE_RISK_RELEASABLE_BUFFER",
 regcap.TLAC:"FSB_MINIMUM_EXTERNAL_TLAC_FOR_GSIBS",
 mrel.MREL:"EU_RESOLUTION_AUTHORITY_CASE_BY_CASE_MREL",
}

def _sha(v:Any)->str:
 return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _base(status:str,passed:bool=False,**x:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"status":status,"pass":passed,"semantic_truth_authority":False,
 "relative_selection_authority":False,"candidate_universe_complete":False,
 "open_world_ontology_complete":False,"concept_identity_authority":False,
 "execution_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,**x}

def verify_authority(*,repo_root:Any=None,
 ccob_mrel_authority:Callable[...,Mapping[str,Any]]=pair.verify_authority,
 ccyb_mrel_authority:Callable[...,Mapping[str,Any]]=pair.verify_authority,
 tlac_mrel_authority:Callable[...,Mapping[str,Any]]=tlac_mrel.verify_authority)->dict[str,Any]:
 try:
  a=ccob_mrel_authority(pair.CCOB_MREL,repo_root=repo_root)
  b=ccyb_mrel_authority(pair.CCYB_MREL,repo_root=repo_root)
  c=tlac_mrel_authority(repo_root=repo_root)
  rows=(("CCOB_MREL",a,[regcap.CCOB,mrel.MREL]),("CCYB_MREL",b,[regcap.CCYB,mrel.MREL]),("TLAC_MREL",c,[regcap.TLAC,mrel.MREL]))
  for name,row,domain in rows:
   if not isinstance(row,Mapping) or row.get("pass") is not True or row.get("semantic_truth_authority") is not True:
    return _base("FAIL_CLOSED",reason="COMPONENT_AUTHORITY_FAILED:"+name)
   if sorted(str(x) for x in row.get("candidate_domain") or [])!=sorted(domain):
    return _base("FAIL_CLOSED",reason="COMPONENT_DOMAIN_DRIFT:"+name)
   if not str(row.get("authority_sha256") or "").strip():
    return _base("FAIL_CLOSED",reason="COMPONENT_AUTHORITY_DIGEST_MISSING:"+name)
  component={"CCOB_MREL":a["authority_sha256"],"CCYB_MREL":b["authority_sha256"],"TLAC_MREL":c["authority_sha256"]}
  material={"scope_id":SCOPE_ID,"candidate_domain":list(DOMAIN),"observation_id":OBSERVATION_ID,"outcomes":OUTCOMES,"components":component}
  return _base("PASS__FOUR_WAY_GOVERNING_REQUIREMENT_DISCRIMINATOR_AUTHENTICATED",True,
   semantic_truth_authority=True,candidate_universe_complete=True,
   candidate_universe_complete_only_for_scope_id=SCOPE_ID,scope_id=SCOPE_ID,
   candidate_domain=list(DOMAIN),observation_id=OBSERVATION_ID,outcomes=dict(OUTCOMES),
   component_authority_sha256=component,authority_sha256=_sha(material),
   boundary="EXACT_FOUR_CONCEPT_TASK_SCOPE_ONLY__POSITIVE_AUTHENTICATED_MARKERS_ONLY__NO_ABSENCE_AS_NEGATION__NO_OPEN_WORLD_COMPLETENESS")
 except Exception as exc:
  return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))

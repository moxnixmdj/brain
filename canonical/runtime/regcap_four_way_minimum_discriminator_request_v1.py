"""Minimum truthful information request for the bounded CCoB/CCyB/TLAC/MREL ambiguity."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four

SCHEMA="PROJECT_BRAIN_REGCAP_FOUR_WAY_MINIMUM_DISCRIMINATOR_REQUEST_V1"

def _base(status:str,passed:bool=False,**x:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"status":status,"pass":passed,"truth_authority":False,
 "verification_authority":False,"concept_identity_authority":False,
 "candidate_universe_complete":False,"open_world_ontology_complete":False,
 "execution_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,**x}

def compile_request(candidate_concept_ids:Sequence[str],*,repo_root:Any=None,
 authority_verifier:Callable[...,Mapping[str,Any]]=four.verify_authority)->dict[str,Any]:
 try:
  if isinstance(candidate_concept_ids,(str,bytes)) or not isinstance(candidate_concept_ids,Sequence):
   return _base("FAIL_CLOSED",reason="CANDIDATE_IDS_REQUIRED")
  supplied=sorted(str(x) for x in candidate_concept_ids)
  required=sorted(four.DOMAIN)
  if supplied!=required:
   return _base("FAIL_CLOSED",reason="CANDIDATE_SET_MUST_EQUAL_BOUND_FOUR_WAY_DOMAIN",
    supplied_candidate_ids=supplied,required_candidate_ids=required)
  authority=authority_verifier(repo_root=repo_root)
  if not isinstance(authority,Mapping) or authority.get("pass") is not True:
   return _base("FAIL_CLOSED",reason="FOUR_WAY_DISCRIMINATOR_AUTHORITY_FAILED")
  if authority.get("semantic_truth_authority") is not True:
   return _base("FAIL_CLOSED",reason="FOUR_WAY_DISCRIMINATOR_TRUTH_AUTHORITY_MISSING")
  outcomes=authority.get("outcomes")
  if not isinstance(outcomes,Mapping) or set(outcomes)!=set(four.DOMAIN) or len(set(outcomes.values()))!=4:
   return _base("FAIL_CLOSED",reason="FOUR_WAY_OUTCOME_MAP_NOT_EXACTLY_SEPARATING")
  return _base("PASS__MINIMUM_FOUR_WAY_POLICY_CHANGING_INFORMATION_REQUEST",True,
   request_kind="ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
   scope_id=four.SCOPE_ID,observation_id=four.OBSERVATION_ID,
   candidate_concept_ids=list(four.DOMAIN),allowed_outcomes=deepcopy(dict(outcomes)),
   authority_sha256=authority.get("authority_sha256"),
   minimum_observation_count=1,absence_is_not_negative_evidence=True,
   provider_truth_authority=False,independent_verification_required=True,
   after_verified_observation="REENTER_LOSS_CUSHION_GROUNDING_WITH_BOUND_CONTEXT",
   boundary="ONE_POSITIVE_AUTHENTICATED_OBSERVATION_ONLY__NO_GUESSING__NO_OPEN_WORLD_IDENTITY")
 except Exception as exc:
  return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))

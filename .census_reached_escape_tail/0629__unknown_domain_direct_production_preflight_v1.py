"""Fail-closed point-of-use preflight for Unknown-Domain direct production.

This module cannot grant authority. It verifies an eventual activation package
against the frozen production precommit and returns READY only when every
qualification, scope, resource, and one-use prerequisite is already present.
It deliberately does not generate a beacon, create a claim, or execute cases.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

TARGET="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
LEAVES={
 "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
 "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS",
}

def _fail(errors):
 return {
  "status":"FAIL_CLOSED",
  "ready":False,
  "errors":sorted(set(errors)),
  "execution_authority":False,
  "fresh_reality_authority":False,
  "promotion_authority":False,
 }

def preflight(doc:Mapping[str,Any]):
 if not isinstance(doc,Mapping):
  return _fail(["INPUT_INVALID"])
 errors=[]
 if doc.get("qualification_independent_pass") is not True:
  errors.append("V2_QUALIFICATION_NOT_INDEPENDENT_PASS")
 if doc.get("exact_subject_blobs_rechecked") is not True:
  errors.append("EXACT_SUBJECT_BLOBS_NOT_RECHECKED")
 if doc.get("production_cases_consumed") != 0:
  errors.append("PRODUCTION_CASES_ALREADY_CONSUMED")
 if doc.get("production_beacon_generated") is not False:
  errors.append("PRODUCTION_BEACON_ALREADY_GENERATED_OR_UNKNOWN")
 if doc.get("candidate_mutated_after_qualification") is not False:
  errors.append("CANDIDATE_MUTATION_STATE_NOT_FALSE")
 if doc.get("persistent_learned_bytes") != 0:
  errors.append("PERSISTENT_LEARNED_BYTES_NONZERO")
 if doc.get("external_frontier_model_calls") != 0:
  errors.append("EXTERNAL_FRONTIER_MODEL_CALLS_NONZERO")
 if doc.get("external_learned_capability_calls") != 0:
  errors.append("EXTERNAL_LEARNED_CAPABILITY_CALLS_NONZERO")
 if doc.get("incremental_spend_usd") != 0:
  errors.append("INCREMENTAL_SPEND_NONZERO")
 if doc.get("target_predicate") != TARGET:
  errors.append("TARGET_PREDICATE_MISMATCH")
 leaves=doc.get("authorized_leaves")
 if not isinstance(leaves,Sequence) or isinstance(leaves,(str,bytes)) or set(map(str,leaves))!=LEAVES:
  errors.append("AUTHORIZED_LEAF_SET_MISMATCH")
 if doc.get("predicate_local_activation_independent_pass") is not True:
  errors.append("PREDICATE_LOCAL_ACTIVATION_NOT_VERIFIED")
 if doc.get("predicate_local_fresh_reality") is not True:
  errors.append("PREDICATE_LOCAL_FRESH_REALITY_FALSE")
 if doc.get("global_fresh_reality") is not False:
  errors.append("GLOBAL_FRESH_REALITY_MUST_REMAIN_FALSE")
 if doc.get("one_use_claim_created") is not False:
  errors.append("ONE_USE_CLAIM_MUST_NOT_EXIST_AT_PREFLIGHT")
 if doc.get("execution_started") is not False:
  errors.append("EXECUTION_ALREADY_STARTED_OR_UNKNOWN")
 if errors:
  return _fail(errors)
 return {
  "status":"READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY",
  "ready":True,
  "errors":[],
  "next_action":"DERIVE_EXECUTION_LEASE_DIGEST_AND_CREATE_ONE_GITHUB_REF_CLAIM__ONLY_HTTP_201_MAY_ADVANCE_TO_BEACON_GENERATION",
  "execution_authority":False,
  "fresh_reality_authority":False,
  "promotion_authority":False,
 }


#!/usr/bin/env python3
"""Fail-closed authority guard for the current global Retrieval V6 policy.

The guard intentionally validates semantics plus the exact immutable V6
substrate/receipts. It does not hard-code the current-pointer blob, so the
pointer can later add this guard/entrypoint without creating a hash cycle.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_AUTHORITY_GUARD_V1"

EXPECTED={
 "activation_path":"canonical/governance/GLOBAL_RETRIEVAL_V6_ACTIVATION_V1.json",
 "activation_blob":"335b285d27faa16913c9ec661cdf0b6a25057726",
 "activation_verification_path":"canonical/verification/GLOBAL_RETRIEVAL_V6_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "activation_verification_blob":"9d0e031501a68f3a009b371cf9bde4d86fe34656",
 "core_verification_path":"canonical/verification/GLOBAL_RETRIEVAL_V6_CORE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "core_verification_blob":"47b43d15919172b1752e8658bff3194c4491a132",
 "controller_path":"canonical/runtime/global_retrieval_controller_v1.py",
 "controller_blob":"211a34f2bc22f531b895b0c7a26187b176875e9f",
 "torture_path":"canonical/runtime/retrieval_torture_universe_v2.py",
 "torture_blob":"86a7796f2a08e63e0d073cae8bc7a6b66febe98b",
 "pointer_path":"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json",
}

def git_blob_sha(raw:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _fail(*errors:str)->dict[str,Any]:
 return {
  "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
  "errors":sorted(set(errors)),
  "execution_authority":False,"promotion_authority":False,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
 }

def validate(pointer:Mapping[str,Any],activation:Mapping[str,Any],
 activation_verification:Mapping[str,Any],core_verification:Mapping[str,Any],
 actual_blobs:Mapping[str,str])->dict[str,Any]:
 errors=[]
 for key in ("activation_blob","activation_verification_blob","core_verification_blob","controller_blob","torture_blob"):
  if actual_blobs.get(key)!=EXPECTED[key]:
   errors.append("ACTUAL_BLOB_MISMATCH:"+key)
 if pointer.get("schema")!="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1":
  errors.append("POINTER_SCHEMA_INVALID")
 if not str(pointer.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT"):
  errors.append("POINTER_NOT_ACTIVE_V6")
 current=pointer.get("current_global_retrieval_authority")
 if not isinstance(current,Mapping) or current.get("path")!=EXPECTED["activation_path"] or current.get("git_blob_sha")!=EXPECTED["activation_blob"]:
  errors.append("POINTER_ACTIVATION_BINDING_INVALID")
 pol=pointer.get("policy")
 if not isinstance(pol,Mapping):
  errors.append("POINTER_POLICY_MISSING")
 else:
  required={
   "bounded_authoritative_enumeration":"PREFERRED_WHEN_AVAILABLE",
   "candidate_memory":"MONOTONIC__RERANKING_CANNOT_DELETE_DISCOVERED_IDENTITIES",
   "correlated_sources":"DISCOUNT_SHARED_UPSTREAM_INDEX_OR_PROVIDER",
   "open_world_miss":"UNKNOWN__NEVER_NONEXISTENT",
   "real_false_negative":"COMPILE_TO_PERMANENT_TORTURE_REGRESSION",
  }
  for k,v in required.items():
   if pol.get(k)!=v: errors.append("POINTER_POLICY_INVALID:"+k)
  if not str(pol.get("zero_lexical_bridge") or "").startswith("QUERYLESS_BOUNDED_ENUMERATION_REQUIRED"):
   errors.append("ZERO_LEXICAL_BRIDGE_POLICY_INVALID")
 if activation.get("schema")!="PROJECT_BRAIN_GLOBAL_RETRIEVAL_V6_ACTIVATION_V1":
  errors.append("ACTIVATION_SCHEMA_INVALID")
 if activation.get("v6_extension",{}).get("global_controller",{}).get("git_blob_sha")!=EXPECTED["controller_blob"]:
  errors.append("ACTIVATION_CONTROLLER_BINDING_INVALID")
 if activation.get("v6_extension",{}).get("torture_universe",{}).get("git_blob_sha")!=EXPECTED["torture_blob"]:
  errors.append("ACTIVATION_TORTURE_BINDING_INVALID")
 if activation.get("v6_extension",{}).get("independent_core_verification",{}).get("git_blob_sha")!=EXPECTED["core_verification_blob"]:
  errors.append("ACTIVATION_CORE_RECEIPT_BINDING_INVALID")
 if activation_verification.get("independent_runner",{}).get("conclusion")!="success":
  errors.append("ACTIVATION_VERIFICATION_NOT_SUCCESS")
 if core_verification.get("independent_runner",{}).get("conclusion")!="success":
  errors.append("CORE_VERIFICATION_NOT_SUCCESS")
 if core_verification.get("verified",{}).get("finite_torture_case_count")!=4096:
  errors.append("TORTURE_CASE_COUNT_INVALID")
 if core_verification.get("verified",{}).get("finite_architectural_failure_class_coverage")!=1.0:
  errors.append("FINITE_MECHANISM_COVERAGE_INVALID")
 if pointer.get("incremental_spend_usd")!=0:
  errors.append("NONZERO_INCREMENTAL_SPEND")
 if errors:return _fail(*errors)
 return {
  "schema":SCHEMA,
  "status":"PASS__CURRENT_GLOBAL_RETRIEVAL_V6_AUTHORITY_VALIDATED",
  "pass":True,
  "activation_blob":EXPECTED["activation_blob"],
  "controller_blob":EXPECTED["controller_blob"],
  "torture_blob":EXPECTED["torture_blob"],
  "queryless_bounded_enumeration_mandatory_where_available":True,
  "candidate_memory_monotonic":True,
  "correlated_source_discount_mandatory":True,
  "open_world_unknown_preserved":True,
  "execution_authority":False,"promotion_authority":False,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "errors":[],
 }

def evaluate_repository(root:Path)->dict[str,Any]:
 def raw(rel:str)->bytes:return (root/rel).read_bytes()
 def load(rel:str):return json.loads(raw(rel).decode("utf-8"))
 actual={
  "activation_blob":git_blob_sha(raw(EXPECTED["activation_path"])),
  "activation_verification_blob":git_blob_sha(raw(EXPECTED["activation_verification_path"])),
  "core_verification_blob":git_blob_sha(raw(EXPECTED["core_verification_path"])),
  "controller_blob":git_blob_sha(raw(EXPECTED["controller_path"])),
  "torture_blob":git_blob_sha(raw(EXPECTED["torture_path"])),
 }
 return validate(load(EXPECTED["pointer_path"]),load(EXPECTED["activation_path"]),
  load(EXPECTED["activation_verification_path"]),load(EXPECTED["core_verification_path"]),actual)

def main()->int:
 out=evaluate_repository(Path(__file__).resolve().parents[2])
 print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out.get("pass") else 1
if __name__=="__main__":raise SystemExit(main())

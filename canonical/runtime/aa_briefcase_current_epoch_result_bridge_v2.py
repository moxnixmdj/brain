from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CURRENT_EPOCH_RESULT_BRIDGE_V2"
PREDICATES = ("PROWORK_AA_BRIEFCASE_GE_1822","ARTIFACT_AA_BRIEFCASE_GE_1822")
TARGET_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OPUS55_CURRENT_OWNER_TARGET_V1"
EXPECTED_BENCHMARK = "AA-Briefcase v1.1"
EXPECTED_MODEL = "Claude Opus 5.5 (Max, Default Fallback)"
EXPECTED_UNIT = "Elo"

class BridgeError(ValueError): pass

def _canon(v: Any) -> bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _sha(v: Any) -> str: return hashlib.sha256(_canon(v)).hexdigest()

def _finite_number(v: Any,label: str) -> float:
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise BridgeError(label+"_INVALID")
    x=float(v)
    if x!=x or x in (float("inf"),float("-inf")): raise BridgeError(label+"_INVALID")
    return x

def compile_current_epoch_bridge(current_target: Mapping[str,Any], result: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(current_target,Mapping): raise BridgeError("TARGET_INVALID")
    if current_target.get("schema")!=TARGET_SCHEMA: raise BridgeError("TARGET_SCHEMA_MISMATCH")
    target=current_target.get("target"); epoch_rule=current_target.get("epoch_rule")
    if not isinstance(target,Mapping) or not isinstance(epoch_rule,Mapping): raise BridgeError("TARGET_BINDING_MISSING")
    if target.get("benchmark")!=EXPECTED_BENCHMARK: raise BridgeError("TARGET_BENCHMARK_MISMATCH")
    if target.get("model")!=EXPECTED_MODEL: raise BridgeError("TARGET_MODEL_MISMATCH")
    observed_date=target.get("observed_date")
    if not isinstance(observed_date,str) or not observed_date: raise BridgeError("TARGET_OBSERVED_DATE_INVALID")
    reference=_finite_number(target.get("current_owner_elo"),"TARGET_REFERENCE")
    if _finite_number(epoch_rule.get("current_epoch_minimum_opus55_target_elo"),"TARGET_EPOCH_REFERENCE")!=reference: raise BridgeError("TARGET_EPOCH_REFERENCE_DRIFT")
    required={"schema","status","independent_or_owner_verified","benchmark","model","unit","brain_score","subject_sha256","matched_current_owner_epoch","target_observed_date","opus55_reference_score"}
    if not isinstance(result,Mapping) or set(result)!=required: raise BridgeError("RESULT_FIELDS_INVALID")
    if result.get("status")!="VERIFIED_COMPARABLE_BRAIN_SCORE": raise BridgeError("RESULT_NOT_VERIFIED_COMPARABLE")
    if result.get("independent_or_owner_verified") is not True: raise BridgeError("RESULT_NOT_INDEPENDENT_OR_OWNER_VERIFIED")
    if result.get("benchmark")!=EXPECTED_BENCHMARK: raise BridgeError("RESULT_BENCHMARK_MISMATCH")
    if result.get("model")!=EXPECTED_MODEL: raise BridgeError("RESULT_MODEL_MISMATCH")
    if result.get("unit")!=EXPECTED_UNIT: raise BridgeError("RESULT_UNIT_MISMATCH")
    if result.get("matched_current_owner_epoch") is not True: raise BridgeError("RESULT_EPOCH_NOT_MATCHED")
    if result.get("target_observed_date")!=observed_date: raise BridgeError("RESULT_TARGET_DATE_MISMATCH")
    if _finite_number(result.get("opus55_reference_score"),"RESULT_REFERENCE")!=reference: raise BridgeError("RESULT_REFERENCE_MISMATCH")
    subject=result.get("subject_sha256")
    if not isinstance(subject,str) or len(subject)!=64 or any(c not in "0123456789abcdef" for c in subject): raise BridgeError("RESULT_SUBJECT_HASH_INVALID")
    score=_finite_number(result.get("brain_score"),"RESULT_SCORE"); passed=score>=reference
    material={"schema":SCHEMA,"status":"PASS_CURRENT_TARGET" if passed else "FAIL_CURRENT_TARGET","shared_surface":EXPECTED_BENCHMARK,"target_model":EXPECTED_MODEL,"brain_score":score,"opus55_reference_score":reference,"unit":EXPECTED_UNIT,"target_observed_date":observed_date,"subject_sha256":subject,"predicate_results":{pid:passed for pid in PREDICATES},"single_result_reused_across_predicates":True,"historical_1822_predicate_ids_preserved":True,"historical_epoch_rewritten":False,"acceptance_credit_delta":0}
    return {**material,"bridge_verdict_sha256":_sha(material)}

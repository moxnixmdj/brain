from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_DUAL_PREDICATE_RESULT_BRIDGE_V1"
PREDICATES = (
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
)
THRESHOLD = 1822.0
FROZEN_RATING_EPOCH = "ANTHROPIC_RELEASE_2026_09_22__AA_BRIEFCASE_V1_1__OPUS55_MAX_DEFAULT_FALLBACK"
EXPECTED = {
    "benchmark": "AA-Briefcase",
    "benchmark_version": "1.1",
    "model": "Claude Opus 5.5",
    "effort": "max",
    "evaluator": "Artificial Analysis",
    "harness": "Artificial Analysis release-snapshot AA-Briefcase v1.1 evaluation",
    "fallback_policy": "DEFAULT_FALLBACK_AS_RELEASE_SNAPSHOT",
    "unit": "Elo",
}

class BridgeError(ValueError):
    pass

def _canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def _sha(v: Any) -> str:
    return hashlib.sha256(_canon(v)).hexdigest()

def _rows_by_id(doc: Mapping[str, Any], key: str) -> dict[str, Mapping[str, Any]]:
    rows = doc.get(key)
    if not isinstance(rows, list):
        raise BridgeError(key.upper()+"_MISSING")
    out = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise BridgeError(key.upper()+"_ROW_INVALID")
        pid = row.get("predicate_id") if key == "bindings" else row.get("id")
        if isinstance(pid, str):
            out[pid] = row
    return out

def compile_bridge(registry: Mapping[str, Any], target_bindings: Mapping[str, Any], root2: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    reg = _rows_by_id(registry, "predicates")
    binds = _rows_by_id(target_bindings, "bindings")
    rootrows = _rows_by_id(root2, "predicates")
    for pid in PREDICATES:
        if pid not in reg or pid not in binds or pid not in rootrows:
            raise BridgeError("PREDICATE_BINDING_MISSING:"+pid)
        if reg[pid].get("surface") != "AA-Briefcase v1.1":
            raise BridgeError("REGISTRY_SURFACE_DRIFT:"+pid)
        if "1822" not in str(reg[pid].get("acceptance") or ""):
            raise BridgeError("REGISTRY_THRESHOLD_DRIFT:"+pid)
        for k,v in EXPECTED.items():
            if binds[pid].get(k) != v:
                raise BridgeError("TARGET_TUPLE_DRIFT:"+pid+":"+k)
        if float(binds[pid].get("score")) != THRESHOLD:
            raise BridgeError("TARGET_THRESHOLD_DRIFT:"+pid)
        if rootrows[pid].get("class") != "RELATIVE_RATING_THRESHOLD":
            raise BridgeError("ROOT2_CLASS_DRIFT:"+pid)
    a = {k: binds[PREDICATES[0]].get(k) for k in EXPECTED}
    b = {k: binds[PREDICATES[1]].get(k) for k in EXPECTED}
    if a != b or binds[PREDICATES[0]].get("score") != binds[PREDICATES[1]].get("score"):
        raise BridgeError("SHARED_TARGET_TUPLE_NOT_IDENTICAL")
    shared = target_bindings.get("shared_target_tuple")
    if not isinstance(shared, Mapping) or set(shared.get("predicates") or []) != set(PREDICATES):
        raise BridgeError("SHARED_TARGET_TUPLE_DECLARATION_MISSING")

    required = {
        "schema","status","independent_or_owner_verified",
        "benchmark","benchmark_version","evaluator","harness","fallback_policy","unit",
        "brain_score","subject_sha256",
        "rating_epoch","rating_epoch_verified","opus55_reference_score",
    }
    if not isinstance(result, Mapping) or set(result) != required:
        raise BridgeError("RESULT_FIELDS_INVALID")
    if result.get("status") != "VERIFIED_COMPARABLE_BRAIN_SCORE" or result.get("independent_or_owner_verified") is not True:
        raise BridgeError("RESULT_NOT_VERIFIED_COMPARABLE")
    for k in ("benchmark","benchmark_version","evaluator","harness","fallback_policy","unit"):
        if result.get(k) != EXPECTED[k]:
            raise BridgeError("RESULT_TUPLE_MISMATCH:"+k)
    if result.get("rating_epoch") != FROZEN_RATING_EPOCH:
        raise BridgeError("RESULT_RATING_EPOCH_MISMATCH")
    if result.get("rating_epoch_verified") is not True:
        raise BridgeError("RESULT_RATING_EPOCH_NOT_VERIFIED")
    ref = result.get("opus55_reference_score")
    if isinstance(ref, bool) or not isinstance(ref,(int,float)) or float(ref) != THRESHOLD:
        raise BridgeError("RESULT_OPUS55_REFERENCE_SCORE_MISMATCH")
    subject = result.get("subject_sha256")
    if not isinstance(subject,str) or len(subject)!=64 or any(c not in "0123456789abcdef" for c in subject):
        raise BridgeError("RESULT_SUBJECT_HASH_INVALID")
    score = result.get("brain_score")
    if isinstance(score, bool) or not isinstance(score,(int,float)):
        raise BridgeError("RESULT_SCORE_INVALID")
    passed = float(score) >= THRESHOLD
    material = {
        "schema": SCHEMA,
        "status": "PASS_THRESHOLD" if passed else "FAIL_THRESHOLD",
        "shared_surface": "AA-Briefcase v1.1",
        "brain_score": float(score),
        "threshold": THRESHOLD,
        "unit": "Elo",
        "rating_epoch": FROZEN_RATING_EPOCH,
        "opus55_reference_score": THRESHOLD,
        "subject_sha256": subject,
        "predicate_results": {pid: passed for pid in PREDICATES},
        "single_result_reused_across_predicates": True,
        "acceptance_credit_delta": 0,
    }
    return {**material, "bridge_verdict_sha256": _sha(material)}

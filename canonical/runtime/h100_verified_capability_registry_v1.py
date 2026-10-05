"""Verified capability registry and library-first resolver for H100.

Only capabilities with prior content-addressed independent verification may
enter this registry. Known capabilities are dispatched before raw synthesis.
Unknown inputs fail closed to the raw-search stage.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_zero_learned_parametric_unary_v1 as param
from canonical.runtime import h100_oewn_lexical_acquisition_v1 as oewn
from canonical.runtime import h100_lexical_source_fallback_v1 as lexsrc
from canonical.runtime import h100_zero_learned_compositional_language_v1 as comp
from canonical.runtime import h100_zero_learned_tool_trace_normalizer_v1 as trace

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V1"

REGISTRY=(
    {"capability_id":"CAP_LINEAR_TREND_SINUSOID_V1","kind":"PARAMETRIC","family":"linear_trend_sinusoid","route":"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE","prior_verification":"canonical/verification/H100_ZERO_LEARNED_TRANSFER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_EXP_ABS_V1","kind":"PARAMETRIC","family":"exp_abs","route":"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE","prior_verification":"canonical/verification/H100_ZERO_LEARNED_TRANSFER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_THRESHOLD_STEP_V1","kind":"PARAMETRIC","family":"threshold_step","route":"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE","prior_verification":"canonical/verification/H100_ZERO_LEARNED_TRANSFER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_OEWN_REAL_LEXICAL_V1","kind":"DIRECT","route":"OEWN_REAL_LEXICAL","prior_verification":"canonical/verification/H100_OEWN_REAL_LEXICAL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_LEXICAL_SOURCE_FALLBACK_V1","kind":"DIRECT","route":"LEXICAL_SOURCE_FALLBACK","prior_verification":"canonical/verification/H100_LEXICAL_SOURCE_FALLBACK_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_COMPOSITIONAL_LANGUAGE_V1","kind":"DIRECT","route":"COMPOSITIONAL_LANGUAGE","prior_verification":"canonical/verification/H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
    {"capability_id":"CAP_TOOL_TRACE_NORMALIZER_V1","kind":"DIRECT","route":"TOOL_TRACE_NORMALIZER","prior_verification":"canonical/verification/H100_ZERO_LEARNED_TOOL_TRACE_NORMALIZER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"},
)
_BY_FAMILY={row["family"]:row for row in REGISTRY if row.get("kind")=="PARAMETRIC"}
_BY_ID={row["capability_id"]:row for row in REGISTRY}

class CapabilityRegistryError(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"VERIFIED_CAPABILITY_REGISTRY_READY",
        "entry_count":len(REGISTRY),"entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        "routing_priority":"LIBRARY_FIRST",
    }

def resolve_verified_capability(rows:Sequence[Mapping[str,Any]],*,target:str,input_name:str|None=None,exact_nrmse:float=1e-8)->dict[str,Any]:
    try:
        out=param.discover(rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse)
    except param.ParametricUnaryError as exc:
        return {"schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","reason":"COMPILED_ADAPTER_REJECTED:"+str(exc),"match":None,"persistent_learned_bytes":0}
    candidate=out.get("best_candidate")
    if not isinstance(candidate,Mapping):
        return {"schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","reason":"NO_COMPILED_CANDIDATE","match":None,"persistent_learned_bytes":0}
    family=str(candidate.get("family") or "")
    entry=_BY_FAMILY.get(family)
    if entry is None or float(candidate.get("nrmse",float("inf"))) > exact_nrmse:
        return {"schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","candidate_family":family or None,"match":None,"persistent_learned_bytes":0}
    return {"schema":SCHEMA,"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","match":{"capability_id":entry["capability_id"],"family":family,"route":entry["route"],"candidate":dict(candidate),"prior_verification":entry["prior_verification"]},"persistent_learned_bytes":0,"external_learned_capability_calls":0,"raw_synthesis_attempts_before_hit":0}

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryError("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping) or not isinstance(match.get("candidate"),Mapping):
        raise CapabilityRegistryError("MATCH_INVALID")
    return param.predict(match["candidate"],point)

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    """Invoke one already-verified direct capability by stable registry ID."""
    entry=_BY_ID.get(str(capability_id))
    if entry is None or entry.get("kind")!="DIRECT":
        raise CapabilityRegistryError("DIRECT_CAPABILITY_ID_INVALID")
    if not isinstance(payload,Mapping):
        raise CapabilityRegistryError("PAYLOAD_INVALID")
    route=entry["route"]
    if route=="OEWN_REAL_LEXICAL":
        out=oewn.resolve_lexical_role(payload.get("cue"),payload.get("context"),payload.get("knowledge"))
    elif route=="LEXICAL_SOURCE_FALLBACK":
        out=lexsrc.resolve_source_relations(payload.get("term"),payload.get("records"))
    elif route=="COMPOSITIONAL_LANGUAGE":
        out=comp.compile_compositional_roles(payload.get("text"))
    elif route=="TOOL_TRACE_NORMALIZER":
        out=trace.normalize_tool_trace(payload.get("payload"),inputs=payload.get("inputs"),target=payload.get("target"),format_hint=payload.get("format_hint"))
    else:
        raise CapabilityRegistryError("DIRECT_ROUTE_UNKNOWN")
    return {
        "schema":SCHEMA,
        "status":"DIRECT_LIBRARY_INVOKED__VERIFY_RESULT",
        "capability_id":capability_id,
        "prior_verification":entry["prior_verification"],
        "result":out,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "raw_synthesis_attempts_before_hit":0,
    }

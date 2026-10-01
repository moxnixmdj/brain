"""Validate frozen-envelope M0B transform type bindings.

This proves coverage and fail-closed drift detection for the current frozen behavioral
contract registry. It does not decide whether the semantic binding itself is correct;
that semantic responsibility remains upstream in M0A/source normalization.
"""
from __future__ import annotations
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_M0B_FROZEN_ENVELOPE_TYPE_BINDINGS_V1"

def validate(registry: Mapping[str, Any], bindings: Mapping[str, Any], supported: set[str]) -> list[str]:
    errors=[]
    if bindings.get("schema") != SCHEMA:
        errors.append("BINDING_SCHEMA_INVALID")
    rows=registry.get("active_contracted_residuals")
    if not isinstance(rows,list):
        return errors+["REGISTRY_ACTIVE_CONTRACTS_INVALID"]
    expected=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"REGISTRY_ROW_INVALID:{i}")
            continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid:
            errors.append(f"REGISTRY_BEHAVIOR_ID_INVALID:{i}")
            continue
        expected.append(bid)
    if len(expected)!=len(set(expected)):
        errors.append("REGISTRY_BEHAVIOR_ID_DUPLICATE")

    b_rows=bindings.get("bindings")
    if not isinstance(b_rows,list):
        return errors+["BINDINGS_NOT_LIST"]
    by_id={}
    for i,row in enumerate(b_rows):
        if not isinstance(row,Mapping):
            errors.append(f"BINDING_ROW_INVALID:{i}")
            continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid:
            errors.append(f"BINDING_BEHAVIOR_ID_INVALID:{i}")
            continue
        if bid in by_id:
            errors.append(f"BINDING_BEHAVIOR_ID_DUPLICATE:{bid}")
            continue
        kinds=row.get("transform_kinds")
        if not isinstance(kinds,list) or not kinds or any(not isinstance(k,str) or not k for k in kinds):
            errors.append(f"TRANSFORM_KINDS_INVALID:{bid}")
            kinds=[]
        unknown=sorted(set(kinds)-supported)
        if unknown:
            errors.append(f"UNSUPPORTED_TRANSFORM_KIND:{bid}:"+",".join(unknown))
        basis=row.get("basis")
        if not isinstance(basis,str) or not basis.strip():
            errors.append(f"BINDING_BASIS_MISSING:{bid}")
        by_id[bid]=row

    missing=sorted(set(expected)-set(by_id))
    extra=sorted(set(by_id)-set(expected))
    errors.extend(f"FROZEN_BEHAVIOR_UNTYPED:{x}" for x in missing)
    errors.extend(f"NONREGISTRY_BEHAVIOR_BOUND:{x}" for x in extra)

    declared=bindings.get("supported_transform_kinds")
    if not isinstance(declared,list) or set(declared)!=supported:
        errors.append("SUPPORTED_TRANSFORM_KIND_SET_MISMATCH")
    return sorted(set(errors))

def verdict(registry: Mapping[str,Any], bindings: Mapping[str,Any], supported:set[str]) -> dict[str,Any]:
    errors=validate(registry,bindings,supported)
    return {
        "schema":"PROJECT_BRAIN_M0B_FROZEN_ENVELOPE_TYPE_COVERAGE_VERDICT_V1",
        "pass":not errors,
        "errors":errors,
        "behavior_count":len(registry.get("active_contracted_residuals",[])) if isinstance(registry.get("active_contracted_residuals"),list) else 0,
        "closure_scope":"FROZEN_CURRENT_BEHAVIORAL_CONTRACT_REGISTRY_ONLY",
        "semantic_authority":False,
        "recompute_rule":"ANY_REGISTRY_BEHAVIOR_CHANGE_INVALIDATES_THIS_VERDICT",
    }

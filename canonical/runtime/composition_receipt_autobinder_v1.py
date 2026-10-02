"""Fail-closed claim-bound receipt autobinder for composition interfaces.

A receipt binds only when it explicitly names the frozen composition claim,
component, interface, required property, and carries all required verification
metadata.  Names, family membership, behavioral passes, or semantic similarity
are never used as substitutes.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COMPOSITION_RECEIPT_AUTOBINDER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "interfaces": [],
        "bound_interface_count": 0,
        "open_interface_count": 0,
        "all_used_component_interfaces_scoped_proved": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _admissible_receipt(r: Mapping[str, Any]) -> bool:
    return (
        r.get("verified") is True
        and r.get("independent") is True
        and r.get("contamination_clean") is True
        and r.get("acceptance_scoped") is True
        and isinstance(r.get("source_path"), str) and bool(r.get("source_path"))
        and isinstance(r.get("source_sha"), str) and bool(r.get("source_sha"))
    )


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = doc.get("claim_id")
    interfaces = doc.get("interfaces")
    receipts = doc.get("receipts")
    if not isinstance(claim_id, str) or not claim_id:
        return _fail("CLAIM_ID_REQUIRED")
    if not isinstance(interfaces, list) or not interfaces:
        return _fail("INTERFACES_REQUIRED")
    if not isinstance(receipts, list):
        return _fail("RECEIPTS_NOT_LIST")

    parsed_receipts = []
    errors: list[str] = []
    for i, r in enumerate(receipts):
        if not isinstance(r, Mapping):
            errors.append(f"RECEIPT_{i}_INVALID")
            continue
        props = r.get("properties")
        if not isinstance(props, list) or any(not isinstance(p, str) or not p for p in props):
            errors.append(f"RECEIPT_{i}_PROPERTIES_INVALID")
            continue
        parsed_receipts.append(r)
    if errors:
        return _fail(*errors)

    out = []
    keys = set()
    bound_count = 0
    for i, interface in enumerate(interfaces):
        if not isinstance(interface, Mapping):
            return _fail(f"INTERFACE_{i}_INVALID")
        component_id = interface.get("component_id")
        interface_id = interface.get("interface_id")
        required = interface.get("required_properties")
        if (
            not isinstance(component_id, str) or not component_id
            or not isinstance(interface_id, str) or not interface_id
            or not isinstance(required, list) or not required
            or any(not isinstance(p, str) or not p for p in required)
        ):
            return _fail(f"INTERFACE_{i}_SHAPE_INVALID")
        key = (component_id, interface_id)
        if key in keys:
            return _fail(f"DUPLICATE_INTERFACE:{component_id}:{interface_id}")
        keys.add(key)

        proved = set()
        supporting = []
        for r in parsed_receipts:
            if not _admissible_receipt(r):
                continue
            if r.get("claim_id") != claim_id:
                continue
            if r.get("component_id") != component_id:
                continue
            if r.get("interface_id") != interface_id:
                continue
            overlap = set(required) & set(r.get("properties", []))
            if overlap:
                proved.update(overlap)
                supporting.append(r.get("receipt_id") or r["source_path"])

        missing = sorted(set(required) - proved)
        state = "BOUND" if not missing else "OPEN"
        if state == "BOUND":
            bound_count += 1
        out.append({
            "component_id": component_id,
            "interface_id": interface_id,
            "required_properties": sorted(set(required)),
            "proved_properties": sorted(proved),
            "missing_properties": missing,
            "supporting_receipt_ids": sorted(set(supporting)),
            "state": state,
        })

    return {
        "schema": SCHEMA,
        "status": (
            "ALL_EXACT_INTERFACE_RECEIPTS_BOUND"
            if bound_count == len(out)
            else "RESIDUAL_EXACT_INTERFACE_RECEIPTS_OPEN"
        ),
        "errors": [],
        "claim_id": claim_id,
        "interfaces": out,
        "bound_interface_count": bound_count,
        "open_interface_count": len(out) - bound_count,
        "all_used_component_interfaces_scoped_proved": bound_count == len(out),
        "rule": (
            "EXACT_CLAIM_COMPONENT_INTERFACE_PROPERTY_MATCH_ONLY__"
            "INDEPENDENT_CONTAMINATION_CLEAN_ACCEPTANCE_SCOPED_RECEIPTS_REQUIRED__"
            "NO_NAME_OR_FAMILY_INFERENCE"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

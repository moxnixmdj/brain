"""Exact load-bearing component proof slicer for frozen composition claims.

The slicer does not weaken a composition acceptance protocol and grants no credit.
It only answers whether every property of every explicitly declared component
interface used by a frozen composition claim is covered by independently verified,
contamination-clean, claim-bound, acceptance-scoped receipts.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COMPOSITION_COMPONENT_PROOF_SLICER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "interfaces": [],
        "all_used_component_interfaces_scoped_proved": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = doc.get("claim_id")
    interfaces = doc.get("interfaces")
    receipts = doc.get("receipts", [])
    if not isinstance(claim_id, str) or not claim_id:
        return _fail("CLAIM_ID_REQUIRED")
    if not isinstance(interfaces, list) or not interfaces:
        return _fail("INTERFACES_REQUIRED")
    if not isinstance(receipts, list):
        return _fail("RECEIPTS_INVALID")

    parsed_interfaces: list[tuple[str, str, set[str]]] = []
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(interfaces):
        if not isinstance(row, Mapping):
            return _fail(f"INTERFACE_{i}_INVALID")
        component = row.get("component_id")
        interface = row.get("interface_id")
        props = row.get("required_properties")
        key = (component, interface)
        if (
            not isinstance(component, str) or not component
            or not isinstance(interface, str) or not interface
            or key in seen
            or not isinstance(props, list) or not props
            or any(not isinstance(x, str) or not x for x in props)
            or len(props) != len(set(props))
        ):
            return _fail("INTERFACE_DEFINITION_INVALID_OR_DUPLICATE")
        seen.add(key)
        parsed_interfaces.append((component, interface, set(props)))

    valid_receipts: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    receipt_ids: set[str] = set()
    for i, row in enumerate(receipts):
        if not isinstance(row, Mapping):
            return _fail(f"RECEIPT_{i}_INVALID")
        rid = row.get("receipt_id")
        if not isinstance(rid, str) or not rid or rid in receipt_ids:
            return _fail("RECEIPT_IDENTITIES_INVALID_OR_DUPLICATE")
        receipt_ids.add(rid)
        component = row.get("component_id")
        interface = row.get("interface_id")
        props = row.get("proved_properties")
        if not isinstance(component, str) or not isinstance(interface, str):
            return _fail(f"RECEIPT_BINDING_INVALID:{rid}")
        if not isinstance(props, list) or any(not isinstance(x, str) or not x for x in props):
            return _fail(f"RECEIPT_PROPERTIES_INVALID:{rid}")
        if len(props) != len(set(props)):
            return _fail(f"RECEIPT_PROPERTIES_DUPLICATE:{rid}")
        flags = (
            row.get("verified") is True,
            row.get("independent") is True,
            row.get("contamination_clean") is True,
            row.get("acceptance_scoped") is True,
            row.get("binds_frozen_claim") == claim_id,
        )
        if all(flags):
            valid_receipts.setdefault((component, interface), []).append(row)

    out = []
    all_pass = True
    for component, interface, required in parsed_interfaces:
        rows = valid_receipts.get((component, interface), [])
        covered = set()
        used_ids = []
        for row in rows:
            covered.update(row["proved_properties"])
            used_ids.append(row["receipt_id"])
        missing = sorted(required - covered)
        unknown = sorted(covered - required)
        if missing:
            all_pass = False
        out.append({
            "component_id": component,
            "interface_id": interface,
            "required_properties": sorted(required),
            "proved_properties": sorted(required & covered),
            "missing_properties": missing,
            "extra_receipt_properties_ignored": unknown,
            "supporting_receipt_ids": sorted(used_ids),
            "state": "SCOPED_PROVED" if not missing else "OPEN",
        })

    return {
        "schema": SCHEMA,
        "status": (
            "ALL_USED_COMPONENT_INTERFACES_SCOPED_PROVED"
            if all_pass else "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN"
        ),
        "errors": [],
        "claim_id": claim_id,
        "interfaces": out,
        "all_used_component_interfaces_scoped_proved": all_pass,
        "rule": (
            "ONLY_EXACT_DECLARED_LOAD_BEARING_INTERFACES_ARE_REDUCED__"
            "NO_WHOLE_FAMILY_PASS_INHERITANCE__NO_UNBOUND_RECEIPT_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

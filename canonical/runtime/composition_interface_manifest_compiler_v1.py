"""Literal composition component-interface manifest compiler.

Derives only the isolated component tokens that are explicitly present in the
frozen MULTI_CAPABILITY_COMPOSITION task dimensions as '+'-joined chains.

It does not map tokens to capability families, infer semantic equivalence,
bind receipts, close predicates, or authorize execution.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COMPOSITION_INTERFACE_MANIFEST_COMPILER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "claim_id": None,
        "interfaces": [],
        "composition_only_dimensions": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(protocols: Mapping[str, Any]) -> dict[str, Any]:
    rows = protocols.get("protocols")
    if not isinstance(rows, list):
        return _fail("PROTOCOLS_NOT_LIST")
    matches = [
        r for r in rows
        if isinstance(r, Mapping)
        and r.get("family") == "MULTI_CAPABILITY_COMPOSITION"
    ]
    if len(matches) != 1:
        return _fail("COMPOSITION_PROTOCOL_NOT_UNIQUE")
    row = matches[0]
    if row.get("status") != "DEFINED_RESULT_OPEN":
        return _fail("COMPOSITION_PROTOCOL_NOT_OPEN")

    acceptance = row.get("acceptance")
    required_clause = "Every isolated component used in the claim has its own scoped proof"
    if not isinstance(acceptance, str) or required_clause not in acceptance:
        return _fail("ISOLATED_COMPONENT_SCOPED_PROOF_CLAUSE_MISSING")

    dims = row.get("task_dimensions")
    if not isinstance(dims, list) or not dims or any(not isinstance(x, str) or not x for x in dims):
        return _fail("TASK_DIMENSIONS_INVALID")

    interfaces = []
    composition_only = []
    seen = set()
    for dim_index, dim in enumerate(dims):
        if "+" not in dim:
            composition_only.append({
                "source_dimension_index": dim_index,
                "source_dimension_literal": dim,
                "reason": "NO_LITERAL_PLUS_JOINED_ISOLATED_COMPONENT_CHAIN",
            })
            continue
        parts = [x.strip() for x in dim.split("+")]
        if len(parts) < 2 or any(not x for x in parts):
            return _fail(f"INVALID_PLUS_CHAIN:{dim_index}")
        for component_index, component in enumerate(parts):
            key = (component, dim)
            if key in seen:
                return _fail(f"DUPLICATE_COMPONENT_INTERFACE:{component}:{dim}")
            seen.add(key)
            interfaces.append({
                "component_id": component,
                "interface_id": dim,
                "required_properties": ["SCOPED_ACCEPTANCE_PROOF"],
                "source_dimension_index": dim_index,
                "source_component_index": component_index,
                "source_dimension_literal": dim,
                "source_component_literal": component,
                "family_binding": None,
                "receipt_binding": None,
            })

    if not interfaces:
        return _fail("NO_LITERAL_ISOLATED_COMPONENT_INTERFACES")

    return {
        "schema": SCHEMA,
        "status": "LITERAL_INTERFACE_MANIFEST_READY__FAMILY_AND_RECEIPT_BINDINGS_OPEN",
        "errors": [],
        "claim_id": "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1",
        "family": "MULTI_CAPABILITY_COMPOSITION",
        "source_acceptance_literal": acceptance,
        "source_task_dimensions": dims,
        "interfaces": interfaces,
        "composition_only_dimensions": composition_only,
        "isolated_component_interface_count": len(interfaces),
        "unique_component_literals": sorted({x["component_id"] for x in interfaces}),
        "family_bindings_complete": False,
        "receipt_bindings_complete": False,
        "rule": (
            "ONLY_LITERAL_PLUS_JOINED_COMPONENT_TOKENS_ARE_EXTRACTED__"
            "NO_FAMILY_MAPPING_NO_SEMANTIC_EQUIVALENCE_NO_RECEIPT_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

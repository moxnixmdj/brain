"""Fail-closed classifier for non-base behavioral-contract extension fields.

The canonical base-field adequacy gate handles the required behavioral schema.
This module handles the currently observed extension surface. Unknown extension
fields fail closed. Only extensions classified as ABC membership/adequacy may
enter the ABC adequacy basis; D/promotion metadata remains separate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_BEHAVIORAL_CONTRACT_EXTENSION_GATE_V1"

BASE_FIELDS = {
    "behavior_id","inputs","environment_state","allowed_information",
    "required_output_or_action","success_condition","failure_condition",
    "terminal_consequence","verification_route","dependency_boundary","scope",
    "source",
}

EXTENSION_ROLES = {
    "mechanism_state": "D_IMPLEMENTATION_METADATA",
    "mechanism_artifact": "D_IMPLEMENTATION_BINDING",
    "mechanism_evidence": "D_EVIDENCE_AUTHORITY",
    "remaining_scope": "ABC_MEMBERSHIP_BOUNDARY",
    "terminal_acceptance": "PROMOTION_EVIDENCE_AUTHORITY",
}

ABC_ROLES = {"ABC_MEMBERSHIP_BOUNDARY", "ABC_ADEQUACY", "ABC_HARD_CONSTRAINT"}


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _atom(behavior_id: str, field: str, value: Any) -> str:
    d = sha256(_canon(value).encode("utf-8")).hexdigest()
    return f"CONTRACT_EXTENSION::{behavior_id}::{field}::{d}"


def compile_extensions(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["CONTRACT_NOT_OBJECT"]}
    bid=contract.get("behavior_id")
    if not isinstance(bid,str) or not bid.strip():
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BEHAVIOR_ID_INVALID"]}

    errors=[]
    rows=[]
    for field,value in contract.items():
        if field in BASE_FIELDS:
            continue
        role=EXTENSION_ROLES.get(field)
        if role is None:
            errors.append("UNCLASSIFIED_EXTENSION_FIELD:"+field)
            continue
        rows.append({
            "field":field,
            "role":role,
            "atom_id":_atom(bid,field,value),
            "abc_load_bearing":role in ABC_ROLES,
        })

    if errors:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":sorted(errors)}

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__ALL_EXTENSION_FIELDS_CLASSIFIED",
        "behavior_id":bid,
        "extensions":sorted(rows,key=lambda x:x["field"]),
        "abc_extension_atom_ids":sorted(x["atom_id"] for x in rows if x["abc_load_bearing"]),
        "non_abc_extension_atom_ids":sorted(x["atom_id"] for x in rows if not x["abc_load_bearing"]),
        "unknown_extensions_fail_closed":True,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def verify_abc_extension_admission(contract: Any, admission_atom_ids: Any) -> dict[str, Any]:
    compiled=compile_extensions(contract)
    if compiled.get("pass") is not True:
        return compiled
    if not isinstance(admission_atom_ids,list) or any(not isinstance(x,str) or not x for x in admission_atom_ids):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["ADMISSION_ATOM_IDS_INVALID"]}
    required=set(compiled["abc_extension_atom_ids"])
    supplied=set(admission_atom_ids)
    missing=sorted(required-supplied)
    return {
        "schema":SCHEMA,
        "pass":not missing,
        "status":"PASS__ABC_EXTENSION_MEMBERSHIP_BOUND" if not missing else "FAIL_CLOSED",
        "errors":["ABC_EXTENSION_MEMBERSHIP_UNBOUND:"+x for x in missing],
        "compiled":compiled,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }

"""Fail-closed validator for the frozen Opus55 composition component interface manifest.

This validator materializes no capability evidence and grants no credit. It checks
that the isolated component interface set is a deterministic projection of the
frozen composition protocol plus the existing direct-scope decomposition, and
then executes the independently verified component proof slicer over the manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_components

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "canonical/governance/OPUS55_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"

EXPECTED_DIMENSIONS = [
    "research+tool use+artifact creation",
    "browser/computer action+memory+recovery",
    "coding+debugging+tool discovery",
    "delegation+evidence synthesis+artifact production",
    "cross-capability state handoff and rollback",
]
EXPECTED_ROLES = {
    "RESEARCH", "TOOL", "ARTIFACT", "BROWSER", "MEMORY",
    "RECOVERY", "CODING_DEBUGGING", "DELEGATION", "SYNTHESIS",
}
DECOMPOSITION_ROLE_TOKENS = {
    "RESEARCH", "TOOL", "ARTIFACT", "BROWSER", "MEMORY",
    "RECOVERY", "CODING", "DEBUGGING", "DELEGATION", "SYNTHESIS",
}


def _load(rel: str) -> dict[str, Any]:
    v = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(rel)
    return v


def _blob_sha(rel: str) -> str:
    b = (ROOT / rel).read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(b)}\0".encode())
    h.update(b)
    return h.hexdigest()


def evaluate(
    manifest: Mapping[str, Any],
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    decomposition: Mapping[str, Any],
    contracts: Mapping[str, Any],
    *,
    actual_blob_shas: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    if manifest.get("claim_id") != "OPUS55_MULTI_CAPABILITY_COMPOSITION_FROZEN_CLAIM_V1":
        errors.append("CLAIM_ID_MISMATCH")
    if manifest.get("isolated_component_scope_only") is not True:
        errors.append("ISOLATED_COMPONENT_SCOPE_FLAG_REQUIRED")

    authority = manifest.get("authority")
    if not isinstance(authority, Mapping):
        errors.append("AUTHORITY_MISSING")
        authority = {}
    authority_keys = {
        "protocols", "predicate_registry", "direct_scope_decomposition",
        "behavioral_contract_registry",
    }
    if set(authority) != authority_keys:
        errors.append("AUTHORITY_SET_MISMATCH")
    if actual_blob_shas is not None:
        for key in sorted(authority_keys):
            row = authority.get(key)
            if not isinstance(row, Mapping):
                errors.append(f"AUTHORITY_ROW_MISSING:{key}")
                continue
            path = row.get("path")
            sha = row.get("git_blob_sha")
            if not isinstance(path, str) or actual_blob_shas.get(path) != sha:
                errors.append(f"AUTHORITY_BLOB_MISMATCH:{key}")

    prows = protocols.get("protocols")
    comp = None
    if isinstance(prows, list):
        found = [
            x for x in prows
            if isinstance(x, Mapping) and x.get("family") == "MULTI_CAPABILITY_COMPOSITION"
        ]
        comp = found[0] if len(found) == 1 else None
    if not isinstance(comp, Mapping):
        errors.append("FROZEN_COMPOSITION_PROTOCOL_MISSING")
    else:
        if comp.get("task_dimensions") != EXPECTED_DIMENSIONS:
            errors.append("FROZEN_COMPOSITION_DIMENSIONS_MISMATCH")
        if comp.get("proof_mode") != "MATCHED_INTERACTION_AND_COMPOSITION_PROTOCOL":
            errors.append("FROZEN_COMPOSITION_PROOF_MODE_MISMATCH")

    predicates = registry.get("predicates")
    prow = None
    if isinstance(predicates, list):
        found = [
            x for x in predicates
            if isinstance(x, Mapping) and x.get("id") == "COMPOSITION_COMPONENT_SCOPED_PROOFS"
        ]
        prow = found[0] if len(found) == 1 else None
    if not isinstance(prow, Mapping):
        errors.append("COMPOSITION_COMPONENT_PREDICATE_MISSING")
    else:
        if prow.get("kind") != "DEPENDENCY_PROOF":
            errors.append("COMPOSITION_COMPONENT_PREDICATE_KIND_MISMATCH")
        if "ALL_COMPONENTS_USED_BY_COMPOSITION" not in str(prow.get("execution_rule", "")):
            errors.append("COMPOSITION_COMPONENT_EXECUTION_RULE_MISMATCH")

    parents = decomposition.get("parent_predicates")
    drow = None
    if isinstance(parents, list):
        found = [
            x for x in parents
            if isinstance(x, Mapping) and x.get("predicate_id") == "COMPOSITION_COMPONENT_SCOPED_PROOFS"
        ]
        drow = found[0] if len(found) == 1 else None
    if not isinstance(drow, Mapping):
        errors.append("DIRECT_SCOPE_COMPOSITION_ROW_MISSING")
    else:
        discharge = str(drow.get("discharge_condition", ""))
        for token in sorted(DECOMPOSITION_ROLE_TOKENS):
            if token not in discharge:
                errors.append(f"DECOMPOSITION_ROLE_TOKEN_MISSING:{token}")

    interfaces = manifest.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("INTERFACES_MISSING")
        interfaces = []
    keys: set[str] = set()
    roles: set[str] = set()
    for i, row in enumerate(interfaces):
        if not isinstance(row, Mapping):
            errors.append(f"INTERFACE_INVALID:{i}")
            continue
        component = row.get("component_id")
        interface = row.get("interface_id")
        role = row.get("component_role")
        props = row.get("required_properties")
        if not isinstance(component, str) or not component:
            errors.append(f"INTERFACE_COMPONENT_INVALID:{i}")
            continue
        if not isinstance(interface, str) or not interface:
            errors.append(f"INTERFACE_ID_INVALID:{i}")
            continue
        k = f"{component}::{interface}"
        if k in keys:
            errors.append(f"INTERFACE_DUPLICATE:{k}")
        keys.add(k)
        if not isinstance(role, str) or not role:
            errors.append(f"INTERFACE_ROLE_INVALID:{k}")
        else:
            roles.add(role)
        if (
            not isinstance(props, list) or not props
            or any(not isinstance(x, str) or not x for x in props)
            or len(props) != len(set(props))
        ):
            errors.append(f"INTERFACE_PROPERTIES_INVALID:{k}")

    if roles != EXPECTED_ROLES:
        errors.append("INTERFACE_ROLE_SET_MISMATCH")
    if len(keys) != 10:
        errors.append("INTERFACE_COUNT_NOT_10")

    dims = manifest.get("frozen_composition_dimensions")
    if dims != EXPECTED_DIMENSIONS:
        errors.append("MANIFEST_DIMENSIONS_MISMATCH")
    mapping = manifest.get("dimension_to_interfaces")
    if not isinstance(mapping, Mapping) or set(mapping) != set(EXPECTED_DIMENSIONS):
        errors.append("DIMENSION_INTERFACE_MAP_MISMATCH")
        mapping = {}
    referenced: set[str] = set()
    for dim in EXPECTED_DIMENSIONS:
        refs = mapping.get(dim)
        if not isinstance(refs, list) or not refs:
            errors.append(f"DIMENSION_HAS_NO_INTERFACES:{dim}")
            continue
        for ref in refs:
            if ref not in keys:
                errors.append(f"DIMENSION_REFERENCES_UNKNOWN_INTERFACE:{dim}:{ref}")
            else:
                referenced.add(ref)
    if referenced != keys:
        errors.append("NOT_ALL_INTERFACES_LOAD_BEARING_IN_DIMENSION_MAP")

    contract_rows = contracts.get("active_contracted_residuals")
    contract_ids = {
        x.get("behavior_id")
        for x in contract_rows or []
        if isinstance(x, Mapping) and isinstance(x.get("behavior_id"), str)
    }
    allowed_noncontract = {"LONG_HORIZON_MEMORY_AND_CONTINUITY", "ADVANCED_AGENTIC_CODING"}
    for key in keys:
        component = key.split("::", 1)[0]
        if component not in contract_ids and component not in allowed_noncontract:
            errors.append(f"UNBOUND_COMPONENT_ID:{component}")

    forbidden_claims = set(manifest.get("explicitly_not_claimed_by_this_manifest") or [])
    required_forbidden = {
        "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
        "CROSS_COMPONENT_INTERACTION_SUCCESS",
        "WHOLE_FAMILY_PASS_INHERITANCE",
    }
    if forbidden_claims != required_forbidden:
        errors.append("EXPLICIT_NONCLAIMS_MISMATCH")

    receipts = manifest.get("receipts")
    if receipts != []:
        errors.append("INITIAL_MANIFEST_MUST_NOT_EMBED_UNVERIFIED_RECEIPTS")

    slicer_input = {
        "claim_id": manifest.get("claim_id"),
        "interfaces": [
            {
                "component_id": x["component_id"],
                "interface_id": x["interface_id"],
                "required_properties": x["required_properties"],
            }
            for x in interfaces if isinstance(x, Mapping)
            and isinstance(x.get("component_id"), str)
            and isinstance(x.get("interface_id"), str)
            and isinstance(x.get("required_properties"), list)
        ],
        "receipts": [],
    }
    slicer = slice_components(slicer_input) if not errors else None
    if slicer is not None:
        if slicer.get("status") != "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN":
            errors.append("INITIAL_SLICER_STATUS_UNEXPECTED")
        open_count = sum(x.get("state") == "OPEN" for x in slicer.get("interfaces", []))
        if open_count != 10:
            errors.append("INITIAL_SLICER_OPEN_INTERFACE_COUNT_NOT_10")
        if slicer.get("all_used_component_interfaces_scoped_proved") is not False:
            errors.append("INITIAL_SLICER_MUST_NOT_CLOSE_DEPENDENCY")

    errors = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_OPUS55_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_VERDICT_V1",
        "status": (
            "PASS__FROZEN_COMPONENT_INTERFACES_EXPLICIT__COMPONENT_PROOFS_STILL_OPEN__ZERO_CREDIT"
            if not errors else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "interface_count": len(keys),
        "component_role_count": len(roles),
        "frozen_dimension_count": len(EXPECTED_DIMENSIONS),
        "representation_precondition_satisfied": not errors,
        "composition_component_predicate_closed": False,
        "slicer_status": slicer.get("status") if slicer else None,
        "slicer_open_interface_count": (
            sum(x.get("state") == "OPEN" for x in slicer.get("interfaces", []))
            if slicer else None
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "THIS_VERDICT_ONLY_MATERIALIZES_THE_FROZEN_ISOLATED_COMPONENT_INTERFACE_SET__"
            "NO_COMPONENT_OR_COMPOSITION_ACCEPTANCE_CREDIT"
        ),
    }


def evaluate_live() -> dict[str, Any]:
    manifest = _load(MANIFEST)
    auth = manifest["authority"]
    shas = {
        row["path"]: _blob_sha(row["path"])
        for row in auth.values()
    }
    return evaluate(
        manifest,
        _load(auth["protocols"]["path"]),
        _load(auth["predicate_registry"]["path"]),
        _load(auth["direct_scope_decomposition"]["path"]),
        _load(auth["behavioral_contract_registry"]["path"]),
        actual_blob_shas=shas,
    )


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

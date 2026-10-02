"""Fail-closed binder for already-accepted composition component proofs.

A binding is admissible only when the composition family and the accepted source
family share the exact active behavioral contract ID, the source family maps to
that single behavior, the current calibration accepts the family, and the typed
witness is independently verified, contamination-clean, full-protocol, and
PROVEN_STRONGER.

This reducer grants no new family or capability credit. It only supplies
SCOPED_ACCEPTANCE_PROOF receipts to the exact declared composition interfaces.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_components

ROOT = Path(__file__).resolve().parents[2]
BINDINGS = "canonical/governance/COMPOSITION_ACCEPTED_COMPONENT_SCOPED_BINDINGS_V1.json"
BASE_INPUT = "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json"


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


def _contract_row(registry: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    rows = registry.get("active_contracted_residuals")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
    return found[0] if len(found) == 1 else None


def evaluate_live() -> dict[str, Any]:
    doc = _load(BINDINGS)
    auth = doc.get("authority")
    errors: list[str] = []
    if not isinstance(auth, Mapping):
        return {"status": "FAIL_CLOSED", "errors": ["AUTHORITY_MISSING"], "pass": False}

    docs: dict[str, dict[str, Any]] = {}
    for key, row in auth.items():
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            errors.append(f"AUTHORITY_ROW_INVALID:{key}")
            continue
        path = row["path"]
        docs[key] = _load(path)
        if row.get("git_blob_sha") != _blob_sha(path):
            errors.append(f"AUTHORITY_BLOB_MISMATCH:{key}")

    manifest = docs.get("manifest", {})
    registry = docs.get("registry", {})
    calibration = docs.get("calibration", {})
    calibrated = set(((calibration.get("result") or {}).get("acceptance_calibrated_families") or []))
    family_map = registry.get("family_to_residual_contracts")
    if not isinstance(family_map, Mapping):
        errors.append("FAMILY_MAP_MISSING")
        family_map = {}

    composition_behaviors = family_map.get("MULTI_CAPABILITY_COMPOSITION")
    if not isinstance(composition_behaviors, list):
        errors.append("COMPOSITION_BEHAVIOR_MAP_MISSING")
        composition_behaviors = []

    manifest_keys = {
        (r.get("component_id"), r.get("interface_id"))
        for r in manifest.get("interfaces", [])
        if isinstance(r, Mapping)
    }
    base = _load(BASE_INPUT)
    if base.get("claim_id") != doc.get("claim_id"):
        errors.append("CLAIM_ID_MISMATCH")

    receipt_rows = []
    binding_results = []
    seen_binding_ids: set[str] = set()
    for i, binding in enumerate(doc.get("bindings") or []):
        berr: list[str] = []
        if not isinstance(binding, Mapping):
            errors.append(f"BINDING_INVALID:{i}")
            continue
        bid = binding.get("binding_id")
        component = binding.get("component_id")
        interface = binding.get("interface_id")
        source_family = binding.get("source_family")
        behavior = binding.get("source_behavior_id")
        witness_path = binding.get("source_witness")
        if not isinstance(bid, str) or not bid or bid in seen_binding_ids:
            berr.append("BINDING_ID_INVALID_OR_DUPLICATE")
        else:
            seen_binding_ids.add(bid)
        if (component, interface) not in manifest_keys:
            berr.append("TARGET_INTERFACE_NOT_IN_FROZEN_MANIFEST")
        source_map = family_map.get(source_family)
        if source_map != [behavior]:
            berr.append("SOURCE_FAMILY_NOT_EXACT_SINGLE_BEHAVIOR_MAP")
        if behavior not in composition_behaviors:
            berr.append("BEHAVIOR_NOT_LOAD_BEARING_IN_COMPOSITION")
        if source_family not in calibrated:
            berr.append("SOURCE_FAMILY_NOT_CURRENTLY_ACCEPTANCE_CALIBRATED")
        contract = _contract_row(registry, str(behavior))
        if contract is None:
            berr.append("ACTIVE_BEHAVIOR_CONTRACT_MISSING")
        else:
            consequence = str(contract.get("terminal_consequence", "")).lower()
            if "composition" not in consequence:
                berr.append("BEHAVIOR_CONTRACT_NOT_EXPLICITLY_COMPOSITION_LOAD_BEARING")

        witness_key = (
            "delegation_witness"
            if source_family == "SUBAGENT_DELEGATION_AND_COORDINATION"
            else "tool_discovery_witness"
            if source_family == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
            else None
        )
        witness = docs.get(witness_key or "", {})
        expected_witness_path = (auth.get(witness_key) or {}).get("path") if witness_key else None
        if witness_path != expected_witness_path:
            berr.append("WITNESS_PATH_NOT_AUTHORITY_BOUND")
        witness_flags = [
            witness.get("verified") is True,
            witness.get("independent") is True,
            witness.get("contamination_clean") is True,
            witness.get("binds_frozen_protocol") is True,
            witness.get("scope_relation") == "PROVEN_STRONGER",
            witness.get("closes_entire_protocol") is True,
            witness.get("source_behavior_id") == behavior,
            witness.get("family") == source_family,
        ]
        if not all(witness_flags):
            berr.append("WITNESS_NOT_FULL_SCOPE_ACCEPTANCE_ADMISSIBLE")
        if binding.get("proved_properties") != ["SCOPED_ACCEPTANCE_PROOF"]:
            berr.append("BINDING_PROPERTY_NOT_EXACT")

        if not berr:
            receipt_rows.append({
                "receipt_id": bid,
                "component_id": component,
                "interface_id": interface,
                "proved_properties": ["SCOPED_ACCEPTANCE_PROOF"],
                "verified": True,
                "independent": True,
                "contamination_clean": True,
                "acceptance_scoped": True,
                "binds_frozen_claim": doc["claim_id"],
                "source_family": source_family,
                "source_behavior_id": behavior,
                "source_witness": witness_path,
                "bridge_rule": binding.get("bridge_rule"),
            })
        binding_results.append({
            "binding_id": bid,
            "admissible": not berr,
            "errors": berr,
        })
        errors.extend(f"{bid}:{e}" for e in berr)

    if len(receipt_rows) != 2:
        errors.append("ADMISSIBLE_RECEIPT_COUNT_NOT_2")

    slicer_input = dict(base)
    slicer_input["schema"] = "PROJECT_BRAIN_COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V2"
    slicer_input["status"] = "TWO_EXACT_SHARED_BEHAVIOR_SCOPED_RECEIPTS_BOUND__ZERO_CREDIT"
    slicer_input["receipts"] = receipt_rows
    slicer_input["source_bindings"] = BINDINGS
    slicer_input["rule"] = (
        "ONLY_EXACT_SHARED_ACTIVE_BEHAVIOR_ID_BRIDGES_WITH_CURRENT_FULL_SCOPE_ACCEPTANCE_WITNESSES_COUNT__"
        "NO_NAME_OR_ANALOGY_BINDINGS"
    )
    sliced = slice_components(slicer_input) if not errors else None

    if sliced is not None:
        rows = sliced.get("interfaces")
        proved = [r for r in rows or [] if r.get("state") == "SCOPED_PROVED"]
        opened = [r for r in rows or [] if r.get("state") == "OPEN"]
        if len(proved) != 2:
            errors.append("SCOPED_PROVED_INTERFACE_COUNT_NOT_2")
        if len(opened) != 10:
            errors.append("OPEN_INTERFACE_COUNT_NOT_10")
        expected = {
            ("delegation", "delegation+evidence synthesis+artifact production"),
            ("tool discovery", "coding+debugging+tool discovery"),
        }
        if {(r.get("component_id"), r.get("interface_id")) for r in proved} != expected:
            errors.append("SCOPED_PROVED_INTERFACE_SET_MISMATCH")
        if sliced.get("all_used_component_interfaces_scoped_proved") is not False:
            errors.append("COMPOSITION_COMPONENT_DEPENDENCY_FALSE_CLOSURE")

    errors = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_COMPOSITION_ACCEPTED_COMPONENT_SCOPED_BINDING_VERDICT_V1",
        "status": (
            "PASS__2_OF_12_COMPONENT_INTERFACES_SCOPED_PROVED__10_OPEN__ZERO_CREDIT"
            if not errors else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "binding_results": binding_results,
        "admissible_receipts": receipt_rows if not errors else [],
        "slicer_input": slicer_input if not errors else None,
        "slicer_result": sliced if not errors else None,
        "scoped_proved_interface_count": 2 if not errors else None,
        "open_interface_count": 10 if not errors else None,
        "composition_component_predicate_closed": False,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "EXACT_SHARED_BEHAVIOR_ID_PLUS_CURRENT_FULL_SCOPE_ACCEPTANCE_WITNESS_MAY_DISCHARGE_ONLY_THE_DECLARED_ISOLATED_INTERFACE__"
            "NO_WHOLE_COMPOSITION_CREDIT"
        ),
    }


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

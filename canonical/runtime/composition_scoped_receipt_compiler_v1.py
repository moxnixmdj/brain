"""Compile current scoped composition receipts from activation-equivalent verified bindings.

Only three exact component interfaces are transported here: research,
browser/computer action, and tool discovery. The remaining nine stay open.
No family or terminal acceptance credit is granted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.activation_only_binding_equivalence_v1 import evaluate_capsule
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_evaluate

SCHEMA = "PROJECT_BRAIN_COMPOSITION_SCOPED_RECEIPT_COMPILER_V1"
CLAIM_ID = "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"


def evaluate(root: Path, capsule: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    eq = evaluate_capsule(capsule, root)
    if not eq.get("pass"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["ACTIVATION_EQUIVALENCE_FAILED"] + list(eq.get("errors") or []),
            "all_used_component_interfaces_scoped_proved": False,
            "closed_component_count": 0,
            "open_component_count": None,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    interfaces = manifest.get("interfaces")
    if not isinstance(interfaces, list) or len(interfaces) != 12:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["FROZEN_INTERFACE_MANIFEST_NOT_EXACTLY_12"],
            "all_used_component_interfaces_scoped_proved": False,
            "closed_component_count": 0,
            "open_component_count": None,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    slicer_interfaces = []
    exact_keys = set()
    for row in interfaces:
        if not isinstance(row, Mapping):
            return {
                "schema": SCHEMA, "status": "FAIL_CLOSED",
                "errors": ["INTERFACE_ROW_INVALID"],
                "all_used_component_interfaces_scoped_proved": False,
                "closed_component_count": 0, "open_component_count": None,
                "new_reality_units_consumed": 0, "capability_credit_delta": 0,
                "family_credit_delta": 0,
            }
        key = (row.get("component_id"), row.get("interface_id"))
        exact_keys.add(key)
        slicer_interfaces.append({
            "component_id": row.get("component_id"),
            "interface_id": row.get("interface_id"),
            "required_properties": row.get("required_properties"),
        })

    receipts = []
    for row in eq["rows"]:
        key = (row["component_id"], row["interface_id"])
        if key not in exact_keys:
            return {
                "schema": SCHEMA, "status": "FAIL_CLOSED",
                "errors": [f"BINDING_NOT_IN_FROZEN_INTERFACE_MANIFEST:{key!r}"],
                "all_used_component_interfaces_scoped_proved": False,
                "closed_component_count": 0, "open_component_count": None,
                "new_reality_units_consumed": 0, "capability_credit_delta": 0,
                "family_credit_delta": 0,
            }
        receipts.append({
            "receipt_id": "ACTIVATION_EQ::" + row["binding_id"],
            "component_id": row["component_id"],
            "interface_id": row["interface_id"],
            "proved_properties": ["SCOPED_ACCEPTANCE_PROOF"],
            "verified": True,
            "independent": True,
            "contamination_clean": True,
            "acceptance_scoped": True,
            "binds_frozen_claim": CLAIM_ID,
        })

    sliced = slice_evaluate({
        "claim_id": CLAIM_ID,
        "interfaces": slicer_interfaces,
        "receipts": receipts,
    })
    rows = sliced.get("interfaces") or []
    closed = [x["component_id"] for x in rows if x.get("state") == "SCOPED_PROVED"]
    opened = [x["component_id"] for x in rows if x.get("state") == "OPEN"]

    expected = sorted(["research", "browser/computer action", "tool discovery"])
    if sorted(closed) != expected:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["UNEXPECTED_SCOPED_PROOF_CLOSURE_SET"],
            "closed_components": sorted(closed),
            "open_components": sorted(opened),
            "all_used_component_interfaces_scoped_proved": False,
            "closed_component_count": len(closed),
            "open_component_count": len(opened),
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PARTIAL_SCOPED_PROOF_TRANSPORT__3_OF_12_CLOSED__9_OPEN__ZERO_CREDIT",
        "errors": [],
        "claim_id": CLAIM_ID,
        "closed_components": sorted(closed),
        "open_components": sorted(opened),
        "closed_component_count": len(closed),
        "open_component_count": len(opened),
        "all_used_component_interfaces_scoped_proved": False,
        "composition_component_scoped_proofs_predicate_closed": False,
        "slicer_result": sliced,
        "rule": "ONLY_HASH_EQUIVALENT_INDEPENDENTLY_VERIFIED_CURRENT_BINDINGS_TRANSPORTED__NO_WHOLE_FAMILY_INHERITANCE",
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    capsule = json.loads((root / "canonical/governance/OBJECTIVE_BINDING_ACTIVATION_EQUIVALENCE_V1.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json").read_text(encoding="utf-8"))
    out = evaluate(root, capsule, manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 1 if out["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())

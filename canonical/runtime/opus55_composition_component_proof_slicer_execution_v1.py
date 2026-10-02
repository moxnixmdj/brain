"""Execute the frozen composition component proof slicer against the literal manifest.

This is a zero-reality, zero-credit dependency reduction. The manifest itself
contains no family or receipt bindings. Therefore this execution may only expose
which literal isolated-component interfaces still lack claim-bound scoped proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_components

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
VERIFICATION = "canonical/verification/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"


def _load(rel: str) -> dict[str, Any]:
    v = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(rel)
    return v


def _blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate_live() -> dict[str, Any]:
    manifest = _load(MANIFEST)
    verification = _load(VERIFICATION)
    errors: list[str] = []

    if verification.get("status") != "INDEPENDENT_PUBLIC_RUNNER_PASS__LITERAL_12_INTERFACE_RECOMPUTATION__ZERO_CREDIT":
        errors.append("MANIFEST_INDEPENDENT_VERIFICATION_NOT_PASS")
    exact = verification.get("exact_brain_blobs")
    if not isinstance(exact, dict) or exact.get(MANIFEST) != _blob_sha(MANIFEST):
        errors.append("MANIFEST_BLOB_NOT_EXACTLY_INDEPENDENTLY_VERIFIED")
    if manifest.get("isolated_component_interface_count") != 12:
        errors.append("MANIFEST_INTERFACE_COUNT_NOT_12")
    if manifest.get("family_bindings_complete") is not False:
        errors.append("FAMILY_BINDINGS_UNEXPECTEDLY_COMPLETE")
    if manifest.get("receipt_bindings_complete") is not False:
        errors.append("RECEIPT_BINDINGS_UNEXPECTEDLY_COMPLETE")

    interfaces = manifest.get("interfaces")
    if not isinstance(interfaces, list) or len(interfaces) != 12:
        errors.append("MANIFEST_INTERFACES_INVALID")
        interfaces = []

    slicer_input = {
        "claim_id": manifest.get("claim_id"),
        "interfaces": [
            {
                "component_id": row.get("component_id"),
                "interface_id": row.get("interface_id"),
                "required_properties": row.get("required_properties"),
            }
            for row in interfaces if isinstance(row, dict)
        ],
        "receipts": [],
    }
    sliced = slice_components(slicer_input) if not errors else None
    if sliced is not None:
        if sliced.get("status") != "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN":
            errors.append("SLICER_STATUS_NOT_RESIDUAL_OPEN")
        if sliced.get("all_used_component_interfaces_scoped_proved") is not False:
            errors.append("SLICER_FALSE_CLOSURE")
        rows = sliced.get("interfaces")
        if not isinstance(rows, list) or len(rows) != 12:
            errors.append("SLICER_INTERFACE_COUNT_NOT_12")
        else:
            for row in rows:
                if row.get("state") != "OPEN":
                    errors.append(f"INTERFACE_NOT_OPEN:{row.get('component_id')}::{row.get('interface_id')}")
                if row.get("missing_properties") != ["SCOPED_ACCEPTANCE_PROOF"]:
                    errors.append(f"UNEXPECTED_MISSING_PROPERTIES:{row.get('component_id')}::{row.get('interface_id')}")
                if row.get("supporting_receipt_ids") != []:
                    errors.append(f"UNEXPECTED_RECEIPT_BINDING:{row.get('component_id')}::{row.get('interface_id')}")

    errors = sorted(set(errors))
    residuals = []
    if sliced is not None:
        for row in sliced.get("interfaces", []):
            residuals.append({
                "component_id": row["component_id"],
                "interface_id": row["interface_id"],
                "missing_properties": row["missing_properties"],
                "required_next_binding": "INDEPENDENT_ACCEPTANCE_SCOPED_CLAIM_BOUND_RECEIPT",
            })

    return {
        "schema": "PROJECT_BRAIN_OPUS55_COMPOSITION_COMPONENT_PROOF_SLICER_EXECUTION_V1",
        "status": (
            "PASS__12_LITERAL_COMPONENT_INTERFACES_EXPLICIT__12_SCOPED_PROOF_BINDINGS_OPEN__ZERO_CREDIT"
            if not errors else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "manifest_path": MANIFEST,
        "manifest_git_blob_sha": _blob_sha(MANIFEST),
        "manifest_verification_path": VERIFICATION,
        "interface_count": 12 if not errors else len(interfaces),
        "scoped_proved_interface_count": 0,
        "open_interface_count": 12 if not errors else None,
        "composition_component_predicate_closed": False,
        "family_bindings_complete": False,
        "receipt_bindings_complete": False,
        "residual_component_interface_proofs": residuals,
        "composition_only_interaction_dimensions": manifest.get("composition_only_dimensions", []),
        "next": (
            "BIND_ONLY_INDEPENDENT_ACCEPTANCE_SCOPED_CLAIM_BOUND_RECEIPTS_TO_THE_12_LITERAL_INTERFACES__"
            "RERUN_SLICER__DO_NOT_INFER_BINDINGS_BY_NAME_OR_ANALOGY"
        ),
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "REPRESENTATION_GAP_CLOSED__PROOF_BINDING_GAP_EXPOSED__"
            "NO_COMPONENT_OR_COMPOSITION_ACCEPTANCE_CREDIT"
        ),
    }


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed verifier for independently reproduced composition bridge activation v1.

The activation is a mechanical translation layer. It may authorize only the exact
two component receipts independently reproduced by the public bridge verifier.
It grants no parent composition, capability, family, execution, or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.composition_behavioral_bridge_verifier_v1 import derive as derive_bridge
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_components

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANSMUTATION = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
MANIFEST = ROOT / "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
BRIDGE = ROOT / "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"
PUBLIC_VERIFY = ROOT / "canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BASELINE = ROOT / "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json"
ACTIVATION = ROOT / "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json"

SCHEMA = "PROJECT_BRAIN_COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_VERDICT_V1"


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def _rid(binding: Mapping[str, Any]) -> str:
    component = str(binding["component_id"]).replace(" ", "_")
    return f"COMPOSITION_BRIDGE::{binding['behavior_id']}::{component}"


def expected_receipts(bindings: list[Mapping[str, Any]], claim_id: str) -> list[dict[str, Any]]:
    rows = []
    for b in bindings:
        rows.append({
            "receipt_id": _rid(b),
            "component_id": b["component_id"],
            "interface_id": b["interface_id"],
            "proved_properties": list(b["proved_properties"]),
            "verified": True,
            "independent": True,
            "contamination_clean": True,
            "acceptance_scoped": True,
            "binds_frozen_claim": claim_id,
            "source_family": b["source_family"],
            "behavior_id": b["behavior_id"],
            "source_witness_path": b["source_witness_path"],
            "bridge_verification": "canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        })
    return sorted(rows, key=lambda x: x["receipt_id"])


def evaluate(
    registry: Mapping[str, Any],
    transmutation: Mapping[str, Any],
    manifest: Mapping[str, Any],
    bridge: Mapping[str, Any],
    public_verify: Mapping[str, Any],
    baseline: Mapping[str, Any],
    activation: Mapping[str, Any],
    shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    if activation.get("schema") != "PROJECT_BRAIN_COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1":
        errors.append("ACTIVATION_SCHEMA_MISMATCH")
    claim_id = manifest.get("claim_id")
    if not isinstance(claim_id, str) or activation.get("claim_id") != claim_id or baseline.get("claim_id") != claim_id:
        errors.append("CLAIM_ID_MISMATCH")

    auth = activation.get("authority")
    expected_auth = {
        "bridge": ("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json", shas["bridge"]),
        "independent_verification": ("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json", shas["public_verify"]),
        "baseline_slice_input": ("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json", shas["baseline"]),
    }
    if not isinstance(auth, Mapping):
        errors.append("AUTHORITY_MISSING")
    else:
        for key, (path, sha) in expected_auth.items():
            row = auth.get(key)
            if not isinstance(row, Mapping) or row.get("path") != path or row.get("git_blob_sha") != sha:
                errors.append(f"AUTHORITY_MISMATCH:{key}")

    # The public receipt must bind the exact candidate blob and a successful,
    # merged, independent reproduction. It is the authority that changes the
    # bridge from candidate-only to mechanically activatable.
    if public_verify.get("status") != "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_TWO_COMPONENT_BEHAVIORAL_BRIDGE__ZERO_CREDIT":
        errors.append("PUBLIC_VERIFICATION_STATUS_INVALID")
    exact = public_verify.get("exact_brain_blobs")
    if not isinstance(exact, Mapping) or exact.get("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json") != shas["bridge"]:
        errors.append("PUBLIC_VERIFICATION_BRIDGE_BLOB_MISMATCH")
    runner = public_verify.get("public_runner")
    if not isinstance(runner, Mapping) or runner.get("conclusion") != "success" or not runner.get("merge_commit"):
        errors.append("PUBLIC_RUNNER_NOT_SUCCESSFULLY_MERGED")
    if public_verify.get("derived_binding_count") != 2:
        errors.append("PUBLIC_VERIFICATION_BINDING_COUNT_NOT_TWO")

    derived = derive_bridge(registry, transmutation, manifest)
    actual_bridge = bridge.get("bindings")
    if not isinstance(actual_bridge, list) or sorted(actual_bridge, key=lambda x: (x.get("component_id"), x.get("interface_id"), x.get("behavior_id"))) != derived:
        errors.append("BRIDGE_NO_LONGER_EXACT_RECOMPUTATION")
    if len(derived) != 2 or {x.get("component_id") for x in derived} != {"delegation", "tool discovery"}:
        errors.append("DERIVED_BRIDGE_SET_NOT_EXACT_TWO")

    exp_receipts = expected_receipts(derived, str(claim_id))
    actual_receipts = activation.get("receipts")
    if not isinstance(actual_receipts, list):
        errors.append("ACTIVATION_RECEIPTS_INVALID")
    else:
        actual_sorted = sorted(actual_receipts, key=lambda x: x.get("receipt_id", "") if isinstance(x, Mapping) else "")
        if actual_sorted != exp_receipts:
            errors.append("ACTIVATION_RECEIPTS_NOT_EXACT_TRANSLATION")

    interfaces = baseline.get("interfaces")
    if not isinstance(interfaces, list):
        errors.append("BASELINE_INTERFACES_INVALID")
        slicer = None
    else:
        slicer = slice_components({
            "claim_id": claim_id,
            "interfaces": interfaces,
            "receipts": exp_receipts if not errors else [],
        })
        if not errors:
            states = slicer.get("interfaces", [])
            proved = [x for x in states if x.get("state") == "SCOPED_PROVED"]
            opened = [x for x in states if x.get("state") == "OPEN"]
            if len(proved) != 2 or len(opened) != 10:
                errors.append("SLICER_EXPECTED_TWO_PROVED_TEN_OPEN")
            if {x.get("component_id") for x in proved} != {"delegation", "tool discovery"}:
                errors.append("SLICER_PROVED_COMPONENT_SET_MISMATCH")
            if slicer.get("all_used_component_interfaces_scoped_proved") is not False:
                errors.append("PARENT_COMPONENT_PREDICATE_MUST_REMAIN_OPEN")

    return {
        "schema": SCHEMA,
        "status": "PASS__TWO_CLAIM_BOUND_COMPONENT_RECEIPTS_ACTIVATABLE__TEN_INTERFACES_REMAIN_OPEN__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "activated_receipt_count": 2 if not errors else 0,
        "activated_components": ["delegation", "tool discovery"] if not errors else [],
        "open_component_interface_count": 10 if not errors else None,
        "parent_predicate_closed": False,
        "slicer_preview": slicer if not errors else None,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    docs = {
        "registry": json.loads(REGISTRY.read_text()),
        "transmutation": json.loads(TRANSMUTATION.read_text()),
        "manifest": json.loads(MANIFEST.read_text()),
        "bridge": json.loads(BRIDGE.read_text()),
        "public_verify": json.loads(PUBLIC_VERIFY.read_text()),
        "baseline": json.loads(BASELINE.read_text()),
        "activation": json.loads(ACTIVATION.read_text()),
    }
    out = evaluate(
        docs["registry"], docs["transmutation"], docs["manifest"], docs["bridge"],
        docs["public_verify"], docs["baseline"], docs["activation"],
        {
            "bridge": git_blob_sha(BRIDGE),
            "public_verify": git_blob_sha(PUBLIC_VERIFY),
            "baseline": git_blob_sha(BASELINE),
        },
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed verifier for exact composition behavioral bridge v1."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANSMUTATION = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
MANIFEST = ROOT / "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
BRIDGE = ROOT / "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"
SCHEMA = "PROJECT_BRAIN_COMPOSITION_BEHAVIORAL_BRIDGE_VERDICT_V1"

def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def norm(x: Any) -> str:
    s = str(x or "").lower().replace("_", " ").replace("/", " ")
    return re.sub(r"\s+", " ", s).strip()

def derive(registry: Mapping[str, Any], transmutation: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    residuals = registry.get("active_contracted_residuals")
    fammap = registry.get("family_to_residual_contracts")
    interfaces = manifest.get("interfaces")
    evidence = transmutation.get("evidence")
    if not isinstance(residuals, list) or not isinstance(fammap, Mapping) or not isinstance(interfaces, list) or not isinstance(evidence, list):
        return []
    by_id = {x.get("behavior_id"): x for x in residuals if isinstance(x, Mapping) and isinstance(x.get("behavior_id"), str)}
    composition = fammap.get("MULTI_CAPABILITY_COMPOSITION")
    if not isinstance(composition, list):
        return []
    composition = set(composition)
    closures = []
    for x in evidence:
        if not isinstance(x, Mapping):
            continue
        if (
            x.get("verified") is True
            and x.get("independent") is True
            and x.get("contamination_clean") is True
            and x.get("binds_frozen_protocol") is True
            and x.get("scope_relation") == "PROVEN_STRONGER"
            and x.get("closes_entire_protocol") is True
        ):
            closures.append(x)
    out = []
    for iface in interfaces:
        if not isinstance(iface, Mapping):
            continue
        component = iface.get("component_id")
        interface_id = iface.get("interface_id")
        if not isinstance(component, str) or not isinstance(interface_id, str):
            continue
        for e in closures:
            family = e.get("family")
            if not isinstance(family, str):
                continue
            contracts = fammap.get(family)
            if not isinstance(contracts, list) or len(contracts) != 1:
                continue
            behavior_id = contracts[0]
            if behavior_id not in composition:
                continue
            row = by_id.get(behavior_id)
            if not isinstance(row, Mapping):
                continue
            contract_text = norm(" ".join(str(row.get(k) or "") for k in ("source", "scope", "terminal_consequence")))
            if norm(component) not in contract_text:
                continue
            out.append({
                "component_id": component,
                "interface_id": interface_id,
                "behavior_id": behavior_id,
                "source_family": family,
                "closure_evidence_id": e.get("id"),
                "source_witness_path": e.get("source_witness_path"),
                "independent_verification": e.get("independent_verification"),
                "proved_properties": ["SCOPED_ACCEPTANCE_PROOF"],
            })
    return sorted(out, key=lambda x: (x["component_id"], x["interface_id"], x["behavior_id"]))

def evaluate(registry: Mapping[str, Any], transmutation: Mapping[str, Any], manifest: Mapping[str, Any], bridge: Mapping[str, Any], shas: Mapping[str, str]) -> dict[str, Any]:
    errors: list[str] = []
    if bridge.get("schema") != "PROJECT_BRAIN_COMPOSITION_BEHAVIORAL_BRIDGE_V1":
        errors.append("BRIDGE_SCHEMA_MISMATCH")
    if bridge.get("claim_id") != manifest.get("claim_id"):
        errors.append("CLAIM_ID_MISMATCH")
    auth = bridge.get("authority")
    if not isinstance(auth, Mapping):
        errors.append("AUTHORITY_MISSING")
    else:
        checks = {
            "behavioral_contract_registry": ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", shas["registry"]),
            "acceptance_transmutation": ("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json", shas["transmutation"]),
            "component_manifest": ("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json", shas["manifest"]),
        }
        for key, (path, sha) in checks.items():
            row = auth.get(key)
            if not isinstance(row, Mapping) or row.get("path") != path or row.get("git_blob_sha") != sha:
                errors.append(f"AUTHORITY_MISMATCH:{key}")
    expected = derive(registry, transmutation, manifest)
    actual = bridge.get("bindings")
    actual_sorted = sorted(actual, key=lambda x: (x.get("component_id"), x.get("interface_id"), x.get("behavior_id"))) if isinstance(actual, list) and all(isinstance(x, Mapping) for x in actual) else None
    if actual_sorted != expected:
        errors.append("BINDINGS_NOT_EXACT_RECOMPUTATION")
    state = bridge.get("verification_state")
    if not isinstance(state, Mapping) or state.get("independent_verification") is not False or state.get("slicer_receipt_authorized") is not False:
        errors.append("CANDIDATE_MUST_NOT_SELF_AUTHORIZE")
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_TWO_COMPONENT_BEHAVIORAL_BRIDGE__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "derived_binding_count": len(expected),
        "derived_bindings": expected,
        "slicer_receipt_authorized": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    transmutation = json.loads(TRANSMUTATION.read_text())
    manifest = json.loads(MANIFEST.read_text())
    bridge = json.loads(BRIDGE.read_text())
    out = evaluate(
        registry, transmutation, manifest, bridge,
        {"registry": git_blob_sha(REGISTRY), "transmutation": git_blob_sha(TRANSMUTATION), "manifest": git_blob_sha(MANIFEST)}
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

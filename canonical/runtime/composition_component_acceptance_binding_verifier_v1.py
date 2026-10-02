"""Fail-closed verifier for explicit composition component acceptance bindings v1.

This verifier validates exact source blobs and independently calibrated family
state before deriving receipts for the existing composition proof slicer.
It closes no composition predicate and grants no capability/family credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_evaluate

ROOT = Path(__file__).resolve().parents[2]
BINDINGS = ROOT / "canonical/governance/COMPOSITION_COMPONENT_ACCEPTANCE_BINDINGS_V1.json"

SCHEMA = "PROJECT_BRAIN_COMPOSITION_COMPONENT_ACCEPTANCE_BINDING_VERDICT_V1"


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\\0" + b).hexdigest()


def load_rel(rel: str) -> Mapping[str, Any]:
    p = ROOT / rel
    if not p.is_file():
        raise ValueError(f"MISSING_FILE:{rel}")
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, Mapping):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{rel}")
    return obj


def fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "scoped_proved_component_count": 0,
        "open_component_count": 12,
        "composition_atomic_predicate_closed": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def require_blob(rel: str, expected: str, errors: list[str], label: str) -> Mapping[str, Any] | None:
    try:
        p = ROOT / rel
        if git_blob_sha(p) != expected:
            errors.append(f"{label}_BLOB_SHA_MISMATCH")
            return None
        return load_rel(rel)
    except Exception as exc:
        errors.append(f"{label}_LOAD_ERROR:{type(exc).__name__}")
        return None


def validate_source(binding: Mapping[str, Any], calibrated: set[str], errors: list[str]) -> bool:
    bid = str(binding.get("binding_id", "UNKNOWN"))
    family = binding.get("family")
    if family not in calibrated:
        errors.append(f"{bid}:FAMILY_NOT_IN_CALIBRATED_SET")
        return False

    source_path = binding.get("source_path")
    source_sha = binding.get("source_git_blob_sha")
    if not isinstance(source_path, str) or not isinstance(source_sha, str):
        errors.append(f"{bid}:SOURCE_IDENTITY_MISSING")
        return False
    source = require_blob(source_path, source_sha, errors, f"{bid}:SOURCE")
    if source is None:
        return False

    verification = binding.get("independent_verification")
    if not isinstance(verification, Mapping):
        errors.append(f"{bid}:INDEPENDENT_VERIFICATION_MISSING")
        return False
    vp = verification.get("path")
    vs = verification.get("git_blob_sha")
    if not isinstance(vp, str) or not isinstance(vs, str):
        errors.append(f"{bid}:VERIFICATION_IDENTITY_MISSING")
        return False
    receipt = require_blob(vp, vs, errors, f"{bid}:VERIFICATION")
    if receipt is None:
        return False

    profile = binding.get("source_profile")
    if profile == "ACCEPTANCE_TYPED_WITNESS_V1":
        checks = [
            source.get("schema") == "PROJECT_BRAIN_OPUS55_ACCEPTANCE_TYPED_WITNESS_V1",
            source.get("family") == family,
            source.get("verified") is True,
            source.get("independent") is True,
            source.get("contamination_clean") is True,
            source.get("binds_frozen_protocol") is True,
            source.get("scope_relation") == "PROVEN_STRONGER",
            source.get("closes_entire_protocol") is True,
            isinstance(source.get("result"), Mapping),
            source.get("result", {}).get("brain_lower_bound") == source.get("result", {}).get("theoretical_upper_bound"),
        ]
        if not all(checks):
            errors.append(f"{bid}:TYPED_WITNESS_NOT_ADMISSIBLE")
            return False
        if verification.get("profile") != "PUBLIC_RUNNER_V1":
            errors.append(f"{bid}:PUBLIC_RUNNER_PROFILE_REQUIRED")
            return False
        if not str(receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
            errors.append(f"{bid}:PUBLIC_RUNNER_NOT_PASS")
            return False
        return True

    if profile == "OWNERSHIP_PACKAGE_V1":
        decision = source.get("decision")
        tests = source.get("ownership_tests")
        fresh = source.get("fresh_verification")
        adjudication = source.get("independent_adjudication")
        checks = [
            source.get("schema") == "PROJECT_BRAIN_OPUS55_CAPABILITY_OWNERSHIP_PACKAGE_V1",
            source.get("family") == family,
            source.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER",
            isinstance(decision, Mapping) and decision.get("parent_family_closed_for_claim_scope") is True,
            isinstance(tests, Mapping) and all(v == "PASS" or (isinstance(v, str) and v.startswith("PASS__")) for v in tests.values()),
            isinstance(fresh, Mapping) and str(fresh.get("conclusion", "")).upper() == "SUCCESS",
            isinstance(adjudication, Mapping) and adjudication.get("all_checks_pass") is True,
            isinstance(adjudication, Mapping) and adjudication.get("path") == vp,
        ]
        if not all(checks):
            errors.append(f"{bid}:OWNERSHIP_PACKAGE_NOT_ADMISSIBLE")
            return False
        if verification.get("profile") != "CLEANROOM_ADJUDICATION_V1":
            errors.append(f"{bid}:CLEANROOM_PROFILE_REQUIRED")
            return False
        if receipt.get("all_checks_pass") is not True or receipt.get("trust_executor_claims") is not False:
            errors.append(f"{bid}:CLEANROOM_ADJUDICATION_NOT_PASS")
            return False
        return True

    errors.append(f"{bid}:UNKNOWN_SOURCE_PROFILE")
    return False


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if doc.get("schema") != "PROJECT_BRAIN_COMPOSITION_COMPONENT_ACCEPTANCE_BINDINGS_V1":
        errors.append("BINDING_SCHEMA_MISMATCH")

    claim_id = doc.get("claim_id")
    if claim_id != "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1":
        errors.append("CLAIM_ID_MISMATCH")

    manifest_ref = doc.get("source_manifest")
    protocol_ref = doc.get("protocol_authority")
    calibration_ref = doc.get("calibration_authority")
    for name, ref in (("MANIFEST", manifest_ref), ("PROTOCOL", protocol_ref), ("CALIBRATION", calibration_ref)):
        if not isinstance(ref, Mapping) or not isinstance(ref.get("path"), str) or not isinstance(ref.get("git_blob_sha"), str):
            errors.append(f"{name}_AUTHORITY_INVALID")

    if errors:
        return fail(*errors)

    manifest = require_blob(manifest_ref["path"], manifest_ref["git_blob_sha"], errors, "MANIFEST")
    protocol = require_blob(protocol_ref["path"], protocol_ref["git_blob_sha"], errors, "PROTOCOL")
    calibration = require_blob(calibration_ref["path"], calibration_ref["git_blob_sha"], errors, "CALIBRATION")
    if manifest is None or protocol is None or calibration is None:
        return fail(*errors)

    if manifest.get("claim_id") != claim_id:
        errors.append("MANIFEST_CLAIM_MISMATCH")
    if manifest.get("isolated_component_interface_count") != 12:
        errors.append("MANIFEST_COMPONENT_COUNT_MISMATCH")

    protocols = protocol.get("protocols")
    if not isinstance(protocols, list):
        errors.append("PROTOCOL_LIST_INVALID")
        return fail(*errors)
    protocol_rows = {x.get("family"): x for x in protocols if isinstance(x, Mapping)}
    composition = protocol_rows.get("MULTI_CAPABILITY_COMPOSITION")
    if not isinstance(composition, Mapping):
        errors.append("COMPOSITION_PROTOCOL_MISSING")
    else:
        acc = str(composition.get("acceptance", ""))
        if "Every isolated component used in the claim has its own scoped proof" not in acc:
            errors.append("COMPOSITION_SCOPED_COMPONENT_RULE_MISSING")

    expected_calibrated = calibration_ref.get("exact_calibrated_families")
    actual_calibrated = calibration.get("result", {}).get("acceptance_calibrated_families")
    if actual_calibrated != expected_calibrated:
        errors.append("CALIBRATED_FAMILY_SET_MISMATCH")
    calibrated = set(actual_calibrated or [])

    interfaces = manifest.get("interfaces")
    if not isinstance(interfaces, list):
        errors.append("MANIFEST_INTERFACES_INVALID")
        return fail(*errors)
    frozen_pairs = {
        (x.get("component_id"), x.get("interface_id")): tuple(x.get("required_properties", []))
        for x in interfaces if isinstance(x, Mapping)
    }

    receipts = []
    seen = set()
    bindings = doc.get("bindings")
    if not isinstance(bindings, list):
        return fail("BINDINGS_INVALID")

    for row in bindings:
        if not isinstance(row, Mapping):
            errors.append("BINDING_ROW_INVALID")
            continue
        bid = row.get("binding_id")
        if not isinstance(bid, str) or not bid or bid in seen:
            errors.append("BINDING_ID_INVALID_OR_DUPLICATE")
            continue
        seen.add(bid)
        pair = (row.get("component_id"), row.get("interface_id"))
        required = frozen_pairs.get(pair)
        proved = tuple(row.get("proved_properties", []))
        if required is None:
            errors.append(f"{bid}:PAIR_NOT_IN_FROZEN_MANIFEST")
            continue
        if tuple(required) != proved:
            errors.append(f"{bid}:PROVED_PROPERTIES_NOT_EXACT_REQUIRED_SET")
            continue

        family = row.get("family")
        family_protocol = protocol_rows.get(family)
        if not isinstance(family_protocol, Mapping):
            errors.append(f"{bid}:FAMILY_PROTOCOL_MISSING")
            continue
        if family_protocol.get("status") not in ("PASS", "DEFINED_RESULT_OPEN"):
            errors.append(f"{bid}:FAMILY_PROTOCOL_STATE_INVALID")
            continue

        if not validate_source(row, calibrated, errors):
            continue

        receipts.append({
            "receipt_id": bid,
            "component_id": pair[0],
            "interface_id": pair[1],
            "proved_properties": list(proved),
            "verified": True,
            "independent": True,
            "contamination_clean": True,
            "acceptance_scoped": True,
            "binds_frozen_claim": claim_id,
        })

    if errors:
        return fail(*errors)

    slicer_input = {
        "claim_id": claim_id,
        "interfaces": [
            {
                "component_id": x["component_id"],
                "interface_id": x["interface_id"],
                "required_properties": x["required_properties"],
            }
            for x in interfaces
        ],
        "receipts": receipts,
    }
    sliced = slice_evaluate(slicer_input)
    proved_rows = [x for x in sliced.get("interfaces", []) if x.get("state") == "SCOPED_PROVED"]
    open_rows = [x for x in sliced.get("interfaces", []) if x.get("state") == "OPEN"]
    proved_ids = sorted(x["component_id"] for x in proved_rows)
    expected_ids = sorted(["memory", "tool discovery", "delegation"])

    if proved_ids != expected_ids:
        errors.append("UNEXPECTED_PROVED_COMPONENT_SET")
    if len(open_rows) != 9:
        errors.append("OPEN_COMPONENT_COUNT_NOT_9")
    if sliced.get("all_used_component_interfaces_scoped_proved") is not False:
        errors.append("COMPOSITION_MUST_REMAIN_OPEN")

    if errors:
        return fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_3_OF_12_EXISTING_ACCEPTANCE_PROOFS_REUSED__9_COMPONENTS_REMAIN_OPEN__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "scoped_proved_component_count": 3,
        "scoped_proved_components": proved_ids,
        "open_component_count": 9,
        "open_components": sorted(x["component_id"] for x in open_rows),
        "composition_atomic_predicate_closed": False,
        "slicer_status": sliced.get("status"),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    doc = json.loads(BINDINGS.read_text(encoding="utf-8"))
    out = evaluate(doc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

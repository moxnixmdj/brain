"""Verifier for normalized strict P3 binary top-law policy adequacy.

This does not create new adequacy. It checks that the standard policy-adequacy
certificate is an exact normalization of the already independently verified
strict P3 binary top-law region.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from canonical.runtime.p3_binary_explicit_top_law_region_verifier_v1 import (
    verify as verify_region,
)

SCHEMA = "PROJECT_BRAIN_P3_BINARY_TOP_LAW_POLICY_ADEQUACY_VERIFIER_V1"
ROOT = Path(__file__).resolve().parents[2]

CERT_PATH = "canonical/governance/P3_BINARY_TOP_LAW_POLICY_ADEQUACY_CERTIFICATE_20261008_V1.json"
CERT_BLOB = "7b27ac7bce607651c71e395aa275317761ddea7a"
REGION_PATH = "canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_20261008_V1.json"
REGION_BLOB = "e367ff0a5734e2430b0b5476bf073b4688c410e1"
REGION_VERIFIER_PATH = "canonical/runtime/p3_binary_explicit_top_law_region_verifier_v1.py"
REGION_VERIFIER_BLOB = "da871727e5939b5c190e9c383d6c361642168b80"
REGION_VERIFY_PATH = "canonical/verification/P3_BINARY_EXPLICIT_TOP_LAW_REGION_TWO_SPRITE_VERIFICATION_20261008_V1.json"
REGION_VERIFY_BLOB = "05dd31a787eccec0311c8abd26f21c624d4deb66"
POLICY_PATH = "canonical/runtime/p3_binary_decision_grounded_expression_v1.py"
POLICY_BLOB = "590cdc4e7f5a513d0e40bb31afed20df61826bad"
MEMBERSHIP_PATH = "canonical/runtime/p3_binary_explicit_contract_membership_v1.py"
MEMBERSHIP_BLOB = "ca24d891210fb6d885a959c26a9da3451a8b67c7"

POLICY_ID = "P3_BOUND_BINARY_GROUNDED_DECISION_TOP_LAW_POLICY_V1"
CONDITION = {"op": "ATOM", "id": "P3_BOUND_BINARY_EXPLICIT_TOP_LAW_MEMBERSHIP_V1"}


def _blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def verify() -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        CERT_PATH: CERT_BLOB,
        REGION_PATH: REGION_BLOB,
        REGION_VERIFIER_PATH: REGION_VERIFIER_BLOB,
        REGION_VERIFY_PATH: REGION_VERIFY_BLOB,
        POLICY_PATH: POLICY_BLOB,
        MEMBERSHIP_PATH: MEMBERSHIP_BLOB,
    }
    for path, want in expected.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("MISSING:" + path)
            continue
        got = _blob(path)
        if got != want:
            errors.append("DRIFT:" + path + ":" + got)

    if errors:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": errors,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    cert = json.loads((ROOT / CERT_PATH).read_text(encoding="utf-8"))
    if cert.get("schema") != "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1":
        errors.append("CERT_SCHEMA")
    if cert.get("policy_id") != POLICY_ID:
        errors.append("POLICY_ID")
    if cert.get("policy_condition") != CONDITION:
        errors.append("POLICY_CONDITION")
    condition_sha = sha256(_canon(CONDITION).encode("utf-8")).hexdigest()
    if cert.get("policy_condition_sha256") != condition_sha:
        errors.append("POLICY_CONDITION_SHA")
    if cert.get("adequacy_proved") is not True:
        errors.append("ADEQUACY_NOT_PROVED")
    if cert.get("brain_owned") is not True:
        errors.append("BRAIN_OWNED_FALSE")
    if cert.get("load_bearing_constraints_preserved") is not True:
        errors.append("LOAD_BEARING_CONSTRAINTS_FALSE")
    if cert.get("membership_self_certified") is not False:
        errors.append("MEMBERSHIP_SELF_CERTIFICATION")
    if cert.get("root_task_authority_self_proved") is not False:
        errors.append("ROOT_AUTHORITY_SELF_CERTIFICATION")
    if cert.get("terminal_authority") is not False:
        errors.append("TERMINAL_AUTHORITY_OVERCLAIM")

    if (cert.get("exact_policy") or {}).get("git_blob_sha") != POLICY_BLOB:
        errors.append("CERT_POLICY_BLOB")
    if (cert.get("adequacy_region") or {}).get("git_blob_sha") != REGION_BLOB:
        errors.append("CERT_REGION_BLOB")
    if (cert.get("region_verifier") or {}).get("git_blob_sha") != REGION_VERIFIER_BLOB:
        errors.append("CERT_REGION_VERIFIER_BLOB")
    if (cert.get("independent_region_verification") or {}).get("git_blob_sha") != REGION_VERIFY_BLOB:
        errors.append("CERT_REGION_VERIFY_BLOB")
    if (cert.get("membership_recognizer") or {}).get("git_blob_sha") != MEMBERSHIP_BLOB:
        errors.append("CERT_MEMBERSHIP_BLOB")

    region = verify_region()
    if region.get("pass") is not True:
        errors.append("REGION_VERIFIER_FAIL")
    if region.get("parameterized_D_B_region_candidate") is not True:
        errors.append("REGION_NOT_PARAMETERIZED")
    if region.get("whole_p3_closed") is not False or region.get("u_empty") is not False:
        errors.append("REGION_SCOPE_OVERCLAIM")

    independent = json.loads((ROOT / REGION_VERIFY_PATH).read_text(encoding="utf-8"))
    if not str(independent.get("status") or "").startswith("PASS_ON_TWO_SPRITES__"):
        errors.append("INDEPENDENT_REGION_STATUS")
    rows = independent.get("verification")
    if not isinstance(rows, list) or len(rows) != 2 or any(x.get("result") != "PASS" for x in rows):
        errors.append("INDEPENDENT_REGION_TWO_SPRITE_PASS")
    verified = independent.get("verified")
    if not isinstance(verified, dict):
        errors.append("INDEPENDENT_REGION_VERIFIED_BODY")
    else:
        for key in (
            "exact_region_bytes",
            "explicit_membership_20_of_20_two_sprite_receipt",
            "binary_expression_11_of_11_two_sprite_receipt",
            "no_caller_membership_flag_or_semantic_extractor",
            "explicit_selection_order_top_law_common_policy",
            "target_comparator_required",
            "p3_required_checks_imply_synthesis_contract_success",
            "parameterized_D_B_region_candidate",
        ):
            expected_value = False if key == "target_comparator_required" else True
            if verified.get(key) is not expected_value:
                errors.append("INDEPENDENT_REGION_PROPERTY:" + key)
        if verified.get("whole_p3_closed") is not False or verified.get("u_empty") is not False:
            errors.append("INDEPENDENT_REGION_SCOPE_OVERCLAIM")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__P3_BINARY_TOP_LAW_POLICY_ADEQUACY_NORMALIZATION_VERIFIED"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": errors,
        "policy_id": POLICY_ID,
        "policy_condition": CONDITION,
        "policy_condition_sha256": condition_sha,
        "adequacy_certificate_path": CERT_PATH,
        "adequacy_certificate_blob_sha": CERT_BLOB,
        "brain_owned": not errors,
        "load_bearing_constraints_preserved": not errors,
        "root_task_authority_self_proved": False,
        "whole_p3_closed": False,
        "u_empty": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)

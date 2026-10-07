"""Authenticate upstream quality bindings for the P2 strong-visible certifier.

Every quality claim must be carried by:
1. a content-addressed JSON receipt at a canonical repository path;
2. a separate content-addressed independent-verification JSON receipt;
3. exact binding to the normalized P2 context SHA256 and receipt Git blob SHA.

This module validates receipt identity and schema/binding. The independent verifier
is the truth authority for the receipt claim; opaque caller strings cannot substitute.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "BRAIN_P2_QUALITY_BINDING_AUTHENTICATOR_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_P2_QUALITY_BINDING_RECEIPT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_P2_QUALITY_BINDING_INDEPENDENT_VERIFICATION_V1"

KINDS = {
    "BASELINE_LAYOUT_NONOBSCURING",
    "EMPTY_BASELINE_EQUIVALENCE",
    "BOUND_BASELINE",
    "ABLATION_RESCUE_SEMANTICS",
    "RUBRIC_EQUIVALENCE",
    "TARGET_COMPARISON_ORDER",
    "NATIVE_GATE_REQUIREMENT",
    "NATIVE_MECHANICAL_GATE_PASS",
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "quality_binding": None,
        "terminal_authority": False,
    }


def _verify_pair(
    kind: str,
    pair: Mapping[str, Any],
    *,
    context_sha256: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError("QUALITY_BINDING_KIND_UNKNOWN:" + kind)
    if not isinstance(pair, Mapping):
        raise ValueError("QUALITY_BINDING_PAIR_INVALID:" + kind)

    receipt = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
    verify = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    rd = receipt["document"]
    vd = verify["document"]

    if rd.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("RECEIPT_SCHEMA_INVALID:" + kind)
    if rd.get("kind") != kind:
        raise ValueError("RECEIPT_KIND_MISMATCH:" + kind)
    if rd.get("context_sha256") != context_sha256:
        raise ValueError("RECEIPT_CONTEXT_MISMATCH:" + kind)
    if rd.get("pass") is not True:
        raise ValueError("RECEIPT_NOT_PASS:" + kind)
    claim = rd.get("claim")
    if not isinstance(claim, Mapping):
        raise ValueError("RECEIPT_CLAIM_INVALID:" + kind)

    if vd.get("schema") != VERIFY_SCHEMA:
        raise ValueError("VERIFY_SCHEMA_INVALID:" + kind)
    if vd.get("kind") != kind:
        raise ValueError("VERIFY_KIND_MISMATCH:" + kind)
    if vd.get("context_sha256") != context_sha256:
        raise ValueError("VERIFY_CONTEXT_MISMATCH:" + kind)
    if vd.get("subject_git_blob_sha") != receipt["git_blob_sha"]:
        raise ValueError("VERIFY_SUBJECT_BLOB_MISMATCH:" + kind)
    if vd.get("pass") is not True:
        raise ValueError("INDEPENDENT_VERIFY_NOT_PASS:" + kind)
    verifier_id = vd.get("verifier_id")
    if not isinstance(verifier_id, str) or not verifier_id.strip():
        raise ValueError("INDEPENDENT_VERIFIER_ID_MISSING:" + kind)

    return {
        "kind": kind,
        "claim": dict(claim),
        "receipt_path": receipt["path"],
        "receipt_git_blob_sha": receipt["git_blob_sha"],
        "verification_path": verify["path"],
        "verification_git_blob_sha": verify["git_blob_sha"],
        "verifier_id": verifier_id.strip(),
    }


def authenticate(
    bindings: Any,
    *,
    context_sha256: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(bindings, Mapping):
        return _fail("QUALITY_BINDINGS_NOT_OBJECT")
    if not isinstance(context_sha256, str) or len(context_sha256) != 64:
        return _fail("CONTEXT_SHA256_INVALID")

    errors: list[str] = []
    rows: dict[str, dict[str, Any]] = {}
    for kind, pair in bindings.items():
        try:
            rows[str(kind)] = _verify_pair(
                str(kind), pair, context_sha256=context_sha256, repo_root=repo_root
            )
        except (Exception, ReceiptResolutionError) as exc:
            errors.append(type(exc).__name__ + ":" + str(exc))

    required = {
        "BASELINE_LAYOUT_NONOBSCURING",
        "ABLATION_RESCUE_SEMANTICS",
        "NATIVE_GATE_REQUIREMENT",
    }
    for missing in sorted(required - set(rows)):
        errors.append("REQUIRED_QUALITY_BINDING_MISSING:" + missing)

    baseline_modes = [
        k for k in ("EMPTY_BASELINE_EQUIVALENCE", "BOUND_BASELINE") if k in rows
    ]
    if len(baseline_modes) != 1:
        errors.append("EXACTLY_ONE_BASELINE_MODE_REQUIRED")

    order_modes = [
        k for k in ("RUBRIC_EQUIVALENCE", "TARGET_COMPARISON_ORDER") if k in rows
    ]
    if len(order_modes) != 1:
        errors.append("EXACTLY_ONE_QUALITY_ORDER_MODE_REQUIRED")

    if errors:
        return _fail(*errors)

    qb: dict[str, Any] = {}
    authenticated: list[dict[str, Any]] = []

    def claim(kind: str) -> Mapping[str, Any]:
        authenticated.append(rows[kind])
        return rows[kind]["claim"]

    c = claim("BASELINE_LAYOUT_NONOBSCURING")
    if c.get("baseline_layout_nonobscuring") is not True:
        return _fail("BASELINE_LAYOUT_CLAIM_INVALID")
    qb["baseline_layout_nonobscuring"] = True
    qb["baseline_layout_receipt"] = rows["BASELINE_LAYOUT_NONOBSCURING"]["receipt_git_blob_sha"]

    c = claim("ABLATION_RESCUE_SEMANTICS")
    if c.get("ablation_rescue_semantics_bound_to_certifier_policy") is not True:
        return _fail("ABLATION_RESCUE_CLAIM_INVALID")
    if c.get("policy") != "REMOVE_MAXIMUM_MARGINAL_VALUE_SELECTED_EDIT__LEXICAL_TIE_BREAK":
        return _fail("ABLATION_RESCUE_POLICY_MISMATCH")
    qb["ablation_rescue_semantics_bound_to_certifier_policy"] = True
    qb["ablation_rescue_semantics_receipt"] = rows["ABLATION_RESCUE_SEMANTICS"]["receipt_git_blob_sha"]

    baseline = baseline_modes[0]
    c = claim(baseline)
    if baseline == "EMPTY_BASELINE_EQUIVALENCE":
        if c.get("mechanics_only_baseline_equals_empty_p2_plan") is not True:
            return _fail("EMPTY_BASELINE_CLAIM_INVALID")
        qb["mechanics_only_baseline_equals_empty_p2_plan"] = True
        qb["mechanics_only_baseline_equivalence_receipt"] = rows[baseline]["receipt_git_blob_sha"]
    else:
        if c.get("mechanics_baseline_bound") is not True:
            return _fail("BOUND_BASELINE_CLAIM_INVALID")
        bid = c.get("mechanics_baseline_id")
        if not isinstance(bid, str) or not bid.strip():
            return _fail("BOUND_BASELINE_ID_INVALID")
        qb["mechanics_baseline_bound"] = True
        qb["mechanics_baseline_id"] = bid.strip()
        qb["mechanics_baseline_binding_receipt"] = rows[baseline]["receipt_git_blob_sha"]

    order = order_modes[0]
    c = claim(order)
    if order == "RUBRIC_EQUIVALENCE":
        if c.get("explicit_rubric_equivalent_to_p2_objective") is not True:
            return _fail("RUBRIC_EQUIVALENCE_CLAIM_INVALID")
        qb["explicit_rubric_equivalent_to_p2_objective"] = True
        qb["rubric_equivalence_receipt"] = rows[order]["receipt_git_blob_sha"]
    else:
        if c.get("target_comparison_order_bound") is not True:
            return _fail("TARGET_COMPARISON_ORDER_CLAIM_INVALID")
        co = c.get("comparison_order")
        if not isinstance(co, Mapping):
            return _fail("TARGET_COMPARISON_ORDER_INVALID")
        required_co = {
            "selected_edit_ids",
            "baseline_id",
            "ablated_edit_id",
            "selected_gt_baseline",
            "selected_gt_ablated",
            "rescue_eq_selected",
        }
        if set(co) != required_co:
            return _fail("TARGET_COMPARISON_ORDER_KEYS_INVALID")
        if not isinstance(co.get("selected_edit_ids"), list):
            return _fail("TARGET_COMPARISON_SELECTED_IDS_INVALID")
        for key in ("selected_gt_baseline", "selected_gt_ablated", "rescue_eq_selected"):
            if co.get(key) is not True:
                return _fail("TARGET_COMPARISON_REQUIRED_TRUE:" + key)
        qb["target_comparison_order_bound"] = True
        qb["target_comparison_order_receipt"] = rows[order]["receipt_git_blob_sha"]
        qb["comparison_order"] = dict(co)

    c = claim("NATIVE_GATE_REQUIREMENT")
    native_required = c.get("native_mechanical_gate_required")
    if type(native_required) is not bool:
        return _fail("NATIVE_GATE_REQUIREMENT_CLAIM_INVALID")
    qb["native_mechanical_gate_required"] = native_required
    if native_required:
        if "NATIVE_MECHANICAL_GATE_PASS" not in rows:
            return _fail("NATIVE_MECHANICAL_GATE_PASS_BINDING_REQUIRED")
        c2 = claim("NATIVE_MECHANICAL_GATE_PASS")
        if c2.get("native_mechanical_gate_pass") is not True:
            return _fail("NATIVE_MECHANICAL_GATE_PASS_CLAIM_INVALID")
        qb["native_mechanical_gate_pass"] = True
        qb["native_mechanical_gate_receipt"] = rows["NATIVE_MECHANICAL_GATE_PASS"]["receipt_git_blob_sha"]
    elif "NATIVE_MECHANICAL_GATE_PASS" in rows:
        return _fail("UNNEEDED_NATIVE_GATE_PASS_BINDING_PRESENT")

    return {
        "schema": SCHEMA,
        "status": "PASS__CONTENT_ADDRESSED_INDEPENDENTLY_VERIFIED_P2_QUALITY_BINDINGS",
        "pass": True,
        "errors": [],
        "context_sha256": context_sha256,
        "quality_binding": qb,
        "authenticated_bindings": sorted(authenticated, key=lambda x: x["kind"]),
        "terminal_authority": False,
    }

#!/usr/bin/env python3
"""Shared fail-closed verifier for common objective-route proof certificates.

This verifier intentionally checks only invariants that are structurally identical
across frozen objective routes. Domain semantics remain the responsibility of each
route's residual validator. Passing this verifier grants no execution, promotion,
capability, family, or terminal-result authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

MANIFEST = "canonical/governance/OBJECTIVE_ROUTE_CERTIFICATE_BASIS_V1.json"
SCHEMA = "PROJECT_BRAIN_OBJECTIVE_ROUTE_CERTIFICATE_BASIS_V1"
OUT_SCHEMA = "PROJECT_BRAIN_OBJECTIVE_ROUTE_CERTIFICATE_VERIFICATION_V1"
KERNEL_PROTOCOL = "GLOBAL_TERMINAL_SELECTION_KERNEL_V1"
COMMON_TRUE_GATES = (
    "candidate_package_frozen",
    "executable_evaluator_bound",
    "population_or_source_pool_frozen",
    "information_boundary_frozen",
    "post_freeze_selector_frozen",
    "terminal_parent_binding_frozen",
)
SELECTOR_FALSE_FIELDS = (
    "beacon_known_before_freeze",
    "adaptive_case_selection",
    "case_replacement",
    "tuning_replay",
)
ZERO_FIELDS = (
    "terminal_results_observed",
    "fresh_terminal_evidence_consumed",
    "capability_credit_delta",
    "family_credit_delta",
)


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("NOT_OBJECT")
    return obj


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def validate_manifest(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []

    if manifest.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")

    kernel = manifest.get("selection_kernel")
    if not isinstance(kernel, Mapping):
        return _fail("SELECTION_KERNEL_MANIFEST_INVALID")
    kernel_path = kernel.get("path")
    kernel_sha = kernel.get("blob_sha")
    if not isinstance(kernel_path, str) or not kernel_path:
        errors.append("SELECTION_KERNEL_PATH_INVALID")
    if not isinstance(kernel_sha, str) or not kernel_sha:
        errors.append("SELECTION_KERNEL_SHA_INVALID")
    if errors:
        return _fail(*errors)

    kp = root / kernel_path
    if not kp.is_file():
        return _fail("SELECTION_KERNEL_FILE_MISSING")
    observed_kernel_sha = _blob_sha(kp)
    if observed_kernel_sha != kernel_sha:
        errors.append("SELECTION_KERNEL_SHA_MISMATCH")

    routes = manifest.get("routes")
    if not isinstance(routes, list) or not routes:
        return _fail("ROUTES_INVALID")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, route in enumerate(routes):
        if not isinstance(route, Mapping):
            errors.append(f"ROUTE_NOT_OBJECT:{index}")
            continue

        bid = route.get("behavior_id")
        binding_path = route.get("binding_path")
        expected_binding_sha = route.get("binding_blob_sha")
        residual_validator = route.get("residual_validator")
        residual_tests = route.get("residual_tests")

        if not isinstance(bid, str) or not bid:
            errors.append(f"BEHAVIOR_ID_INVALID:{index}")
            continue
        if bid in seen:
            errors.append(f"BEHAVIOR_ID_DUPLICATE:{bid}")
        seen.add(bid)

        if not isinstance(binding_path, str) or not binding_path:
            errors.append(f"{bid}:BINDING_PATH_INVALID")
            continue
        if not isinstance(expected_binding_sha, str) or not expected_binding_sha:
            errors.append(f"{bid}:BINDING_SHA_INVALID")
            continue

        bp = root / binding_path
        if not bp.is_file():
            errors.append(f"{bid}:BINDING_FILE_MISSING")
            continue

        observed_binding_sha = _blob_sha(bp)
        if observed_binding_sha != expected_binding_sha:
            errors.append(f"{bid}:BINDING_SHA_MISMATCH")

        try:
            binding = _read(bp)
        except Exception as exc:
            errors.append(f"{bid}:BINDING_READ_FAILURE:{type(exc).__name__}")
            continue

        if binding.get("behavior_id") != bid:
            errors.append(f"{bid}:BEHAVIOR_ID_MISMATCH")

        for authority_field in ("execution_authority", "promotion_authority"):
            if binding.get(authority_field) is not False:
                errors.append(f"{bid}:{authority_field.upper()}_NOT_FALSE")
        for zero_field in ZERO_FIELDS:
            if binding.get(zero_field) != 0:
                errors.append(f"{bid}:{zero_field.upper()}_NOT_ZERO")

        gates = binding.get("route_gates")
        if not isinstance(gates, Mapping):
            errors.append(f"{bid}:ROUTE_GATES_INVALID")
            gates = {}
        for gate in COMMON_TRUE_GATES:
            if gates.get(gate) is not True:
                errors.append(f"{bid}:COMMON_GATE_NOT_TRUE:{gate}")
        independent = gates.get("independent_verification_pass")
        if not isinstance(independent, bool):
            errors.append(f"{bid}:INDEPENDENT_VERIFICATION_GATE_NOT_BOOLEAN")
        elif binding.get("prewave_admissible") is not independent:
            errors.append(f"{bid}:PREWAVE_ADMISSIBILITY_VERIFICATION_STATE_MISMATCH")

        selector = binding.get("selector")
        if not isinstance(selector, Mapping):
            errors.append(f"{bid}:SELECTOR_INVALID")
            selector = {}
        if selector.get("protocol") != KERNEL_PROTOCOL:
            errors.append(f"{bid}:SELECTOR_PROTOCOL_NOT_IMMUTABLE_KERNEL")
        for field in SELECTOR_FALSE_FIELDS:
            if selector.get(field) is not False:
                errors.append(f"{bid}:SELECTOR_FIELD_NOT_FALSE:{field}")

        bound = binding.get("exact_bound_blobs")
        if not isinstance(bound, Mapping):
            errors.append(f"{bid}:EXACT_BOUND_BLOBS_INVALID")
            bound = {}
        kernel_bound = bound.get("selection_kernel")
        if not isinstance(kernel_bound, Mapping):
            errors.append(f"{bid}:SELECTION_KERNEL_NOT_EXACT_BOUND")
        else:
            if kernel_bound.get("path") != kernel_path:
                errors.append(f"{bid}:SELECTION_KERNEL_PATH_MISMATCH")
            if kernel_bound.get("blob_sha") != kernel_sha:
                errors.append(f"{bid}:SELECTION_KERNEL_BOUND_SHA_MISMATCH")

        selection_semantics = binding.get("selection_semantics")
        if not isinstance(selection_semantics, Mapping):
            errors.append(f"{bid}:SELECTION_SEMANTICS_INVALID")
        else:
            if selection_semantics.get("kernel") != kernel_path:
                errors.append(f"{bid}:SELECTION_SEMANTICS_KERNEL_PATH_MISMATCH")
            if selection_semantics.get("kernel_blob_sha") != kernel_sha:
                errors.append(f"{bid}:SELECTION_SEMANTICS_KERNEL_SHA_MISMATCH")

        info = binding.get("information_boundary")
        if not isinstance(info, Mapping):
            errors.append(f"{bid}:INFORMATION_BOUNDARY_INVALID")
            info = {}
        if binding.get("candidate_receives_hidden_oracle") is True or info.get("candidate_receives_hidden_oracle") is True:
            errors.append(f"{bid}:CANDIDATE_RECEIVES_HIDDEN_ORACLE")
        hidden = info.get("hidden_from_candidate")
        if not isinstance(hidden, list) or not hidden:
            errors.append(f"{bid}:HIDDEN_INFORMATION_SET_EMPTY")

        exact_blob_mismatches: list[str] = []
        for label, item in bound.items():
            if not isinstance(item, Mapping):
                errors.append(f"{bid}:BOUND_BLOB_INVALID:{label}")
                continue
            rel = item.get("path")
            sha = item.get("blob_sha")
            if not isinstance(rel, str) or not rel or not isinstance(sha, str) or not sha:
                errors.append(f"{bid}:BOUND_BLOB_DECLARATION_INVALID:{label}")
                continue
            p = root / rel
            if not p.is_file():
                errors.append(f"{bid}:BOUND_BLOB_FILE_MISSING:{label}")
                continue
            got = _blob_sha(p)
            if got != sha:
                exact_blob_mismatches.append(label)
                errors.append(f"{bid}:BOUND_BLOB_SHA_MISMATCH:{label}")

        for kind, rel in (("RESIDUAL_VALIDATOR", residual_validator), ("RESIDUAL_TESTS", residual_tests)):
            if not isinstance(rel, str) or not rel or not (root / rel).is_file():
                errors.append(f"{bid}:{kind}_MISSING")

        rows.append(
            {
                "behavior_id": bid,
                "binding_path": binding_path,
                "binding_blob_sha": observed_binding_sha,
                "independent_verification_pass": independent if isinstance(independent, bool) else None,
                "prewave_admissible": binding.get("prewave_admissible"),
                "exact_bound_blob_count": len(bound),
                "exact_bound_blob_mismatches": sorted(exact_blob_mismatches),
                "residual_validator": residual_validator,
                "residual_tests": residual_tests,
            }
        )

    if errors:
        return {**_fail(*errors), "routes": rows}

    return {
        "schema": OUT_SCHEMA,
        "status": "PASS_COMMON_CERTIFICATE_BASIS__RESIDUAL_VALIDATION_STILL_REQUIRED",
        "pass": True,
        "exact": True,
        "selection_kernel": {
            "path": kernel_path,
            "blob_sha": observed_kernel_sha,
        },
        "route_count": len(rows),
        "routes": rows,
        "common_invariants_verified_once": list(manifest.get("common_invariants") or []),
        "semantic_projection_authorized": False,
        "residual_validation_required": True,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
        "rule": "COMMON_STRUCTURAL_INVARIANTS_ARE_QUOTIENTED_ONCE__DOMAIN_SPECIFIC_SEMANTICS_REMAIN_RESIDUAL__NO_CROSS_BEHAVIOR_SCORE_OR_SEMANTIC_INHERITANCE",
    }


def validate(root: Path, manifest_path: str = MANIFEST) -> dict[str, Any]:
    root = root.resolve()
    try:
        manifest = _read(root / manifest_path)
    except Exception as exc:
        return _fail("MANIFEST_READ_FAILURE:" + type(exc).__name__)
    return validate_manifest(root, manifest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    ap.add_argument("--manifest", default=MANIFEST)
    args = ap.parse_args()
    out = validate(args.root, args.manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

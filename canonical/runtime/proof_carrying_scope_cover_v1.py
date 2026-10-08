"""Fail-closed proof-carrying positive-adequacy scope-cover compiler.

This module closes the logical gap between:
  (a) deleting a benchmark as an execution route because its attributed behavioral
      obligations have replacement routes, and
  (b) proving the benchmark's terminally relevant scope is actually covered.

It never grants acceptance credit itself. A successful result is only a candidate
SCOPE_COMPLETE_STRONGER_PROOF until this exact runtime + input are independently
verified and content-addressed.

Core rule:
    complete target scope
    + complete cover of that scope
    + Brain-owned resource-admissible policy for every cover cell
    + independent positive adequacy certificate for every cell
    + truthful precommitment selector when multiple policies are needed
    => candidate stronger proof.

Unknown scope, unknown adequacy, or self-certified semantics fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_SCOPE_COVER_V1"

_SCOPE_BASES = {
    "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
    "EXHAUSTIVE_FINITE_SUPERSET",
    "UNIVERSAL_FORMAL_SCOPE_PROOF",
}


def _receipt(obj: Any, label: str, errors: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(obj, Mapping):
        errors.append(f"{label}_NOT_OBJECT")
        return None
    if obj.get("verified") is not True:
        errors.append(f"{label}_NOT_VERIFIED")
    if obj.get("independent") is not True:
        errors.append(f"{label}_NOT_INDEPENDENT")
    path = obj.get("source_path")
    sha = obj.get("source_sha")
    if not isinstance(path, str) or not path.strip():
        errors.append(f"{label}_SOURCE_PATH_MISSING")
    if not isinstance(sha, str) or len(sha.strip()) < 7:
        errors.append(f"{label}_SOURCE_SHA_MISSING")
    return obj


def _scope_complete(scope: Any, errors: list[str]) -> None:
    s = _receipt(scope, "SCOPE_COMPLETENESS", errors)
    if s is None:
        return
    basis = s.get("basis")
    if basis not in _SCOPE_BASES:
        errors.append("SCOPE_COMPLETENESS_BASIS_INVALID")
        return
    if basis == "EXACT_COMPLETE_TARGET_CASE_UNIVERSE":
        if s.get("complete_target_case_set") is not True:
            errors.append("EXACT_TARGET_CASE_UNIVERSE_NOT_COMPLETE")
    elif basis == "EXHAUSTIVE_FINITE_SUPERSET":
        if s.get("exhaustive") is not True:
            errors.append("FINITE_SUPERSET_NOT_EXHAUSTIVE")
        if s.get("target_subset_proved") is not True:
            errors.append("TARGET_SUBSET_NOT_PROVED")
    elif basis == "UNIVERSAL_FORMAL_SCOPE_PROOF":
        if s.get("all_admissible_target_inputs_proved") is not True:
            errors.append("UNIVERSAL_TARGET_SCOPE_NOT_PROVED")
        if s.get("formal_completeness") is not True:
            errors.append("UNIVERSAL_SCOPE_FORMAL_COMPLETENESS_MISSING")


def evaluate(payload: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["INPUT_NOT_OBJECT"],
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    benchmark_id = payload.get("benchmark_id")
    predicate_id = payload.get("predicate_id")
    if not isinstance(benchmark_id, str) or not benchmark_id.strip():
        errors.append("BENCHMARK_ID_INVALID")
    if not isinstance(predicate_id, str) or not predicate_id.strip():
        errors.append("PREDICATE_ID_INVALID")

    _scope_complete(payload.get("scope_completeness"), errors)

    cover = _receipt(payload.get("cover_completeness"), "COVER_COMPLETENESS", errors)
    if isinstance(cover, Mapping) and cover.get("covers_entire_scope") is not True:
        errors.append("COVER_DOES_NOT_PROVE_ENTIRE_SCOPE")

    cells = payload.get("cells")
    if not isinstance(cells, list) or not cells:
        errors.append("CELLS_INVALID_OR_EMPTY")
        cells = []

    seen_cells: set[str] = set()
    policy_ids: set[str] = set()
    cell_results: list[dict[str, Any]] = []

    for i, cell in enumerate(cells):
        local: list[str] = []
        if not isinstance(cell, Mapping):
            errors.append(f"CELL_NOT_OBJECT:{i}")
            continue

        cid = cell.get("cell_id")
        if not isinstance(cid, str) or not cid.strip() or cid in seen_cells:
            local.append("CELL_ID_INVALID_OR_DUPLICATE")
            cid = f"INVALID::{i}"
        seen_cells.add(cid)

        relation = cell.get("scope_relation")
        if relation not in {"EXACT", "PROVEN_STRONGER"}:
            local.append("CELL_SCOPE_RELATION_INSUFFICIENT")

        pid = cell.get("policy_id")
        if not isinstance(pid, str) or not pid.strip():
            local.append("POLICY_ID_INVALID")
        else:
            policy_ids.add(pid)

        if cell.get("brain_owned_policy") is not True:
            local.append("POLICY_NOT_BRAIN_OWNED")
        if cell.get("deployable") is not True:
            local.append("POLICY_NOT_DEPLOYABLE")
        if cell.get("resource_admissible") is not True:
            local.append("POLICY_NOT_RESOURCE_ADMISSIBLE")
        if cell.get("external_target_capability_provider") is not False:
            local.append("EXTERNAL_TARGET_CAPABILITY_PROVIDER_NOT_EXCLUDED")

        cert_errors: list[str] = []
        cert = _receipt(
            cell.get("adequacy_certificate"),
            f"ADEQUACY_CERTIFICATE:{cid}",
            cert_errors,
        )
        if isinstance(cert, Mapping) and cert.get("adequate_for_entire_cell") is not True:
            cert_errors.append("ADEQUACY_CERTIFICATE_NOT_WHOLE_CELL")
        local.extend(cert_errors)

        for e in local:
            errors.append(f"CELL:{cid}:{e}")
        cell_results.append({
            "cell_id": cid,
            "policy_id": pid,
            "pass": not local,
        })

    selector_required = len(policy_ids) > 1
    selector = payload.get("selector")
    if selector_required:
        sel = _receipt(selector, "SELECTOR", errors)
        if isinstance(sel, Mapping):
            if sel.get("precommitment") is not True:
                errors.append("SELECTOR_NOT_PRECOMMITMENT")
            if sel.get("truthful_selected_discriminator_semantics") is not True:
                errors.append("SELECTOR_DISCRIMINATOR_SEMANTICS_NOT_PROVED")
            if sel.get("selects_only_certified_cells") is not True:
                errors.append("SELECTOR_CAN_ESCAPE_CERTIFIED_CELLS")
    elif selector is not None:
        # Optional selectors must still be sound if supplied.
        sel = _receipt(selector, "SELECTOR", errors)
        if isinstance(sel, Mapping) and sel.get("selects_only_certified_cells") is not True:
            errors.append("SELECTOR_CAN_ESCAPE_CERTIFIED_CELLS")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "CANDIDATE_SCOPE_COMPLETE_STRONGER_PROOF_READY__INDEPENDENT_RUNTIME_AND_INPUT_VERIFICATION_REQUIRED"
            if passed else "FAIL_CLOSED"
        ),
        "benchmark_id": benchmark_id,
        "predicate_id": predicate_id,
        "scope_basis": (
            payload.get("scope_completeness", {}).get("basis")
            if isinstance(payload.get("scope_completeness"), Mapping)
            else None
        ),
        "cell_count": len(cell_results),
        "policy_count": len(policy_ids),
        "selector_required": selector_required,
        "cells": cell_results,
        "errors": sorted(set(errors)),
        "candidate_evidence_template": (
            {
                "predicate_id": predicate_id,
                "state": "PROVED",
                "proof_kind": "SCOPE_COMPLETE_STRONGER_PROOF",
                "scope_complete": True,
                "independent_or_objective": True,
                "source_path": "REPLACE_WITH_INDEPENDENT_VERIFICATION_RECEIPT_PATH",
                "source_sha": "REPLACE_WITH_INDEPENDENT_VERIFICATION_RECEIPT_SHA",
            }
            if passed else None
        ),
        "promotion_authority": False,
        "terminal_credit_delta": 0,
        "rule": (
            "ROUTE_REDUNDANCY_IS_NOT_ACCEPTANCE_CLOSURE__"
            "STRONGER_PROOF_REQUIRES_INDEPENDENT_COMPLETE_TARGET_SCOPE__"
            "INDEPENDENT_COMPLETE_COVER__POSITIVE_WHOLE_CELL_ADEQUACY__"
            "AND_TRUTHFUL_PRECOMMITMENT_SELECTION_WHEN_MULTIPLE_POLICIES_ARE_USED"
        ),
    }

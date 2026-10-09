"""Scope-identity binding gate for proof-carrying positive-adequacy covers.

V1 validates receipt quality and positive adequacy structure but does not bind the
cover or its cells to the exact scope named by the scope-completeness receipt.
V2 adds that missing quantifier binding while preserving V1 semantics.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.proof_carrying_scope_cover_v1 import evaluate as evaluate_v1

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_SCOPE_COVER_V2"


def _receipt_identity(obj: Any, label: str, errors: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(obj, Mapping):
        errors.append(label + "_NOT_OBJECT")
        return None
    return obj


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evaluate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["INPUT_NOT_OBJECT"],
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    errors: list[str] = []
    scope = _receipt_identity(payload.get("scope_completeness"), "SCOPE_COMPLETENESS", errors)
    cover = _receipt_identity(payload.get("cover_completeness"), "COVER_COMPLETENESS", errors)

    scope_id = scope.get("scope_id") if isinstance(scope, Mapping) else None
    cover_scope_id = cover.get("scope_id") if isinstance(cover, Mapping) else None

    if not _nonempty(scope_id):
        errors.append("SCOPE_ID_MISSING")
    if not _nonempty(cover_scope_id):
        errors.append("COVER_SCOPE_ID_MISSING")
    if _nonempty(scope_id) and _nonempty(cover_scope_id) and cover_scope_id != scope_id:
        errors.append("COVER_SCOPE_ID_MISMATCH")

    cells = payload.get("cells")
    if isinstance(cells, list) and _nonempty(scope_id):
        for index, cell in enumerate(cells):
            if not isinstance(cell, Mapping):
                continue
            cid = cell.get("cell_id")
            label = cid if _nonempty(cid) else str(index)
            target_scope_id = cell.get("target_scope_id")
            cell_scope_id = cell.get("cell_scope_id")
            relation = cell.get("scope_relation")

            if target_scope_id != scope_id:
                errors.append(f"CELL:{label}:TARGET_SCOPE_ID_MISMATCH")
            if not _nonempty(cell_scope_id):
                errors.append(f"CELL:{label}:CELL_SCOPE_ID_MISSING")
                continue

            if relation == "EXACT":
                if cell_scope_id != scope_id:
                    errors.append(f"CELL:{label}:EXACT_SCOPE_ID_MISMATCH")
            elif relation == "PROVEN_STRONGER":
                receipt = cell.get("scope_relation_receipt")
                if not isinstance(receipt, Mapping):
                    errors.append(f"CELL:{label}:STRONGER_SCOPE_RELATION_RECEIPT_MISSING")
                    continue
                if receipt.get("verified") is not True:
                    errors.append(f"CELL:{label}:STRONGER_SCOPE_RELATION_NOT_VERIFIED")
                if receipt.get("independent") is not True:
                    errors.append(f"CELL:{label}:STRONGER_SCOPE_RELATION_NOT_INDEPENDENT")
                if receipt.get("target_scope_id") != scope_id:
                    errors.append(f"CELL:{label}:STRONGER_RELATION_TARGET_SCOPE_MISMATCH")
                if receipt.get("stronger_scope_id") != cell_scope_id:
                    errors.append(f"CELL:{label}:STRONGER_RELATION_SCOPE_ID_MISMATCH")
                if receipt.get("target_subset_of_stronger_scope") is not True:
                    errors.append(f"CELL:{label}:TARGET_SUBSET_OF_STRONGER_SCOPE_UNPROVED")
                source_path = receipt.get("source_path")
                source_sha = receipt.get("source_sha")
                if not _nonempty(source_path):
                    errors.append(f"CELL:{label}:STRONGER_RELATION_SOURCE_PATH_MISSING")
                if not _nonempty(source_sha):
                    errors.append(f"CELL:{label}:STRONGER_RELATION_SOURCE_SHA_MISSING")

    inherited = evaluate_v1(payload)
    if inherited.get("pass") is not True:
        errors.extend("V1:" + str(x) for x in (inherited.get("errors") or []))

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "CANDIDATE_SCOPE_COMPLETE_STRONGER_PROOF_READY__SCOPE_IDENTITIES_BOUND"
            if passed
            else "FAIL_CLOSED"
        ),
        "benchmark_id": payload.get("benchmark_id"),
        "predicate_id": payload.get("predicate_id"),
        "scope_id": scope_id,
        "cover_scope_id": cover_scope_id,
        "cell_count": inherited.get("cell_count"),
        "policy_count": inherited.get("policy_count"),
        "selector_required": inherited.get("selector_required"),
        "cells": inherited.get("cells"),
        "errors": sorted(set(errors)),
        "inherited_v1_pass": inherited.get("pass") is True,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
        "rule": (
            "A_SCOPE_COVER_MAY_NOT_BORROW_COMPLETENESS_FROM_AN_UNRELATED_SCOPE;"
            "COVER_SCOPE_ID_MUST_EQUAL_THE_SCOPE_COMPLETENESS_SCOPE_ID;"
            "EVERY_CELL_MUST_BIND_TO_THAT_TARGET_SCOPE;"
            "PROVEN_STRONGER_CELLS_REQUIRE_AN_INDEPENDENT_TARGET_SUBSET_RECEIPT"
        ),
    }

"""Localize the first sound residual blocking professional-context P2 membership.

This is a diagnostic/scheduling component, not an admission gate. It composes:
1. declared source/dimension/convention structural preflight when supplied;
2. strict explicit-P2 source membership;
3. deterministic structural diff when strict membership fails.

Crucially, extra fields are never declared irrelevant. They are surfaced as
POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS until a separate sound projection or
equivalence certificate proves otherwise.

The purpose is to replace vague "professional intelligence missing" diagnoses
with the smallest explicit membership obstruction.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from canonical.runtime.professional_source_authority_coverage_gate_v1 import verify as verify_source_preflight
from canonical.runtime.p2_explicit_contract_membership_v1 import (
    compile_membership,
    P2,
    TASK_KEYS,
    EVIDENCE_KEYS,
    EDIT_KEYS,
)

SCHEMA = "BRAIN_P2_MEMBERSHIP_RESIDUAL_LOCALIZER_V1"


def _load_raw(raw_source: str | bytes) -> tuple[Mapping[str, Any] | None, list[str]]:
    try:
        raw = raw_source.encode("utf-8") if isinstance(raw_source, str) else raw_source
        if not isinstance(raw, bytes):
            return None, ["RAW_SOURCE_MUST_BE_TEXT_OR_BYTES"]
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, Mapping):
            return None, ["RAW_SOURCE_JSON_NOT_OBJECT"]
        return value, []
    except Exception as exc:
        return None, ["RAW_SOURCE_NOT_STRUCTURED_JSON:" + type(exc).__name__]


def _diff(doc: Mapping[str, Any]) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    top = set(doc)
    expected_top = {"contract", "task"}
    for key in sorted(expected_top - top):
        residuals.append({
            "class": "MISSING_REQUIRED_CONTRACT_STRUCTURE",
            "path": key,
            "detail": "required top-level P2 source field missing",
        })
    for key in sorted(top - expected_top):
        residuals.append({
            "class": "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS",
            "path": key,
            "detail": "extra top-level field cannot be silently projected away",
        })

    if doc.get("contract") not in (None, P2):
        residuals.append({
            "class": "CONTRACT_IDENTITY_MISMATCH",
            "path": "contract",
            "detail": "source does not declare the exact P2 contract",
        })

    task = doc.get("task")
    if not isinstance(task, Mapping):
        residuals.append({
            "class": "MISSING_REQUIRED_CONTRACT_STRUCTURE",
            "path": "task",
            "detail": "task must be an object",
        })
        return {"residuals": residuals}

    task_keys = set(task)
    for key in sorted(TASK_KEYS - task_keys):
        residuals.append({
            "class": "MISSING_P2_SEMANTIC_FIELD",
            "path": "task." + key,
            "detail": "required P2 semantic field absent",
        })
    for key in sorted(task_keys - TASK_KEYS):
        residuals.append({
            "class": "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS",
            "path": "task." + key,
            "detail": "extra task dimension requires a separate sound irrelevance/equivalence proof before projection",
        })

    evidence = task.get("evidence")
    if isinstance(evidence, list):
        for i, row in enumerate(evidence):
            if not isinstance(row, Mapping):
                residuals.append({
                    "class": "MALFORMED_P2_FIELD",
                    "path": f"task.evidence[{i}]",
                    "detail": "evidence row is not an object",
                })
                continue
            keys = set(row)
            for key in sorted(EVIDENCE_KEYS - keys):
                residuals.append({
                    "class": "MISSING_P2_SEMANTIC_FIELD",
                    "path": f"task.evidence[{i}].{key}",
                    "detail": "required evidence identity field absent",
                })
            for key in sorted(keys - EVIDENCE_KEYS):
                residuals.append({
                    "class": "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS",
                    "path": f"task.evidence[{i}].{key}",
                    "detail": "extra evidence semantics cannot be discarded without a projection proof",
                })

    edits = task.get("edit_candidates")
    if isinstance(edits, list):
        for i, row in enumerate(edits):
            if not isinstance(row, Mapping):
                residuals.append({
                    "class": "MALFORMED_P2_FIELD",
                    "path": f"task.edit_candidates[{i}]",
                    "detail": "edit row is not an object",
                })
                continue
            keys = set(row)
            for key in sorted(EDIT_KEYS - keys):
                residuals.append({
                    "class": "MISSING_P2_SEMANTIC_FIELD",
                    "path": f"task.edit_candidates[{i}].{key}",
                    "detail": "required edit semantic field absent",
                })
            for key in sorted(keys - EDIT_KEYS):
                residuals.append({
                    "class": "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS",
                    "path": f"task.edit_candidates[{i}].{key}",
                    "detail": "extra edit semantics cannot be discarded without a projection proof",
                })

    return {"residuals": residuals}


def localize(
    raw_source: str | bytes,
    *,
    source_id: str,
    structural_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if structural_manifest is not None:
        preflight = verify_source_preflight(structural_manifest)
        if preflight.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "BLOCKED",
                "membership_proved": False,
                "first_residual_class": "DECLARED_STRUCTURAL_PREFLIGHT_FAILURE",
                "structural_preflight": preflight,
                "next_action": "REPAIR_DECLARED_SOURCE_DIMENSION_OR_CONVENTION_OMISSION_BEFORE_SEMANTIC_MEMBERSHIP",
                "terminal_authority": False,
            }
    else:
        preflight = None

    membership = compile_membership(raw_source, source_id=source_id)
    if membership.get("pass") is True:
        return {
            "schema": SCHEMA,
            "status": "PASS__EXPLICIT_P2_MEMBERSHIP_PROVED",
            "membership_proved": True,
            "membership": membership,
            "structural_preflight": preflight,
            "first_residual_class": None,
            "residuals": [],
            "terminal_authority": False,
        }

    doc, load_errors = _load_raw(raw_source)
    if doc is None:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "membership_proved": False,
            "first_residual_class": "RAW_TO_TYPED_P2_SEMANTIC_COMPILATION",
            "errors": load_errors,
            "strict_membership_failure": membership.get("errors", []),
            "next_action": "USE_ONE_SIDED_SOURCE_GROUNDED_EXTRACTORS_TO_PROVE_ONLY_POLICY_RELEVANT_P2_FIELDS;DO_NOT_GUESS_UNMAPPED_SEMANTICS",
            "terminal_authority": False,
        }

    rows = _diff(doc)["residuals"]
    if not rows:
        # Strict compiler can still reject value-level invalidity after structural shape matches.
        rows = [{
            "class": "MALFORMED_OR_UNPROVED_P2_FIELD_VALUE",
            "path": "task",
            "detail": ";".join(membership.get("errors") or ["STRICT_P2_MEMBERSHIP_FAILED"]),
        }]

    priority = {
        "MISSING_REQUIRED_CONTRACT_STRUCTURE": 0,
        "CONTRACT_IDENTITY_MISMATCH": 1,
        "MISSING_P2_SEMANTIC_FIELD": 2,
        "MALFORMED_P2_FIELD": 3,
        "MALFORMED_OR_UNPROVED_P2_FIELD_VALUE": 4,
        "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS": 5,
    }
    rows = sorted(rows, key=lambda r: (priority.get(r["class"], 99), r["path"]))
    first = rows[0]
    next_action_by_class = {
        "MISSING_REQUIRED_CONTRACT_STRUCTURE": "BIND_REQUIRED_P2_CONTRACT_STRUCTURE",
        "CONTRACT_IDENTITY_MISMATCH": "ESTABLISH_SCOPE_EQUIVALENCE_OR_KEEP_CONTEXT_OUTSIDE_P2",
        "MISSING_P2_SEMANTIC_FIELD": "DERIVE_THE_NAMED_FIELD_WITH_A_ONE_SIDED_SOURCE_GROUNDED_PROOF",
        "MALFORMED_P2_FIELD": "REPAIR_OR_REJECT_THE_MALFORMED_DECLARED_FIELD",
        "MALFORMED_OR_UNPROVED_P2_FIELD_VALUE": "PROVE_THE_DECLARED_FIELD_VALUE_OR_KEEP_CONTEXT_UNRESOLVED",
        "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS": "PROVE_EXTRA_DIMENSION_IRRELEVANT_TO_POLICY_ADEQUACY_OR_EXTEND_THE_CONTRACT",
    }
    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED__LOCALIZED_MEMBERSHIP_RESIDUAL",
        "membership_proved": False,
        "strict_membership_failure": membership.get("errors", []),
        "structural_preflight": preflight,
        "first_residual_class": first["class"],
        "first_residual": first,
        "residuals": rows,
        "next_action": next_action_by_class.get(first["class"], "KEEP_CONTEXT_UNRESOLVED"),
        "semantic_omission_is_unsafe_policy_guess": False,
        "semantic_omission_leaves_context_unresolved": True,
        "terminal_authority": False,
    }

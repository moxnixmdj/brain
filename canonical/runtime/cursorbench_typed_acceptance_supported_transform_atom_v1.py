"""Structural proof for the typed-acceptance supported-transform atom.

This module proves exactly one conditioned-policy membership atom from exact
normalized acceptance-model bytes. It does not infer task semantics, failure-mode
completeness, provenance truth, hidden-verifier isolation, or benchmark membership.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.independent_acceptance_model import OBLIGATIONS

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_SUPPORTED_TRANSFORM_ATOM_PROOF_V1"
ATOM_ID = "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1"
ATOM_SEMANTICS = (
    "EVERY_ACTIVE_TRANSFORM_KIND_IS_ONE_OF_THE_EXACT_BOUND_RUNTIME_SUPPORTED_KINDS"
)


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def model_sha256(model: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(model)).hexdigest()


def verify(model: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    observed: list[str] = []
    unknown: list[str] = []

    if not isinstance(model, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODEL_NOT_OBJECT",
            "errors": ["MODEL_NOT_OBJECT"],
            "atom_id": ATOM_ID,
            "atom_truth_authorized": False,
            "proved_constraint": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    requirements = model.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        errors.append("REQUIREMENTS_INVALID_OR_EMPTY")
        requirements = []

    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, Mapping):
            errors.append(f"REQUIREMENT_NOT_OBJECT:{index}")
            continue
        kinds = requirement.get("transform_kinds", [])
        if not isinstance(kinds, list):
            errors.append(f"TRANSFORM_KINDS_NOT_LIST:{index}")
            continue
        for raw in kinds:
            if not isinstance(raw, str) or not raw.strip():
                errors.append(f"TRANSFORM_KIND_INVALID:{index}")
                continue
            kind = raw.strip()
            observed.append(kind)
            if kind not in OBLIGATIONS:
                unknown.append(kind)

    unknown = sorted(set(unknown))
    if unknown:
        errors.append("UNSUPPORTED_TRANSFORM_KIND:" + ",".join(unknown))

    passed = not errors
    digest = model_sha256(model)
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__SUPPORTED_TRANSFORM_ATOM_PROVED_FROM_EXACT_MODEL_STRUCTURE"
            if passed
            else "FAIL_CLOSED__SUPPORTED_TRANSFORM_ATOM_UNPROVED"
        ),
        "atom_id": ATOM_ID,
        "atom_semantics": ATOM_SEMANTICS,
        "atom_truth_authorized": passed,
        "proof_basis": "EXACT_NORMALIZED_MODEL_STRUCTURAL_PROOF" if passed else None,
        "model_sha256": digest,
        "observed_transform_kinds": sorted(set(observed)),
        "supported_transform_kinds": sorted(OBLIGATIONS),
        "unknown_transform_kinds": unknown,
        "errors": errors,
        "proved_constraint": {"op": "ATOM", "id": ATOM_ID} if passed else None,
        "other_condition_atoms_proved": [],
        "membership_self_certified": False,
        "whole_policy_condition_proved": False,
        "whole_specification_behavior_adequate": False,
        "whole_cursorbench_adequate": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

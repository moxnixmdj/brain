"""Proof-carrying typed acceptance controller.

Composes existing independently verified proof mechanisms with the Brain-owned
independent acceptance model. Missing evidence blocks. Invalid supplied proof
fails closed. This module grants no benchmark or terminal credit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    ATOM_ID as SUPPORTED_TRANSFORM_ATOM_ID,
    verify as verify_supported_transform,
)
from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    PROVED_ATOM_IDS as SOURCE_COVERAGE_ATOM_IDS,
    verify as verify_source_coverage,
)
from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    ATOM_ID as DEPENDENCY_PROVENANCE_ATOM_ID,
    verify as verify_dependency_provenance,
)
from canonical.runtime.cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    ATOM_ID as INFORMATION_BOUNDARY_ATOM_ID,
    verify as verify_information_boundary,
)
from canonical.runtime.independent_acceptance_model import assess

SCHEMA = "PROJECT_BRAIN_CODING_PROOF_CARRYING_TYPED_ACCEPTANCE_CONTROLLER_V1"

_REQUIRED_BINDINGS = (
    ("source_coverage", "typed_acceptance_source_coverage_binding"),
    ("dependency_provenance", "typed_acceptance_dependency_provenance_binding"),
    ("information_boundary", "typed_acceptance_information_boundary_binding"),
)


def _base(status: str, *, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "preflight_authorized": False,
        "proved_atom_ids": [],
        "evidence_gaps": [],
        "proof_failures": [],
        "assessment": None,
        "policy_adequacy_authority": False,
        "benchmark_acceptance_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def _is_open(proof: Mapping[str, Any]) -> bool:
    status = str(proof.get("status") or "")
    return status.startswith("OPEN__") or proof.get("evidence_missing") is True


def evaluate(
    payload: Mapping[str, Any] | None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        out = _base("FAIL_CLOSED__PAYLOAD_MAPPING_REQUIRED")
        out["proof_failures"] = ["PAYLOAD_MAPPING_REQUIRED"]
        return out

    allowed = {
        "typed_acceptance_model",
        "typed_acceptance_source_coverage_binding",
        "typed_acceptance_dependency_provenance_binding",
        "typed_acceptance_information_boundary_binding",
    }
    extra = sorted(set(payload) - allowed)
    if extra:
        out = _base("FAIL_CLOSED__UNKNOWN_PAYLOAD_FIELDS")
        out["proof_failures"] = ["UNKNOWN_PAYLOAD_FIELDS:" + ",".join(extra)]
        return out

    model = payload.get("typed_acceptance_model")
    if not isinstance(model, Mapping):
        out = _base("FAIL_CLOSED__TYPED_ACCEPTANCE_MODEL_REQUIRED")
        out["proof_failures"] = ["TYPED_ACCEPTANCE_MODEL_REQUIRED"]
        return out

    root = Path(repo_root) if repo_root is not None else None
    structural = verify_supported_transform(model)
    proofs: dict[str, dict[str, Any]] = {"supported_transform": structural}
    if structural.get("pass") is not True or structural.get("atom_truth_authorized") is not True:
        out = _base("FAIL_CLOSED__SUPPORTED_TRANSFORM_PROOF_FAILED")
        out["proofs"] = proofs
        out["proof_failures"] = list(structural.get("errors") or [structural.get("status")])
        return out

    source = verify_source_coverage(
        model,
        payload.get("typed_acceptance_source_coverage_binding"),
        repo_root=root,
    )
    provenance = verify_dependency_provenance(
        model,
        payload.get("typed_acceptance_dependency_provenance_binding"),
        repo_root=root,
    )
    boundary = verify_information_boundary(
        model,
        payload.get("typed_acceptance_information_boundary_binding"),
        repo_root=root,
    )
    proofs.update({
        "source_coverage": source,
        "dependency_provenance": provenance,
        "information_boundary": boundary,
    })

    gaps: list[str] = []
    failures: list[str] = []
    for label, field in _REQUIRED_BINDINGS:
        proof = proofs[label]
        if proof.get("pass") is True and proof.get("atom_truth_authorized") is True:
            continue
        if _is_open(proof):
            gaps.append(field)
            continue
        errors = proof.get("errors")
        if isinstance(errors, list) and errors:
            failures.extend(f"{label}:{x}" for x in errors)
        else:
            failures.append(f"{label}:{proof.get('status')}")

    if failures:
        out = _base("FAIL_CLOSED__SUPPLIED_PROOF_INVALID_OR_CONTRADICTORY")
        out["proofs"] = proofs
        out["proof_failures"] = sorted(set(failures))
        out["evidence_gaps"] = sorted(set(gaps))
        return out

    if gaps:
        out = _base("BLOCKED__PROOF_EVIDENCE_INSUFFICIENT")
        out["proofs"] = proofs
        out["evidence_gaps"] = sorted(set(gaps))
        out["proved_atom_ids"] = [SUPPORTED_TRANSFORM_ATOM_ID]
        return out


    proved = {
        SUPPORTED_TRANSFORM_ATOM_ID,
        DEPENDENCY_PROVENANCE_ATOM_ID,
        INFORMATION_BOUNDARY_ATOM_ID,
        *SOURCE_COVERAGE_ATOM_IDS,
    }

    try:
        assessment = assess(dict(model))
    except Exception as exc:
        out = _base("FAIL_CLOSED__INDEPENDENT_ACCEPTANCE_ASSESSMENT_INVALID")
        out["proofs"] = proofs
        out["proved_atom_ids"] = sorted(proved)
        out["proof_failures"] = [type(exc).__name__ + ":" + str(exc)]
        return out

    if assessment.get("terminal_submission_authorized_by_this_gate") is not True:
        out = _base("BLOCKED__INDEPENDENT_ACCEPTANCE_INCOMPLETE")
        out["proofs"] = proofs
        out["proved_atom_ids"] = sorted(proved)
        out["assessment"] = assessment
        out["failed_requirements"] = list(assessment.get("failed_requirements") or [])
        out["counterexample_templates"] = [
            template
            for row in (assessment.get("requirements") or [])
            for template in (row.get("counterexample_templates") or [])
        ]
        return out

    out = _base("PASS__PROOF_CARRYING_TYPED_ACCEPTANCE_PREFLIGHT", passed=True)
    out["proofs"] = proofs
    out["proved_atom_ids"] = sorted(proved)
    out["assessment"] = assessment
    out["preflight_authorized"] = True
    out["boundary"] = (
        "THIS_IS_ONLY_A_PROOF_CARRYING_PRETERMINAL_GATE_DECISION;"
        "CENTRAL_TERMINAL_AUTHORITY_AND_BENCHMARK_ACCEPTANCE_REMAIN_SEPARATE"
    )
    return out

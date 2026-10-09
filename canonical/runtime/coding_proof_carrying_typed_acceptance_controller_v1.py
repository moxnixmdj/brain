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

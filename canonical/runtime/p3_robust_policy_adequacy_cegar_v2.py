"""P3 robust policy-adequacy CEGAR successor.

V2 changes only conditioned-adequacy admission. The finite CEGAR solver,
authenticated adequacy verifier, objective, and output semantics remain V1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as v1
from canonical.runtime.p3_conditioned_policy_adequacy_registry_v2 import (
    augment_problem as augment_with_conditioned_adequacy,
)

ROOT = Path(__file__).resolve().parents[2]


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    registry = augment_with_conditioned_adequacy(problem, repo_root=ROOT)
    if registry.get("pass") is not True:
        return v1._fail(
            "CONDITIONED_POLICY_ADEQUACY_REGISTRY_FAIL_CLOSED",
            conditioned_policy_adequacy_registry=registry,
        )

    result = v1._solve_augmented(registry["problem"])
    out = dict(result)
    out["conditioned_policy_adequacy_registry"] = {
        "status": registry.get("status"),
        "registered_policy_count": registry.get("registered_policy_count"),
        "basis_eligible_policy_count": registry.get("basis_eligible_policy_count"),
        "injected_policy_ids": list(registry.get("injected_policy_ids") or []),
        "reused_policy_ids": list(registry.get("reused_policy_ids") or []),
        "skipped_registered_policies": list(registry.get("skipped_registered_policies") or []),
        "structural_atom_proofs": list(registry.get("structural_atom_proofs") or []),
        "structurally_proved_atom_ids": list(registry.get("structurally_proved_atom_ids") or []),
        "information_boundary_atom_proofs": list(
            registry.get("information_boundary_atom_proofs") or []
        ),
        "information_boundary_proved_atom_ids": list(
            registry.get("information_boundary_proved_atom_ids") or []
        ),
        "dependency_provenance_atom_proofs": list(
            registry.get("dependency_provenance_atom_proofs") or []
        ),
        "dependency_provenance_proved_atom_ids": list(
            registry.get("dependency_provenance_proved_atom_ids") or []
        ),
        "typed_semantics_atom_proofs": list(
            registry.get("typed_semantics_atom_proofs") or []
        ),
        "mode_completeness_atom_proofs": list(
            registry.get("mode_completeness_atom_proofs") or []
        ),
        "proved_condition_atom_ids": list(registry.get("proved_condition_atom_ids") or []),
        "membership_self_certified": False,
        "registry_authority": False,
    }
    out["conditioned_registry_successor"] = "V2"
    return out


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    global ROOT
    old_root = ROOT
    old_v1_root = v1.ROOT
    if root is not None:
        ROOT = Path(root)
        v1.ROOT = Path(root)
    try:
        return solve(args or {})
    finally:
        ROOT = old_root
        v1.ROOT = old_v1_root

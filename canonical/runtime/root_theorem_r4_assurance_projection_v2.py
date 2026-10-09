"""R4 assurance projection V2 with an exact current root-status registry."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.root_certificate_registry_v1 import validate_repo as validate_registry
from canonical.runtime.root_theorem_r4_assurance_projection_v1 import project_repo as project_v1


def project_repo(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    prior = project_v1(root)
    registry = validate_registry(root)

    errors = list(prior.get("errors") or [])
    if registry.get("pass") is not True:
        errors.append("ROOT_CERTIFICATE_REGISTRY_INVALID")

    representation = bool(
        (prior.get("gates") or {}).get("representation_closure", {}).get("closed")
    )
    proof_closed = (
        registry.get("pass") is True
        and registry.get("proof_closure_ready") is True
        and registry.get("root_status_vector") == ["PROVED", "PROVED", "PROVED"]
    )
    execution_closed = False
    adversarial_closed = False

    residuals: list[str] = []
    if not representation:
        residuals.append("R4_REPRESENTATION_CLOSURE_CURRENT_DECLARED_REGISTRY")
    if not proof_closed:
        residuals.append("R4_R1_R2_R3_EXACT_ROOT_PROOF_CLOSURE")
    if not execution_closed:
        residuals.append("R4_ROOT_PROOF_TO_REALIZATION_EXECUTION_CLOSURE")
    if not adversarial_closed:
        residuals.append("R4_INDEPENDENT_DOMAIN_ADVERSARIAL_CLOSURE")

    return {
        "schema": "PROJECT_BRAIN_R4_ASSURANCE_PROJECTION_RUNTIME_V2",
        "status": (
            "OPEN__R4_ROOT_REGISTRY_BOUND__EXACT_ROOT_PROOFS_AND_TRUST_TAIL_OPEN"
            if not errors
            else "FAIL_CLOSED__R4_V2_PROJECTION_DRIFT"
        ),
        "pass": False,
        "r4_closed": False,
        "gates": {
            "representation_closure": {"closed": representation},
            "proof_closure": {
                "closed": proof_closed,
                "registry_bound": registry.get("pass") is True,
                "root_status_vector": registry.get("root_status_vector"),
                "reason": (
                    "ALL_EXACT_ROOTS_PROVED"
                    if proof_closed
                    else "R1_R2_R3_EXACT_ROOT_PROPOSITIONS_REMAIN_UNKNOWN"
                ),
            },
            "execution_closure": {
                "closed": execution_closed,
                "reason": "ROOT_PROOF_TO_REALIZATION_BINDING_NOT_BOUND",
            },
            "adversarial_closure": {
                "closed": adversarial_closed,
                "reason": "INDEPENDENT_DOMAIN_LEVEL_ADVERSARIAL_DEFEATER_BINDING_NOT_CLOSED",
            },
        },
        "root_registry": registry,
        "open_residuals": residuals,
        "errors": errors,
        "new_primitive_required": False if representation else None,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(project_repo(Path(__file__).resolve().parents[2]), indent=2, sort_keys=True))

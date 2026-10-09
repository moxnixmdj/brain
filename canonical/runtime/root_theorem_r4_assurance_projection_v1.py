"""Current-state R4 projection onto the existing UVCK V2 assurance gates.

Read-only, zero-credit, and non-authoritative. It never accepts caller booleans
for gate closure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime.root_theorem_live_binding_v1 import validate_repo as validate_live_binding


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_repo(root: Path) -> dict[str, Any]:
    live = validate_live_binding(root)
    if live.get("pass") is not True:
        return {
            "status": "FAIL_CLOSED__R4_LIVE_BINDING_INVALID",
            "pass": False,
            "live_binding": live,
            "r4_closed": False,
            "terminal_credit_delta": 0,
        }

    pointer = _load(root / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json")
    verify = _load(root / "canonical/verification/UVCK_V2_ASSURANCE_CLOSURE_VERIFY_20261009_V1.json")
    theorem = _load(root / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json")

    errors: list[str] = []
    if pointer.get("terminal_authority") is not False:
        errors.append("ASSURANCE_COMPILER_TERMINAL_AUTHORITY_DRIFT")
    if pointer.get("terminal_credit_delta") != 0:
        errors.append("ASSURANCE_COMPILER_CREDIT_DRIFT")
    if verify.get("terminal_authority") is not False:
        errors.append("ASSURANCE_VERIFIER_TERMINAL_AUTHORITY_DRIFT")
    if (verify.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("ASSURANCE_VERIFIER_CREDIT_DRIFT")

    domain = pointer.get("domain_challenge_registry") or {}
    independent = pointer.get("independent_structural_check") or {}
    representation_closed = (
        domain.get("result") == "16_OF_16_EXISTING_KERNEL_RESIDUALS"
        and independent.get("result") == "11_OF_11_MATCH"
    )

    # No caller-supplied certificate booleans are allowed. The current theorem
    # explicitly does not claim R1/R2/R3 closed, and no canonical root
    # certificate registry is bound in the live-binding manifest yet.
    nonclaims = set(theorem.get("nonclaims") or [])
    current_roots_not_proved = all(
        item in nonclaims
        for item in (
            "CURRENT_R1_NOT_PROVED_BY_THIS_ARTIFACT",
            "CURRENT_R2_NOT_PROVED_BY_THIS_ARTIFACT",
            "CURRENT_R3_NOT_PROVED_BY_THIS_ARTIFACT",
        )
    )
    proof_closed = False

    activation = pointer.get("activation") or {}
    required = set(activation.get("required_before_promotion") or [])
    execution_closed = False
    adversarial_closed = False

    residuals: list[str] = []
    if not representation_closed:
        residuals.append("R4_REPRESENTATION_CLOSURE_CURRENT_DECLARED_REGISTRY")
    if not proof_closed:
        residuals.append("R4_ROOT_CERTIFICATE_COVERAGE_AND_PROOF_CLOSURE")
    if not execution_closed:
        residuals.append("R4_ROOT_PROOF_TO_REALIZATION_EXECUTION_CLOSURE")
    if not adversarial_closed:
        residuals.append("R4_INDEPENDENT_DOMAIN_ADVERSARIAL_CLOSURE")

    if "DOMAIN_SEMANTIC_AND_EXECUTION_EVIDENCE_BINDING" not in required:
        errors.append("UVCK_EXECUTION_PROMOTION_PREREQUISITE_DRIFT")
    if "FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION" not in required:
        errors.append("UVCK_FULL_SYSTEM_REPLAY_PREREQUISITE_DRIFT")

    gates = {
        "representation_closure": {
            "closed": representation_closed,
            "scope": "CURRENT_DECLARED_EXISTING_KERNEL_RESIDUAL_CHALLENGE_REGISTRY_ONLY",
        },
        "proof_closure": {
            "closed": proof_closed,
            "reason": "NO_CANONICAL_CURRENT_R1_R2_R3_ROOT_CERTIFICATE_REGISTRY_BOUND",
            "theorem_explicitly_nonclaims_current_roots": current_roots_not_proved,
        },
        "execution_closure": {
            "closed": execution_closed,
            "reason": "ROOT_PROOF_TO_REALIZATION_BINDING_NOT_BOUND",
        },
        "adversarial_closure": {
            "closed": adversarial_closed,
            "reason": "INDEPENDENT_DOMAIN_LEVEL_ADVERSARIAL_DEFEATER_BINDING_NOT_CLOSED",
        },
    }

    return {
        "status": "OPEN__R4_EXACT_RESIDUAL_LOCALIZED" if not errors else "FAIL_CLOSED__R4_PROJECTION_DRIFT",
        "pass": False,
        "r4_closed": False,
        "gates": gates,
        "open_residuals": residuals,
        "errors": errors,
        "assurance_live_default": bool(activation.get("live_default")),
        "assurance_terminal_authority": False,
        "new_primitive_required": False if representation_closed else None,
        "terminal_credit_delta": 0,
        "hard_nonclaim": "REPRESENTATION_PASS_IS_CURRENT_DECLARED_REGISTRY_ONLY_NOT_GLOBAL_OPEN_WORLD_COMPLETENESS",
    }

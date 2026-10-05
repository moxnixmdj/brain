"""Compile the current seven Root3 subprocess effect classes onto one shared
zero-ambient confinement substrate plus three fail-closed policy modes.

This is a structural policy reduction only.  It never grants effect authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ROOT3_SEVEN_CLASS_ONE_SUBSTRATE_POLICY_VERDICT_V1"

EXPECTED_CLASSES = {
    "READ_ONLY_DECLARED_QUERY",
    "TEMPORARY_FILESYSTEM_TRANSFORM",
    "PACKAGE_ENV_MUTATION",
    "LOCAL_LOOPBACK_SERVICE",
    "DECLARED_ARTIFACT_PRODUCTION",
    "BOUND_CHILD_CODE_EXECUTION",
    "ARBITRARY_COMMAND_EXECUTION",
}

POLICY = {
    "READ_ONLY_DECLARED_QUERY": {
        "mode": "CONFINED_NO_MATERIAL_COMMIT",
        "shared_substrate": "canonical/runtime/zero_ambient_authority_launcher_v1.py",
        "material_commit_default": "DENY",
    },
    "TEMPORARY_FILESYSTEM_TRANSFORM": {
        "mode": "CONFINED_NO_MATERIAL_COMMIT",
        "shared_substrate": "canonical/runtime/zero_ambient_authority_launcher_v1.py",
        "material_commit_default": "DENY",
    },
    "LOCAL_LOOPBACK_SERVICE": {
        "mode": "CONFINED_NO_MATERIAL_COMMIT",
        "shared_substrate": "canonical/runtime/zero_ambient_authority_launcher_v1.py",
        "material_commit_default": "DENY",
    },
    "BOUND_CHILD_CODE_EXECUTION": {
        "mode": "CONFINED_NO_MATERIAL_COMMIT",
        "shared_substrate": "canonical/runtime/zero_ambient_authority_launcher_v1.py",
        "material_commit_default": "DENY",
    },
    "DECLARED_ARTIFACT_PRODUCTION": {
        "mode": "CONFINED_TYPED_PARENT_FINALIZATION",
        "shared_substrate": "canonical/runtime/zero_ambient_authority_launcher_v1.py",
        "material_commit_default": "DENY",
    },
    "PACKAGE_ENV_MUTATION": {
        "mode": "DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY",
        "shared_substrate": None,
        "material_commit_default": "DENY",
    },
    "ARBITRARY_COMMAND_EXECUTION": {
        "mode": "DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY",
        "shared_substrate": None,
        "material_commit_default": "DENY",
    },
}


class EffectPolicyReductionError(RuntimeError):
    pass


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_policy(
    registry_governance: Mapping[str, Any],
    reduction_governance: Mapping[str, Any],
) -> dict[str, Any]:
    counts = (
        registry_governance.get("partition", {}).get("class_counts")
        if isinstance(registry_governance, Mapping)
        else None
    )
    if not isinstance(counts, Mapping):
        raise EffectPolicyReductionError("REGISTRY_CLASS_COUNTS_MISSING")
    registry_classes = set(counts)
    if registry_classes != EXPECTED_CLASSES:
        raise EffectPolicyReductionError(
            "EFFECT_CLASS_SET_DRIFT:missing="
            + repr(sorted(EXPECTED_CLASSES - registry_classes))
            + ":extra="
            + repr(sorted(registry_classes - EXPECTED_CLASSES))
        )
    if set(POLICY) != EXPECTED_CLASSES:
        raise EffectPolicyReductionError("POLICY_CLASS_SET_NOT_EXACT")

    modes = {}
    substrate_paths = set()
    for effect_class, policy in POLICY.items():
        mode = policy["mode"]
        modes.setdefault(mode, []).append(effect_class)
        if policy["material_commit_default"] != "DENY":
            raise EffectPolicyReductionError(
                "MATERIAL_COMMIT_NOT_FAIL_CLOSED:" + effect_class
            )
        substrate = policy["shared_substrate"]
        if substrate is not None:
            substrate_paths.add(substrate)

    if substrate_paths != {
        "canonical/runtime/zero_ambient_authority_launcher_v1.py"
    }:
        raise EffectPolicyReductionError("SHARED_SUBSTRATE_NOT_UNIQUE")

    if set(modes["DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY"]) != {
        "PACKAGE_ENV_MUTATION",
        "ARBITRARY_COMMAND_EXECUTION",
    }:
        raise EffectPolicyReductionError("DANGEROUS_CLASS_DENY_SET_DRIFT")

    declared_modes = reduction_governance.get("policy_modes")
    if not isinstance(declared_modes, Mapping) or set(declared_modes) != set(modes):
        raise EffectPolicyReductionError("GOVERNANCE_POLICY_MODE_SET_DRIFT")

    declared_classes = set()
    for mode, record in declared_modes.items():
        if not isinstance(record, Mapping):
            raise EffectPolicyReductionError("GOVERNANCE_MODE_RECORD_INVALID")
        mode_classes = set(record.get("classes") or [])
        if mode_classes != set(modes[mode]):
            raise EffectPolicyReductionError("GOVERNANCE_MODE_CLASS_DRIFT:" + mode)
        declared_classes |= mode_classes
        if record.get("default_material_commit") != "DENY":
            raise EffectPolicyReductionError("GOVERNANCE_MODE_NOT_FAIL_CLOSED:" + mode)

    if declared_classes != EXPECTED_CLASSES:
        raise EffectPolicyReductionError("GOVERNANCE_CLASS_COVERAGE_INCOMPLETE")

    accounting = reduction_governance.get("accounting") or {}
    for key in (
        "incremental_spend_usd",
        "new_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            raise EffectPolicyReductionError("NONZERO_ACCOUNTING:" + key)

    for flag in (
        "scheduling_authority",
        "execution_authority",
        "promotion_authority",
        "fresh_reality_authority",
    ):
        if reduction_governance.get(flag) is not False:
            raise EffectPolicyReductionError("AUTHORITY_ESCALATION:" + flag)

    return {
        "schema": SCHEMA,
        "status": "PASS__7_EFFECT_CLASSES_SHARE_1_CONFINEMENT_SUBSTRATE_PLUS_3_FAIL_CLOSED_POLICY_MODES__ZERO_CREDIT",
        "effect_class_count": len(EXPECTED_CLASSES),
        "policy_mode_count": len(modes),
        "shared_os_confinement_substrate_count": len(substrate_paths),
        "shared_os_confinement_substrates": sorted(substrate_paths),
        "mode_class_counts": {k: len(v) for k, v in sorted(modes.items())},
        "dangerous_default_deny_classes": sorted(
            modes["DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY"]
        ),
        "duplicated_sandbox_implementations_deleted": 6,
        "sandbox_implementation_reduction_percent": 6 / 7 * 100.0,
        "deduction": (
            "THE_CURRENT_SEVEN_EFFECT_CLASSES_DO_NOT_REQUIRE_SEVEN_OS_SANDBOXES; "
            "ALL_NON_DENIED_CLASSES_REUSE_ONE_ZERO_AMBIENT_CHILD_SUBSTRATE; "
            "DECLARED_ARTIFACT_PRODUCTION_ADDS_ONLY_TYPED_PARENT_FINALIZATION; "
            "PACKAGE_ENV_MUTATION_AND_ARBITRARY_COMMAND_EXECUTION_REMAIN_DEFAULT_DENY."
        ),
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }


def audit(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root)
    registry = _load(
        root
        / "canonical/governance/ROOT3_SUBPROCESS_EFFECT_CLASS_REGISTRY_20261005_V1.json"
    )
    reduction = _load(
        root
        / "canonical/governance/ROOT3_SEVEN_CLASS_ONE_SUBSTRATE_POLICY_20261005_V1.json"
    )
    return compile_policy(registry, reduction)


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))

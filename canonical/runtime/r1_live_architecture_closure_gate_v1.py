"""Fail-closed structural closure gate for R1.

R1 is not "closed" because a boolean says so. It is closed only while the
current live architecture remains one coherent public boundary:

ownership -> universal invocation -> canonical front door -> subordinate
execution/learning/reuse/repair surfaces -> exact authority bindings.

The gate intentionally does not test semantic intent-to-capability selection.
That is R2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_R1_LIVE_ARCHITECTURE_CLOSURE_GATE_V1"
ROOT = Path(__file__).resolve().parents[2]
ACTIVATION_PATH = ROOT / "canonical/governance/LIVE_BRAIN_RUNTIME_V1_ACTIVATION_20261008_V1.json"
AUTHORITY_PATH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
FABRIC_PATH = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"
INVOKER_PATH = ROOT / "canonical/runtime/live_capability_invoker_v1.py"
SUBRUNTIME_PATH = ROOT / "canonical/runtime/live_brain_runtime_v1.py"

EXPECTED_PUBLIC_ENTRYPOINT = "canonical.runtime.unified_cognitive_fabric_v1.run"
EXPECTED_SUBRUNTIME_ENTRYPOINT = "canonical.runtime.live_brain_runtime_v1.run"

REQUIRED_ENGINE_BINDINGS = {
    "RAW_GOAL": "live_brain_runtime_v1.run(raw_bound)",
    "COMPILED_TASK": "live_brain_runtime_v1.run(compiled_bound)",
    "ADEQUATE_DECISION": "live_brain_runtime_v1.run(decision)",
    "ADAPTIVE_SOLVER": "live_brain_runtime_v1.run(generic)",
    "LEARNING_EPISODE": "autonomous_verified_self_improvement_v1.run_learning_episode",
    "IMPROVEMENT_CYCLE": "r3_improvement_queue_driver_v1.drain",
    "CAPABILITY_SCHEDULER": "capability_first_scheduler_v1.rank_work",
    "REPAIR_SYNTHESIS": "live_brain_runtime_v1.synthesize_failure_repair",
    "REPAIR_CYCLE": "live_brain_runtime_v1.execute_failure_repair_cycle",
    "LIVE_CAPABILITY": "live_capability_invoker_v1.invoke",
    "LIVE_COMPOSITION": "live_capability_composition_v1.execute",
}

REQUIRED_SUBRUNTIME_SURFACES = {
    "GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
    "UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
    "AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1",
    "LIVE_INTEGRATED_BOUND_BRAIN_V1",
    "P3_REAL_CONTEXT_V12",
    "H100_VERIFIED_CAPABILITY_REGISTRY_V8",
    "CAPABILITY_FIRST_SCHEDULER_V1",
    "COUNTEREXAMPLE_GUIDED_CAUSAL_ARCHITECTURE_SYNTHESIZER_V1",
    "VERIFIED_REPAIR_REPLAY_LOOP_V1",
}

REQUIRED_ACTIVATION_INVARIANTS = {
    "ONE_CANONICAL_PUBLIC_FRONT_DOOR__UNIFIED_COGNITIVE_FABRIC_V1",
    "NATIVE_VERIFICATION_CONTRACTS_PRESERVED",
    "V12_EXECUTION_EXPERIENCE_AUTOMATICALLY_FED_TO_R3_WHEN_LEARNING_ENABLED",
    "PRIOR_VERIFIED_EPISODES_AUTOMATICALLY_REUSED_IN_V12_SCOPE",
    "ACTIVE_VERIFIED_SKILLS_AUTOMATICALLY_LOADED_FOR_SKILL_AWARE_PLANNING",
    "NO_PARALLEL_REIMPLEMENTATION_OF_EXISTING_EXECUTION_ENGINES",
    "LIVE_BRAIN_RUNTIME_V1_HAS_NO_INDEPENDENT_PUBLIC_AUTHORITY",
    "HETEROGENEOUS_LIVE_CAPABILITY_COMPOSITION_FAIL_CLOSED",
    "LIVE_COMPOSITION_OUTCOMES_AUTOMATICALLY_OBSERVED_BY_R3",
}


class R1ClosureError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise R1ClosureError("JSON_NOT_OBJECT:" + str(path))
    return dict(doc)


def _authority_binding_errors(
    authority: Mapping[str, Any],
    *,
    fabric_blob: str,
    invoker_blob: str,
    subruntime_blob: str,
) -> list[str]:
    errors: list[str] = []
    ownership = authority.get("live_capability_ownership_20261008_v1")
    invocation = authority.get("r1_universal_live_capability_invocation_20261008_v1")
    if not isinstance(ownership, Mapping):
        errors.append("AUTHORITY_LIVE_OWNERSHIP_NODE_MISSING")
    else:
        if ownership.get("r1_structural_closure") is not True:
            errors.append("AUTHORITY_R1_CLOSURE_NOT_TRUE")
        if ownership.get("canonical_public_entrypoint") != EXPECTED_PUBLIC_ENTRYPOINT:
            errors.append("AUTHORITY_PUBLIC_ENTRYPOINT_DRIFT")
        if ownership.get("subordinate_runtime_public_authority") is not False:
            errors.append("AUTHORITY_SUBRUNTIME_PUBLIC_AUTHORITY_DRIFT")
        fabric = ownership.get("unified_fabric")
        inv = ownership.get("invoker")
        sub = ownership.get("subordinate_runtime")
        if not isinstance(fabric, Mapping) or fabric.get("git_blob_sha") != fabric_blob:
            errors.append("AUTHORITY_FABRIC_BLOB_DRIFT")
        if not isinstance(inv, Mapping) or inv.get("git_blob_sha") != invoker_blob:
            errors.append("AUTHORITY_INVOKER_BLOB_DRIFT")
        if not isinstance(sub, Mapping) or sub.get("git_blob_sha") != subruntime_blob:
            errors.append("AUTHORITY_SUBRUNTIME_BLOB_DRIFT")
    if not isinstance(invocation, Mapping):
        errors.append("AUTHORITY_UNIVERSAL_INVOCATION_NODE_MISSING")
    else:
        fabric = invocation.get("unified_fabric")
        runtime = invocation.get("runtime")
        if not isinstance(fabric, Mapping) or fabric.get("git_blob_sha") != fabric_blob:
            errors.append("INVOCATION_AUTHORITY_FABRIC_BLOB_DRIFT")
        if not isinstance(runtime, Mapping) or runtime.get("git_blob_sha") != invoker_blob:
            errors.append("INVOCATION_AUTHORITY_INVOKER_BLOB_DRIFT")
        if int(invocation.get("missing_invocation_contract_count", -1)) != 0:
            errors.append("INVOCATION_AUTHORITY_MISSING_CONTRACTS")
    return errors


def evaluate(
    engine_descriptors: Mapping[str, str],
    *,
    ownership: Mapping[str, Any],
    invocation: Mapping[str, Any],
    subruntime_surfaces: Sequence[str],
    canonical_public_entrypoint: str,
    subordinate_runtime_entrypoint: str,
    activation_path: str | Path = ACTIVATION_PATH,
    authority_path: str | Path = AUTHORITY_PATH,
) -> dict[str, Any]:
    errors: list[str] = []

    if not isinstance(engine_descriptors, Mapping):
        raise R1ClosureError("ENGINE_DESCRIPTORS_NOT_OBJECT")
    for mode, expected in REQUIRED_ENGINE_BINDINGS.items():
        if engine_descriptors.get(mode) != expected:
            errors.append("ENGINE_BINDING_DRIFT:" + mode)

    if canonical_public_entrypoint != EXPECTED_PUBLIC_ENTRYPOINT:
        errors.append("PUBLIC_ENTRYPOINT_DRIFT")
    if subordinate_runtime_entrypoint != EXPECTED_SUBRUNTIME_ENTRYPOINT:
        errors.append("SUBRUNTIME_ENTRYPOINT_DRIFT")

    surface_set = {str(x) for x in subruntime_surfaces}
    missing_surfaces = sorted(REQUIRED_SUBRUNTIME_SURFACES - surface_set)
    errors.extend("SUBRUNTIME_SURFACE_MISSING:" + x for x in missing_surfaces)

    if ownership.get("pass") is not True:
        errors.append("LIVE_OWNERSHIP_NOT_CLOSED")
    if ownership.get("live_owned_equals_fabric_reachable") is not True:
        errors.append("LIVE_OWNED_NOT_FABRIC_REACHABLE")
    if invocation.get("pass") is not True:
        errors.append("UNIVERSAL_INVOCATION_COVERAGE_NOT_CLOSED")
    if int(invocation.get("missing_capability_count", -1)) != 0:
        errors.append("UNIVERSAL_INVOCATION_CONTRACTS_MISSING")
    if int(invocation.get("capability_count", -1)) != int(
        ownership.get("live_owned_capability_count", -2)
    ):
        errors.append("OWNERSHIP_INVOCATION_COUNT_DIVERGENCE")

    activation = _json(Path(activation_path))
    if activation.get("status") != "ACTIVE_SUBORDINATE_EXECUTION_RUNTIME":
        errors.append("ACTIVATION_STATUS_DRIFT")
    if activation.get("public_entrypoint") != EXPECTED_PUBLIC_ENTRYPOINT:
        errors.append("ACTIVATION_PUBLIC_ENTRYPOINT_DRIFT")
    if activation.get("canonical_public_entrypoint") != EXPECTED_PUBLIC_ENTRYPOINT:
        errors.append("ACTIVATION_CANONICAL_PUBLIC_ENTRYPOINT_DRIFT")
    if activation.get("subruntime_entrypoint") != EXPECTED_SUBRUNTIME_ENTRYPOINT:
        errors.append("ACTIVATION_SUBRUNTIME_ENTRYPOINT_DRIFT")
    if activation.get("role") != "SUBORDINATE_EXECUTION_RUNTIME__R3_REUSE_REPAIR_AND_COMPATIBILITY_CARRIER":
        errors.append("ACTIVATION_SUBRUNTIME_ROLE_DRIFT")
    activation_invariants = {
        str(x) for x in activation.get("invariants", [])
        if isinstance(x, str)
    }
    missing_activation = sorted(REQUIRED_ACTIVATION_INVARIANTS - activation_invariants)
    errors.extend("ACTIVATION_INVARIANT_MISSING:" + x for x in missing_activation)

    fabric_blob = _git_blob_sha(FABRIC_PATH)
    invoker_blob = _git_blob_sha(INVOKER_PATH)
    subruntime_blob = _git_blob_sha(SUBRUNTIME_PATH)
    authority = _json(Path(authority_path))
    errors.extend(
        _authority_binding_errors(
            authority,
            fabric_blob=fabric_blob,
            invoker_blob=invoker_blob,
            subruntime_blob=subruntime_blob,
        )
    )

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__R1_LIVE_ARCHITECTURE_CLOSED_AND_DRIFT_LOCKED"
            if passed
            else "FAIL_CLOSED__R1_LIVE_ARCHITECTURE_DRIFT"
        ),
        "pass": passed,
        "errors": errors,
        "canonical_public_entrypoint": canonical_public_entrypoint,
        "subordinate_runtime_entrypoint": subordinate_runtime_entrypoint,
        "subordinate_runtime_public_authority": False,
        "required_engine_binding_count": len(REQUIRED_ENGINE_BINDINGS),
        "required_subruntime_surface_count": len(REQUIRED_SUBRUNTIME_SURFACES),
        "missing_subruntime_surfaces": missing_surfaces,
        "live_owned_capability_count": ownership.get("live_owned_capability_count"),
        "universally_invocable_capability_count": invocation.get("supported_capability_count"),
        "fabric_blob_sha": fabric_blob,
        "invoker_blob_sha": invoker_blob,
        "subruntime_blob_sha": subruntime_blob,
        "semantic_selection_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

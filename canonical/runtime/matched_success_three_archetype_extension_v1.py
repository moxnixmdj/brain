from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.matched_success_scope_compiler_v1 import REQUIRED

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_THREE_ARCHETYPE_EXTENSION_VERIFY_V1"
PLAN = "canonical/governance/MATCHED_SUCCESS_THREE_ARCHETYPE_EXTENSION_V1.json"
LEGACY = "canonical/governance/MATCHED_SUCCESS_LEGACY_T2_REUSE_AUDIT_V1.json"

EXPECTED_ARCHETYPES = {
    "ADAPTIVE_BROWSER_WORKFLOW",
    "RESEARCH_DELEGATED_ARTIFACT",
    "CODING_DEBUG_TOOL_DISCOVERY",
}

EXPECTED_GUARDS = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types":
        ("THREE_DISTINCT_ACTION_TYPES_OBSERVED", "COLLAPSE_TO_TWO_ACTION_TYPES"),
    "dimension:long_horizon_state_retention":
        ("CHECKPOINT_RETENTION_ACROSS_LATE_STEP", "DROP_EARLY_STATE_BEFORE_LATE_USE"),
    "dimension:minimal_oversight_completion":
        ("NO_HUMAN_INTERVENTION_AFTER_START", "REQUIRE_HUMAN_INTERVENTION"),
    "dimension:multi_constraint_instruction_compliance":
        ("ALL_FROZEN_CONSTRAINTS_SATISFIED", "VIOLATE_ONE_FROZEN_CONSTRAINT"),
    "dimension:requirement_change":
        ("POST_START_REQUIREMENT_CHANGE_INCORPORATED", "IGNORE_RUNTIME_REQUIREMENT_CHANGE"),
    "dimension:research_plus_tool_use_plus_artifact_creation":
        ("RESEARCH_TOOL_ARTIFACT_CHAIN_COMPLETED", "SKIP_RESEARCH_OR_ARTIFACT_STAGE"),
    "dimension:browser_or_computer_action_plus_memory_plus_recovery":
        ("BROWSER_MEMORY_RECOVERY_CHAIN_COMPLETED", "DROP_MEMORY_OR_RECOVERY_STAGE"),
    "dimension:coding_plus_debugging_plus_tool_discovery":
        ("CODE_DEBUG_TOOL_DISCOVERY_CHAIN_COMPLETED", "SKIP_DEBUG_OR_TOOL_DISCOVERY_STAGE"),
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production":
        ("DELEGATION_SYNTHESIS_ARTIFACT_CHAIN_COMPLETED", "SKIP_DELEGATION_OR_EVIDENCE_SYNTHESIS"),
    "dimension:cross_capability_state_handoff_and_rollback":
        ("HANDOFF_AND_ROLLBACK_STATE_HASH_VERIFIED", "CORRUPT_HANDOFF_OR_ROLLBACK_STATE"),
}


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text())
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def validate(plan: Mapping[str, Any], legacy: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    required_all = set().union(*REQUIRED.values())
    legacy_direct = set((legacy.get("direct_legacy_substrate_witnesses") or {}).keys())
    expected_missing = required_all - legacy_direct

    if len(required_all) != 16:
        errors.append("NORMALIZED_REQUIRED_DIMENSION_COUNT_DRIFT")
    if len(legacy_direct) != 6:
        errors.append("LEGACY_DIRECT_DIMENSION_COUNT_DRIFT")
    if expected_missing != set(EXPECTED_GUARDS):
        errors.append("DERIVED_MISSING_SET_DRIFT")

    if set(plan.get("missing_atoms") or []) != expected_missing:
        errors.append("PLAN_MISSING_ATOM_SET_MISMATCH")

    guards = plan.get("atom_guards")
    if not isinstance(guards, Mapping):
        errors.append("ATOM_GUARDS_INVALID")
    else:
        if set(guards) != expected_missing:
            errors.append("ATOM_GUARD_SET_MISMATCH")
        for atom, pair in EXPECTED_GUARDS.items():
            if list(guards.get(atom) or []) != list(pair):
                errors.append("ATOM_GUARD_MISMATCH:" + atom)

    archetypes = plan.get("archetypes")
    if not isinstance(archetypes, list) or len(archetypes) != 3:
        errors.append("ARCHETYPE_COUNT_INVALID")
        archetypes = []

    seen: set[str] = set()
    coverage: set[str] = set()
    for row in archetypes:
        if not isinstance(row, Mapping):
            errors.append("ARCHETYPE_ROW_INVALID")
            continue
        aid = row.get("id")
        if not isinstance(aid, str) or not aid:
            errors.append("ARCHETYPE_ID_INVALID")
            continue
        if aid in seen:
            errors.append("ARCHETYPE_ID_DUPLICATE:" + aid)
        seen.add(aid)
        atoms = row.get("coverage")
        if not isinstance(atoms, list):
            errors.append("ARCHETYPE_COVERAGE_INVALID:" + aid)
            continue
        atom_set = set(atoms)
        extra = atom_set - expected_missing
        if extra:
            errors.append("ARCHETYPE_UNKNOWN_ATOMS:" + aid)
        coverage.update(atom_set)

    if seen != EXPECTED_ARCHETYPES:
        errors.append("ARCHETYPE_ID_SET_MISMATCH")
    if coverage != expected_missing:
        errors.append("ARCHETYPE_UNION_COVERAGE_INCOMPLETE")

    by_id = {
        str(row.get("id")): set(row.get("coverage") or [])
        for row in archetypes
        if isinstance(row, Mapping)
    }
    must = {
        "ADAPTIVE_BROWSER_WORKFLOW": {
            "dimension:browser_or_computer_action_plus_memory_plus_recovery",
            "dimension:requirement_change",
        },
        "RESEARCH_DELEGATED_ARTIFACT": {
            "dimension:research_plus_tool_use_plus_artifact_creation",
            "dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
        },
        "CODING_DEBUG_TOOL_DISCOVERY": {
            "dimension:coding_plus_debugging_plus_tool_discovery",
            "dimension:requirement_change",
        },
    }
    for aid, atoms in must.items():
        if not atoms.issubset(by_id.get(aid, set())):
            errors.append("ARCHETYPE_LOAD_BEARING_CORE_MISSING:" + aid)

    cross = "dimension:cross_capability_state_handoff_and_rollback"
    if sum(cross in x for x in by_id.values()) < 2:
        errors.append("ROLLBACK_NOT_CROSS_ARCHETYPE")

    info = plan.get("information_boundary")
    if not isinstance(info, Mapping) or info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("HIDDEN_ORACLE_BOUNDARY_INVALID")

    policy = plan.get("generator_policy")
    if not isinstance(policy, Mapping):
        errors.append("GENERATOR_POLICY_INVALID")
    else:
        if policy.get("terminal_cases_generated_now") is not False:
            errors.append("TERMINAL_CASE_GENERATION_OVERCLAIM")
        for key in (
            "future_generator_content_addressed",
            "future_case_count_fixed_before_first_result",
            "no_adaptive_case_selection",
            "no_case_replacement",
        ):
            if policy.get(key) is not True:
                errors.append("GENERATOR_POLICY_NOT_FROZEN:" + key)

    for key in ("execution_authority", "promotion_authority", "fresh_reality_authority"):
        if plan.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)

    return {
        "schema": SCHEMA,
        "status": "PASS__THREE_ARCHETYPE_EXTENSION_COVERS_EXACT_10_MISSING_DIMENSIONS__ZERO_CREDIT"
        if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(errors),
        "required_dimension_count": len(required_all),
        "legacy_reused_dimension_count": len(legacy_direct),
        "new_dimension_count": len(expected_missing),
        "archetype_count": len(seen),
        "terminal_cases_generated": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def evaluate() -> dict[str, Any]:
    plan = _load(PLAN)
    legacy = _load(LEGACY)
    auth = plan.get("authority") or {}
    expected = {
        "legacy_audit": "43d2b820ac1389c7e1e76f907acf2f6f11311607",
        "scope_compiler": "2e344ccaa611cda7764d4d70557f1e5bdec9cf3c",
        "isolation": "1ceef520c4022c6059abbb70923e8049801da192",
        "reducer": "6b2696d70f9d4a9d9768dbd7bd097d62e7d4fd67",
    }
    out = validate(plan, legacy)
    errors = list(out["errors"])
    for key, sha in expected.items():
        row = auth.get(key)
        if not isinstance(row, Mapping) or row.get("git_blob_sha") != sha:
            errors.append("AUTHORITY_BINDING_DRIFT:" + key)
            continue
        path = row.get("path")
        if not isinstance(path, str) or _blob(path) != sha:
            errors.append("AUTHORITY_BLOB_MISMATCH:" + key)
    out["errors"] = sorted(set(errors))
    out["pass"] = not out["errors"]
    if not out["pass"]:
        out["status"] = "FAIL_CLOSED"
    return out


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))

"""Fail-closed target-identity truth lock for current Opus 5.5 Root2 predicates.

This module intentionally grants zero acceptance credit.  It checks that the
current 18 Root2-touching predicates retain their frozen target semantics and
that live leaderboard observations remain non-authoritative scheduling evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OPUS55_TARGET_IDENTITY_TRUTH_LOCK_20261005_V1"

EXPECTED_TARGETS = {
    "CODING_TB4_GE_66_4": ("FROZEN_ABSOLUTE", 66.4),
    "CODING_FRONTIERCODE_GE_54_4": ("FROZEN_ABSOLUTE", 54.4),
    "CODING_CURSORBENCH_GE_57_8": ("FROZEN_ABSOLUTE", 57.8),
    "PROWORK_GDPVAL_GE_1846": ("FROZEN_RELATIVE_SNAPSHOT", 1846),
    "PROWORK_AA_BRIEFCASE_GE_1822": ("FROZEN_RELATIVE_SNAPSHOT", 1822),
    "AUTOMATIONBENCH_GE_40": ("FROZEN_ABSOLUTE", 40.0),
    "HLE_TOOLS_GE_67_7": ("FROZEN_ABSOLUTE", 67.7),
    "TB_SCIENCE_GE_58_7": ("HARNESS_CONDITIONAL", 58.7),
    "CHARTOGRAPHY_TOOLS_GE_89": ("FROZEN_ABSOLUTE", 89.0),
    "OSWORLD_2_1_PARTIAL_GE_81_8": ("FROZEN_ABSOLUTE", 81.8),
    "FINANCE_ACCOUNTING_INDEX_GE_61": ("FROZEN_ABSOLUTE", 61.0),
    "FINANCE_AGENT_V2_GE_58_59": ("FROZEN_ABSOLUTE", 58.59),
    "ARTIFACT_AA_BRIEFCASE_GE_1822": ("FROZEN_RELATIVE_SNAPSHOT", 1822),
    "MYSTERYMECHANISM_GE_49_55": ("FROZEN_ABSOLUTE", 49.55),
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR": ("MATCHED_COMPARATOR", None),
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR": ("MATCHED_COMPARATOR", None),
    "IF_SCOPE_BOUNDARY_NONINFERIOR": ("MATCHED_COMPARATOR", None),
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR": ("MATCHED_COMPARATOR", None),
}

REQUIRED_IDENTITY_FIELDS = {
    "MODEL_IDENTITY",
    "MODEL_REVISION_IF_KNOWN",
    "EFFORT_OR_THINKING_LEVEL",
    "FALLBACK_POLICY",
    "BENCHMARK_VERSION",
    "DATASET_REVISION",
    "HARNESS_AND_AGENT_IDENTITY",
    "TOOL_POLICY",
    "GRADER_OR_JUDGE_IDENTITY",
    "TRIAL_COUNT_OR_RATING_POOL",
    "EVALUATION_DATE_OR_FROZEN_SNAPSHOT",
}


class TargetIdentityError(RuntimeError):
    pass


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(manifest: Mapping[str, Any], root2: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != SCHEMA:
        raise TargetIdentityError("SCHEMA_MISMATCH")

    identity = set(manifest.get("identity_tuple") or [])
    if identity != REQUIRED_IDENTITY_FIELDS:
        raise TargetIdentityError("IDENTITY_TUPLE_INCOMPLETE_OR_DRIFTED")

    targets = manifest.get("targets")
    if not isinstance(targets, list):
        raise TargetIdentityError("TARGETS_NOT_LIST")

    by_id: dict[str, Mapping[str, Any]] = {}
    for record in targets:
        if not isinstance(record, Mapping):
            raise TargetIdentityError("TARGET_RECORD_INVALID")
        predicate_id = record.get("predicate_id")
        if not isinstance(predicate_id, str) or not predicate_id:
            raise TargetIdentityError("TARGET_PREDICATE_ID_INVALID")
        if predicate_id in by_id:
            raise TargetIdentityError("DUPLICATE_TARGET:" + predicate_id)
        by_id[predicate_id] = record

    current_ids = {
        p.get("id")
        for p in root2.get("predicates", [])
        if isinstance(p, Mapping) and isinstance(p.get("id"), str)
    }
    expected_ids = set(EXPECTED_TARGETS)
    if current_ids != expected_ids:
        missing = sorted(expected_ids - current_ids)
        extra = sorted(current_ids - expected_ids)
        raise TargetIdentityError(
            "ROOT2_18_SET_DRIFT:missing=" + repr(missing) + ":extra=" + repr(extra)
        )
    if set(by_id) != expected_ids:
        missing = sorted(expected_ids - set(by_id))
        extra = sorted(set(by_id) - expected_ids)
        raise TargetIdentityError(
            "MANIFEST_TARGET_SET_DRIFT:missing=" + repr(missing) + ":extra=" + repr(extra)
        )

    class_counts: dict[str, int] = {}
    for predicate_id, (expected_mode, expected_value) in EXPECTED_TARGETS.items():
        record = by_id[predicate_id]
        mode = record.get("mode")
        if mode != expected_mode:
            raise TargetIdentityError(
                f"MODE_DRIFT:{predicate_id}:{mode!r}!={expected_mode!r}"
            )
        value = record.get("target_value")
        if value != expected_value:
            raise TargetIdentityError(
                f"FROZEN_TARGET_REBASE:{predicate_id}:{value!r}!={expected_value!r}"
            )
        class_counts[mode] = class_counts.get(mode, 0) + 1

    tb = by_id["TB_SCIENCE_GE_58_7"]
    if tb.get("pre_result_route_lock_required") is not True:
        raise TargetIdentityError("TB_SCIENCE_PRE_RESULT_ROUTE_LOCK_NOT_REQUIRED")
    route_map = {
        r.get("route_id"): r.get("target_value")
        for r in tb.get("route_options", [])
        if isinstance(r, Mapping)
    }
    if route_map != {
        "ANTHROPIC_RELEASE_IDENTICAL_SETUP": 58.7,
        "PUBLIC_CURRENT_HARNESS": 63.3,
    }:
        raise TargetIdentityError("TB_SCIENCE_ROUTE_OPTIONS_DRIFT")

    for observation in manifest.get("live_external_observations", []):
        if not isinstance(observation, Mapping):
            raise TargetIdentityError("LIVE_OBSERVATION_INVALID")
        if observation.get("authoritative_for_acceptance") is not False:
            raise TargetIdentityError("LIVE_OBSERVATION_IMPROPERLY_AUTHORITATIVE")

    rules = set(manifest.get("rules") or [])
    required_rules = {
        "LIVE_LEADERBOARD_MOVEMENT_MUST_NOT_REBASE_A_FROZEN_ACCEPTANCE_TARGET",
        "NO_TARGET_OR_SCORER_REBASE_AFTER_BRAIN_RESULTS",
        "NO_FRESH_REALITY_AUTHORITY",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
    }
    if not required_rules.issubset(rules):
        raise TargetIdentityError("REQUIRED_FAIL_CLOSED_RULE_MISSING")

    accounting = manifest.get("accounting") or {}
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
            raise TargetIdentityError("NONZERO_ACCOUNTING:" + key)

    for flag in (
        "scheduling_authority",
        "execution_authority",
        "promotion_authority",
        "fresh_reality_authority",
    ):
        if manifest.get(flag) is not False:
            raise TargetIdentityError("AUTHORITY_ESCALATION:" + flag)

    return {
        "schema": "PROJECT_BRAIN_OPUS55_TARGET_IDENTITY_TRUTH_LOCK_VERDICT_V1",
        "status": "PASS__EXACT_18_ROOT2_TARGETS_FROZEN__LIVE_DRIFT_QUARANTINED__ZERO_CREDIT",
        "root2_target_count": len(expected_ids),
        "class_counts": class_counts,
        "relative_rating_predicates": sorted(
            k for k, v in EXPECTED_TARGETS.items()
            if v[0] == "FROZEN_RELATIVE_SNAPSHOT"
        ),
        "harness_conditional_predicates": sorted(
            k for k, v in EXPECTED_TARGETS.items()
            if v[0] == "HARNESS_CONDITIONAL"
        ),
        "matched_comparator_predicates": sorted(
            k for k, v in EXPECTED_TARGETS.items()
            if v[0] == "MATCHED_COMPARATOR"
        ),
        "deduction": (
            "CURRENT_ROOT2_TARGET_IDS_AND_NUMERIC_LABELS_ARE_FROZEN; "
            "LIVE_LEADERBOARD_OR_SOCIAL_OBSERVATIONS_CANNOT_REBASE_ACCEPTANCE; "
            "TB_SCIENCE_REQUIRES_PRE_RESULT_HARNESS_ROUTE_LOCK; "
            "RELATIVE_RATINGS_REQUIRE_FROZEN_SNAPSHOT_OR_VERIFIED_RELATIVE_BRIDGE."
        ),
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }


def audit(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root)
    manifest = _load(
        root / "canonical/governance/OPUS55_TARGET_IDENTITY_TRUTH_LOCK_20261005_V1.json"
    )
    root2 = _load(
        root / "canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V3.json"
    )
    return validate_manifest(manifest, root2)


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))

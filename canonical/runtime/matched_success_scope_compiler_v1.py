from __future__ import annotations

from typing import Any, Mapping
import hashlib
import json
import re

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SCOPE_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SCOPE_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR": {
        "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
        "dimension:state_change_after_actions_requiring_replanning",
        "dimension:long_horizon_state_retention",
        "dimension:tool_failure_and_recovery",
        "dimension:subtask_dependency_and_fan_in",
        "dimension:minimal_oversight_completion",
    },
    "IF_SCOPE_BOUNDARY_NONINFERIOR": {
        "dimension:multi_constraint_instruction_compliance",
        "dimension:authorization_and_scope_boundaries",
        "dimension:routine_ambiguity",
        "dimension:requirement_change",
        "dimension:explicit_abstention_and_fail_closed_cases",
    },
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR": {
        "dimension:research_plus_tool_use_plus_artifact_creation",
        "dimension:browser_or_computer_action_plus_memory_plus_recovery",
        "dimension:coding_plus_debugging_plus_tool_discovery",
        "dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
        "dimension:cross_capability_state_handoff_and_rollback",
    },
}


class ScopeError(ValueError):
    pass


def _sha40(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        raise ScopeError(name + "_INVALID")
    return value


def _sha64(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ScopeError(name + "_INVALID")
    return value


def _true(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not True:
        raise ScopeError(prefix + "_" + key.upper() + "_NOT_TRUE")


def _manifest_digest(rows: list[dict[str, Any]]) -> str:
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def compile_scope(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise ScopeError("SCHEMA_INVALID")

        freeze = doc.get("freeze")
        if not isinstance(freeze, Mapping):
            raise ScopeError("FREEZE_INVALID")
        for key in (
            "generator_content_addressed",
            "generator_frozen_before_case_exposure",
            "post_freeze_beacon_or_equivalent_precommitted_randomness",
            "case_count_fixed_before_first_result",
            "scorer_content_addressed",
            "brain_runtime_content_addressed",
            "tool_authority_content_addressed",
            "target_interface_content_addressed",
            "no_case_replacement_after_exposure",
            "no_adaptive_case_selection",
            "no_result_dependent_scope_edit",
        ):
            _true(freeze, key, "FREEZE")
        _sha40(freeze.get("generator_git_blob_sha"), "GENERATOR_GIT_BLOB_SHA")
        _sha40(freeze.get("scorer_git_blob_sha"), "SCORER_GIT_BLOB_SHA")
        _sha40(freeze.get("brain_commit_sha"), "BRAIN_COMMIT_SHA")
        _sha64(freeze.get("tool_authority_sha256"), "TOOL_AUTHORITY_SHA256")
        _sha64(freeze.get("target_interface_sha256"), "TARGET_INTERFACE_SHA256")

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ScopeError("CASES_INVALID")

        fixed_count = freeze.get("fixed_case_count")
        if not isinstance(fixed_count, int) or fixed_count <= 0:
            raise ScopeError("FIXED_CASE_COUNT_INVALID")
        if len(cases) != fixed_count:
            raise ScopeError("CASE_COUNT_MISMATCH")

        seen_ids: set[str] = set()
        manifest_rows: list[dict[str, Any]] = []
        union_by_target = {key: set() for key in REQUIRED}

        for index, raw in enumerate(cases):
            if not isinstance(raw, Mapping):
                raise ScopeError(f"CASE_{index}_INVALID")
            cid = raw.get("case_id")
            if not isinstance(cid, str) or not cid.strip():
                raise ScopeError(f"CASE_{index}_ID_INVALID")
            cid = cid.strip()
            if cid in seen_ids:
                raise ScopeError("CASE_ID_DUPLICATE:" + cid)
            seen_ids.add(cid)

            payload_sha = _sha64(raw.get("case_payload_sha256"), f"CASE_{index}_PAYLOAD_SHA256")
            initial_sha = _sha64(raw.get("case_initial_state_sha256"), f"CASE_{index}_INITIAL_SHA256")

            coverage = raw.get("coverage")
            if not isinstance(coverage, Mapping):
                raise ScopeError(f"CASE_{index}_COVERAGE_INVALID")
            if coverage.get("independently_verified") is not True:
                raise ScopeError(f"CASE_{index}_COVERAGE_NOT_VERIFIED")
            _sha64(coverage.get("receipt_sha256"), f"CASE_{index}_COVERAGE_RECEIPT_SHA256")

            normalized: dict[str, list[str]] = {}
            target_atoms = coverage.get("target_atoms")
            if not isinstance(target_atoms, Mapping):
                raise ScopeError(f"CASE_{index}_TARGET_ATOMS_INVALID")

            for target in REQUIRED:
                values = target_atoms.get(target, [])
                if not isinstance(values, list):
                    raise ScopeError(f"CASE_{index}_{target}_ATOMS_INVALID")
                if any(not isinstance(x, str) or not x for x in values):
                    raise ScopeError(f"CASE_{index}_{target}_ATOM_ITEM_INVALID")
                atom_set = set(values)
                unknown = atom_set - REQUIRED[target]
                if unknown:
                    raise ScopeError(
                        f"CASE_{index}_{target}_UNKNOWN_ATOMS:" + ",".join(sorted(unknown))
                    )
                union_by_target[target].update(atom_set)
                normalized[target] = sorted(atom_set)

            manifest_rows.append({
                "case_id": cid,
                "case_payload_sha256": payload_sha,
                "case_initial_state_sha256": initial_sha,
                "target_atoms": normalized,
                "coverage_receipt_sha256": coverage["receipt_sha256"],
            })

        missing = {
            target: sorted(REQUIRED[target] - union_by_target[target])
            for target in REQUIRED
            if REQUIRED[target] - union_by_target[target]
        }
        if missing:
            raise ScopeError("REQUIRED_ATOM_COVERAGE_INCOMPLETE:" + json.dumps(missing, sort_keys=True))

        manifest_rows.sort(key=lambda x: x["case_id"])
        digest = _manifest_digest(manifest_rows)
        expected_digest = doc.get("case_manifest_sha256")
        if expected_digest is not None:
            if _sha64(expected_digest, "CASE_MANIFEST_SHA256") != digest:
                raise ScopeError("CASE_MANIFEST_SHA256_MISMATCH")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SUCCESS_SCOPE",
            "case_count": len(manifest_rows),
            "case_manifest_sha256": digest,
            "required_atom_count": sum(len(v) for v in REQUIRED.values()),
            "required_atoms": {k: sorted(v) for k, v in REQUIRED.items()},
            "coverage_complete": True,
            "case_generation_frozen": True,
            "no_result_dependent_scope_edit": True,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except ScopeError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

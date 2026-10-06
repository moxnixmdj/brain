from __future__ import annotations

from typing import Any, Mapping
import re

SCHEMA = "PROJECT_BRAIN_BRAIN_FIRST_DIFFERENTIAL_PREWAVE_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_BRAIN_FIRST_DIFFERENTIAL_PREWAVE_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")


class PrewaveError(ValueError):
    pass


def _receipt(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise PrewaveError(name + "_INVALID")
    path = value.get("path")
    sha = value.get("git_blob_sha")
    if not isinstance(path, str) or not path.strip():
        raise PrewaveError(name + "_PATH_INVALID")
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        raise PrewaveError(name + "_SHA_INVALID")
    return {"path": path.strip(), "git_blob_sha": sha.lower()}


def _true(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not True:
        raise PrewaveError(prefix + "_" + key.upper() + "_NOT_TRUE")


def compile_brain_first_prewave(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
            raise PrewaveError("SCHEMA_INVALID")

        scope = doc.get("scope")
        if not isinstance(scope, Mapping):
            raise PrewaveError("SCOPE_INVALID")
        for key in (
            "finite",
            "complete",
            "frozen",
            "content_addressed",
            "shared_binary_success_criterion",
            "case_generation_outcome_independent",
            "post_freeze_generation",
            "contamination_clean",
            "case_outcomes_isolated_or_reset_equivalent",
        ):
            _true(scope, key, "SCOPE")
        scope_receipt = _receipt(scope.get("receipt"), "SCOPE_RECEIPT")

        freeze = doc.get("freeze")
        if not isinstance(freeze, Mapping):
            raise PrewaveError("FREEZE_INVALID")
        for key in (
            "brain_commit_frozen",
            "brain_runtime_frozen",
            "dependencies_frozen",
            "scorer_frozen",
            "tool_authority_boundary_frozen",
            "target_identity_exact_opus55_frozen",
            "comparator_neutral_interface_frozen",
            "future_comparator_must_conform",
            "no_brain_repair_after_exposure",
            "no_brain_replay_after_exposure",
        ):
            _true(freeze, key, "FREEZE")
        freeze_receipt = _receipt(freeze.get("receipt"), "FREEZE_RECEIPT")

        reducer = doc.get("reducer")
        if not isinstance(reducer, Mapping):
            raise PrewaveError("REDUCER_INVALID")
        _true(
            reducer,
            "monotone_under_success_set_inclusion",
            "REDUCER",
        )
        _true(
            reducer,
            "same_reducer_for_brain_and_comparator",
            "REDUCER",
        )
        reducer_receipt = _receipt(reducer.get("receipt"), "REDUCER_RECEIPT")

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            raise PrewaveError("CASES_INVALID")

        seen: set[str] = set()
        residual: list[str] = []
        brain_successes: list[str] = []
        comparator_failures: list[str] = []
        comparator_counterexamples: list[str] = []
        missing_comparator: list[str] = []

        for index, case in enumerate(cases):
            if not isinstance(case, Mapping):
                raise PrewaveError(f"CASE_{index}_INVALID")
            cid = case.get("case_id")
            if not isinstance(cid, str) or not cid.strip():
                raise PrewaveError(f"CASE_{index}_ID_INVALID")
            cid = cid.strip()
            if cid in seen:
                raise PrewaveError("CASE_ID_DUPLICATE:" + cid)
            seen.add(cid)

            brain = case.get("brain")
            if not isinstance(brain, Mapping):
                raise PrewaveError(f"CASE_{index}_BRAIN_INVALID")
            if not isinstance(brain.get("success"), bool):
                raise PrewaveError(f"CASE_{index}_BRAIN_SUCCESS_INVALID")
            if brain.get("verified") is not True:
                raise PrewaveError(f"CASE_{index}_BRAIN_NOT_VERIFIED")
            _receipt(brain.get("receipt"), f"CASE_{index}_BRAIN_RECEIPT")

            if brain["success"] is True:
                brain_successes.append(cid)
                continue

            residual.append(cid)
            comparator = case.get("comparator")
            if comparator is None:
                missing_comparator.append(cid)
                continue
            if not isinstance(comparator, Mapping):
                raise PrewaveError(f"CASE_{index}_COMPARATOR_INVALID")
            if comparator.get("exact_opus55") is not True:
                raise PrewaveError(f"CASE_{index}_COMPARATOR_NOT_EXACT_OPUS55")
            if comparator.get("interface_conformant") is not True:
                raise PrewaveError(f"CASE_{index}_COMPARATOR_INTERFACE_NONCONFORMANT")
            if comparator.get("verified") is not True:
                raise PrewaveError(f"CASE_{index}_COMPARATOR_NOT_VERIFIED")
            if not isinstance(comparator.get("success"), bool):
                raise PrewaveError(f"CASE_{index}_COMPARATOR_SUCCESS_INVALID")
            _receipt(
                comparator.get("receipt"),
                f"CASE_{index}_COMPARATOR_RECEIPT",
            )
            if comparator["success"] is True:
                comparator_counterexamples.append(cid)
            else:
                comparator_failures.append(cid)

        common = {
            "schema": OUTPUT_SCHEMA,
            "case_count": len(cases),
            "brain_success_count": len(brain_successes),
            "brain_failure_residual_count": len(residual),
            "brain_failure_residual_ids": residual,
            "comparator_cases_required": residual,
            "scope_receipt": scope_receipt,
            "freeze_receipt": freeze_receipt,
            "reducer_receipt": reducer_receipt,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

        if comparator_counterexamples:
            return {
                **common,
                "status": "VERIFIED_DIFFERENTIAL_COUNTEREXAMPLE",
                "differential_dominance_proved": False,
                "counterexample_case_ids": comparator_counterexamples,
                "reason": "EXACT_OPUS55_SUCCESS_ON_AT_LEAST_ONE_VERIFIED_BRAIN_FAILURE_CASE",
            }

        if not residual:
            return {
                **common,
                "status": "CANDIDATE_COMPARATOR_FREE_DIFFERENTIAL_DOMINANCE",
                "differential_dominance_proved": True,
                "comparator_execution_required": False,
                "reason": "BRAIN_SUCCEEDED_ON_EVERY_CASE_IN_THE_COMPLETE_FROZEN_SCOPE",
            }

        if missing_comparator:
            return {
                **common,
                "status": "RESIDUAL_COMPARATOR_OPEN",
                "differential_dominance_proved": False,
                "comparator_execution_required": True,
                "unresolved_residual_ids": missing_comparator,
                "resolved_residual_failures": comparator_failures,
                "reason": "ONLY_BRAIN_FAILURE_CASES_REMAIN_COMPARATOR_RELEVANT",
            }

        return {
            **common,
            "status": "CANDIDATE_RESIDUAL_ONLY_DIFFERENTIAL_DOMINANCE",
            "differential_dominance_proved": True,
            "comparator_execution_required": True,
            "comparator_executed_case_count": len(residual),
            "reason": "EXACT_OPUS55_FAILED_ON_EVERY_VERIFIED_BRAIN_FAILURE_RESIDUAL_CASE",
        }
    except PrewaveError as exc:
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

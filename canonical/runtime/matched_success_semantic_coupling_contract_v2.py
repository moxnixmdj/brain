from __future__ import annotations

import re
from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SEMANTIC_COUPLING_INPUT_V2"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SEMANTIC_COUPLING_OUTPUT_V2"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_CLASSES = {
    "AGENCY_THREE_TOOL_LONG_HORIZON",
    "INSTRUCTION_CHANGE_CONTROL",
    "RESEARCH_TOOL_ARTIFACT",
    "BROWSER_MEMORY_RECOVERY",
    "CODING_DEBUG_TOOL_DISCOVERY",
    "DELEGATION_SYNTHESIS_ARTIFACT",
    "CROSS_CAPABILITY_HANDOFF_ROLLBACK",
}


class CouplingError(ValueError):
    pass


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise CouplingError(name + "_INVALID")
    return value


def _true(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not True:
        raise CouplingError(prefix + "_" + key.upper() + "_NOT_TRUE")


def _false(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not False:
        raise CouplingError(prefix + "_" + key.upper() + "_NOT_FALSE")


def _intervention(row: Mapping[str, Any], prefix: str) -> dict[str, str]:
    true_run = row.get("true_run")
    ablated = row.get("ablated_run")
    rescue = row.get("rescue_run")
    if not all(isinstance(x, Mapping) for x in (true_run, ablated, rescue)):
        raise CouplingError(prefix + "_INTERVENTION_ROWS_INVALID")

    true_upstream = _sha(true_run.get("upstream_semantic_sha256"), prefix + "_TRUE_UPSTREAM")
    decoy_upstream = _sha(ablated.get("upstream_semantic_sha256"), prefix + "_DECOY_UPSTREAM")
    rescue_upstream = _sha(rescue.get("upstream_semantic_sha256"), prefix + "_RESCUE_UPSTREAM")
    if true_upstream == decoy_upstream:
        raise CouplingError(prefix + "_DECOY_NOT_SEMANTICALLY_DISTINCT")
    if rescue_upstream != true_upstream:
        raise CouplingError(prefix + "_RESCUE_UPSTREAM_NOT_RESTORED")

    _true(true_run, "success", prefix + "_TRUE")
    _false(ablated, "success", prefix + "_ABLATED")
    _true(rescue, "success", prefix + "_RESCUE")

    true_terminal = _sha(
        true_run.get("terminal_semantic_sha256"),
        prefix + "_TRUE_TERMINAL",
    )
    _sha(
        ablated.get("terminal_semantic_sha256"),
        prefix + "_ABLATION_TERMINAL",
    )
    rescue_terminal = _sha(
        rescue.get("terminal_semantic_sha256"),
        prefix + "_RESCUE_TERMINAL",
    )
    if rescue_terminal != true_terminal:
        raise CouplingError(prefix + "_RESCUE_TERMINAL_NOT_RESTORED")

    for label, run in (("TRUE", true_run), ("ABLATED", ablated), ("RESCUE", rescue)):
        receipt = run.get("receipt")
        if not isinstance(receipt, Mapping):
            raise CouplingError(prefix + "_" + label + "_RECEIPT_INVALID")
        _sha(receipt.get("receipt_sha256"), prefix + "_" + label + "_RECEIPT_SHA256")
        _true(receipt, "independent_or_objective", prefix + "_" + label + "_RECEIPT")

    return {
        "true_upstream": true_upstream,
        "decoy_upstream": decoy_upstream,
        "terminal": true_terminal,
    }


def _class_specific(class_id: str, row: Mapping[str, Any], prefix: str) -> None:
    details = row.get("details")
    if not isinstance(details, Mapping):
        raise CouplingError(prefix + "_DETAILS_INVALID")

    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        count = details.get("distinct_action_type_count")
        if not isinstance(count, int) or count < 3:
            raise CouplingError(prefix + "_DISTINCT_ACTION_TYPES_LT_3")
        _sha(details.get("learned_early_value_sha256"), prefix + "_LEARNED_VALUE")
        recall = _sha(details.get("final_recall_sha256"), prefix + "_FINAL_RECALL")
        if recall != details.get("learned_early_value_sha256"):
            raise CouplingError(prefix + "_EARLY_VALUE_NOT_RECALLED")
        gaps = details.get("intervening_component_boundaries")
        if not isinstance(gaps, int) or gaps < 2:
            raise CouplingError(prefix + "_LONG_HORIZON_TOO_SHORT")
        _false(details, "early_value_replayed_to_final_stage", prefix)
        _false(details, "oversight_requested_after_start", prefix)

    elif class_id == "INSTRUCTION_CHANGE_CONTROL":
        pre = _sha(details.get("prechange_task_lineage_sha256"), prefix + "_PRE_LINEAGE")
        post = _sha(details.get("postchange_task_lineage_sha256"), prefix + "_POST_LINEAGE")
        if pre != post:
            raise CouplingError(prefix + "_REQUIREMENT_CHANGE_NOT_SAME_LINEAGE")
        _sha(details.get("mutation_sha256"), prefix + "_MUTATION")
        _false(details, "stale_prechange_output_passes_postchange", prefix)
        _true(details, "revised_output_passes_postchange", prefix)

    elif class_id in {
        "RESEARCH_TOOL_ARTIFACT",
        "DELEGATION_SYNTHESIS_ARTIFACT",
    }:
        producer = _sha(details.get("producer_projection_sha256"), prefix + "_PRODUCER")
        consumed = _sha(details.get("synthesis_bound_upstream_sha256"), prefix + "_SYNTHESIS_BOUND")
        if producer != consumed:
            raise CouplingError(prefix + "_SYNTHESIS_NOT_BOUND_TO_PRODUCER")
        synthesis = _sha(details.get("synthesis_projection_sha256"), prefix + "_SYNTHESIS")
        artifact = _sha(details.get("artifact_bound_upstream_sha256"), prefix + "_ARTIFACT_BOUND")
        if synthesis != artifact:
            raise CouplingError(prefix + "_ARTIFACT_NOT_BOUND_TO_SYNTHESIS")

    elif class_id == "BROWSER_MEMORY_RECOVERY":
        early = _sha(details.get("early_browser_projection_sha256"), prefix + "_EARLY_BROWSER")
        retained = _sha(details.get("retained_memory_sha256"), prefix + "_RETAINED")
        if early != retained:
            raise CouplingError(prefix + "_BROWSER_MEMORY_NOT_RETAINED")
        _true(details, "observable_failure_injected", prefix)
        _true(details, "recovery_passes", prefix)
        _true(details, "goal_relevant_state_preserved", prefix)

    elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        _sha(details.get("premutation_solution_sha256"), prefix + "_PREMUTATION")
        _sha(details.get("mutated_failure_sha256"), prefix + "_MUTATED_FAILURE")
        _true(details, "debug_localizes_injected_failure", prefix)
        _true(details, "tool_route_admissible", prefix)
        _true(details, "repaired_output_passes_original_oracle", prefix)

    elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        pre = _sha(details.get("pre_mutation_state_sha256"), prefix + "_PRE_STATE")
        mutated = _sha(details.get("mutated_state_sha256"), prefix + "_MUTATED_STATE")
        post = _sha(details.get("post_rollback_state_sha256"), prefix + "_POST_STATE")
        if pre == mutated:
            raise CouplingError(prefix + "_MUTATION_DID_NOT_CHANGE_STATE")
        if post != pre:
            raise CouplingError(prefix + "_ROLLBACK_DID_NOT_RESTORE_STATE")
        _true(details, "state_restoration_independently_verified", prefix)

    else:
        raise CouplingError(prefix + "_UNKNOWN_CLASS")


def compile_coupling(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise CouplingError("SCHEMA_INVALID")
        rows = doc.get("classes")
        if not isinstance(rows, list):
            raise CouplingError("CLASSES_INVALID")

        parsed: dict[str, Mapping[str, Any]] = {}
        for i, raw in enumerate(rows):
            if not isinstance(raw, Mapping):
                raise CouplingError(f"CLASS_{i}_INVALID")
            cid = raw.get("class_id")
            if cid not in REQUIRED_CLASSES:
                raise CouplingError(f"CLASS_{i}_ID_INVALID")
            if cid in parsed:
                raise CouplingError("CLASS_ID_DUPLICATE:" + str(cid))
            parsed[str(cid)] = raw

        if set(parsed) != REQUIRED_CLASSES:
            missing = sorted(REQUIRED_CLASSES - set(parsed))
            extra = sorted(set(parsed) - REQUIRED_CLASSES)
            raise CouplingError(
                "CLASS_SET_MISMATCH:MISSING="
                + ",".join(missing)
                + ":EXTRA="
                + ",".join(extra)
            )

        summaries = {}
        for cid in sorted(REQUIRED_CLASSES):
            prefix = cid
            summary = _intervention(parsed[cid], prefix)
            _class_specific(cid, parsed[cid], prefix)
            summaries[cid] = summary

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__INTERVENTIONAL_SEMANTIC_COUPLING_CONTRACT",
            "class_count": len(summaries),
            "classes": summaries,
            "receipt_acknowledgement_only_sufficient": False,
            "ablation_and_rescue_required": True,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except CouplingError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

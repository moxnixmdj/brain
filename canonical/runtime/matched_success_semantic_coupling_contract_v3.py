from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SEMANTIC_COUPLING_INPUT_V3"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_SEMANTIC_COUPLING_OUTPUT_V3"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
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


class CouplingV3Error(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _sha64(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise CouplingV3Error(name + "_INVALID")
    return value


def _sha40(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        raise CouplingV3Error(name + "_INVALID")
    return value


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CouplingV3Error(name + "_INVALID")
    return value.strip()


def _true(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not True:
        raise CouplingV3Error(prefix + "_" + key.upper() + "_NOT_TRUE")


def _false(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not False:
        raise CouplingV3Error(prefix + "_" + key.upper() + "_NOT_FALSE")


def _content_receipt(
    receipt: Any,
    *,
    prefix: str,
    expected: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(receipt, Mapping):
        raise CouplingV3Error(prefix + "_INVALID")
    path = _token(receipt.get("path"), prefix + "_PATH")
    blob = _sha40(receipt.get("git_blob_sha"), prefix + "_GIT_BLOB_SHA")
    _true(receipt, "independent_or_objective", prefix)

    for key, value in expected.items():
        if receipt.get(key) != value:
            raise CouplingV3Error(prefix + "_" + key.upper() + "_MISMATCH")

    return {"path": path, "git_blob_sha": blob}


def _run(
    class_id: str,
    role: str,
    raw: Any,
) -> dict[str, Any]:
    prefix = class_id + "_" + role.upper()
    if not isinstance(raw, Mapping):
        raise CouplingV3Error(prefix + "_INVALID")

    upstream = _sha64(
        raw.get("upstream_semantic_sha256"),
        prefix + "_UPSTREAM_SEMANTIC_SHA256",
    )
    shape = _sha64(
        raw.get("upstream_shape_sha256"),
        prefix + "_UPSTREAM_SHAPE_SHA256",
    )
    terminal = _sha64(
        raw.get("terminal_semantic_sha256"),
        prefix + "_TERMINAL_SEMANTIC_SHA256",
    )
    success = raw.get("success")
    if not isinstance(success, bool):
        raise CouplingV3Error(prefix + "_SUCCESS_INVALID")

    semantic_record = {
        "class_id": class_id,
        "run_role": role,
        "upstream_semantic_sha256": upstream,
        "upstream_shape_sha256": shape,
        "terminal_semantic_sha256": terminal,
        "success": success,
    }
    run_sha = _digest(semantic_record)
    if raw.get("run_semantics_sha256") != run_sha:
        raise CouplingV3Error(prefix + "_RUN_SEMANTICS_SHA256_MISMATCH")

    receipt = _content_receipt(
        raw.get("receipt"),
        prefix=prefix + "_RECEIPT",
        expected={
            "class_id": class_id,
            "run_role": role,
            "run_semantics_sha256": run_sha,
            "upstream_semantic_sha256": upstream,
            "terminal_semantic_sha256": terminal,
            "success": success,
        },
    )

    return {
        "upstream": upstream,
        "shape": shape,
        "terminal": terminal,
        "success": success,
        "run_sha": run_sha,
        "receipt": receipt,
    }


def _details(
    class_id: str,
    raw: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str, dict[str, str]]:
    details = raw.get("details")
    if not isinstance(details, Mapping):
        raise CouplingV3Error(class_id + "_DETAILS_INVALID")

    details_sha = _digest(details)
    if raw.get("details_sha256") != details_sha:
        raise CouplingV3Error(class_id + "_DETAILS_SHA256_MISMATCH")

    receipt = _content_receipt(
        raw.get("details_receipt"),
        prefix=class_id + "_DETAILS_RECEIPT",
        expected={
            "class_id": class_id,
            "details_sha256": details_sha,
        },
    )
    return details, details_sha, receipt


def _class_specific(
    class_id: str,
    details: Mapping[str, Any],
    *,
    true_upstream: str,
    true_terminal: str,
) -> None:
    p = class_id

    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        count = details.get("distinct_action_type_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 3:
            raise CouplingV3Error(p + "_DISTINCT_ACTION_TYPES_LT_3")
        learned = _sha64(
            details.get("learned_early_value_sha256"),
            p + "_LEARNED_EARLY_VALUE_SHA256",
        )
        recalled = _sha64(
            details.get("final_recall_sha256"),
            p + "_FINAL_RECALL_SHA256",
        )
        if learned != true_upstream:
            raise CouplingV3Error(p + "_EARLY_VALUE_NOT_BOUND_TO_TRUE_UPSTREAM")
        if recalled != learned:
            raise CouplingV3Error(p + "_EARLY_VALUE_NOT_RECALLED")
        gaps = details.get("intervening_component_boundaries")
        if not isinstance(gaps, int) or isinstance(gaps, bool) or gaps < 2:
            raise CouplingV3Error(p + "_LONG_HORIZON_TOO_SHORT")
        _false(details, "early_value_replayed_to_final_stage", p)
        _false(details, "oversight_requested_after_start", p)

    elif class_id == "INSTRUCTION_CHANGE_CONTROL":
        pre_semantic = _sha64(
            details.get("prechange_semantic_sha256"),
            p + "_PRECHANGE_SEMANTIC_SHA256",
        )
        if pre_semantic != true_upstream:
            raise CouplingV3Error(p + "_PRECHANGE_NOT_BOUND_TO_TRUE_UPSTREAM")
        pre_lineage = _sha64(
            details.get("prechange_task_lineage_sha256"),
            p + "_PRECHANGE_LINEAGE_SHA256",
        )
        post_lineage = _sha64(
            details.get("postchange_task_lineage_sha256"),
            p + "_POSTCHANGE_LINEAGE_SHA256",
        )
        if pre_lineage != post_lineage:
            raise CouplingV3Error(p + "_REQUIREMENT_CHANGE_NOT_SAME_LINEAGE")
        _sha64(details.get("mutation_sha256"), p + "_MUTATION_SHA256")
        revised = _sha64(
            details.get("revised_output_semantic_sha256"),
            p + "_REVISED_OUTPUT_SEMANTIC_SHA256",
        )
        if revised != true_terminal:
            raise CouplingV3Error(p + "_REVISED_OUTPUT_NOT_BOUND_TO_TRUE_TERMINAL")
        _false(details, "stale_prechange_output_passes_postchange", p)
        _true(details, "revised_output_passes_postchange", p)

    elif class_id in {
        "RESEARCH_TOOL_ARTIFACT",
        "DELEGATION_SYNTHESIS_ARTIFACT",
    }:
        producer = _sha64(
            details.get("producer_projection_sha256"),
            p + "_PRODUCER_PROJECTION_SHA256",
        )
        if producer != true_upstream:
            raise CouplingV3Error(p + "_PRODUCER_NOT_BOUND_TO_TRUE_UPSTREAM")
        synthesis_bound = _sha64(
            details.get("synthesis_bound_upstream_sha256"),
            p + "_SYNTHESIS_BOUND_UPSTREAM_SHA256",
        )
        if synthesis_bound != producer:
            raise CouplingV3Error(p + "_SYNTHESIS_NOT_BOUND_TO_PRODUCER")
        synthesis = _sha64(
            details.get("synthesis_projection_sha256"),
            p + "_SYNTHESIS_PROJECTION_SHA256",
        )
        artifact_bound = _sha64(
            details.get("artifact_bound_upstream_sha256"),
            p + "_ARTIFACT_BOUND_UPSTREAM_SHA256",
        )
        if artifact_bound != synthesis:
            raise CouplingV3Error(p + "_ARTIFACT_NOT_BOUND_TO_SYNTHESIS")
        artifact = _sha64(
            details.get("artifact_semantic_sha256"),
            p + "_ARTIFACT_SEMANTIC_SHA256",
        )
        if artifact != true_terminal:
            raise CouplingV3Error(p + "_ARTIFACT_NOT_BOUND_TO_TRUE_TERMINAL")

    elif class_id == "BROWSER_MEMORY_RECOVERY":
        early = _sha64(
            details.get("early_browser_projection_sha256"),
            p + "_EARLY_BROWSER_PROJECTION_SHA256",
        )
        if early != true_upstream:
            raise CouplingV3Error(p + "_EARLY_BROWSER_NOT_BOUND_TO_TRUE_UPSTREAM")
        retained = _sha64(
            details.get("retained_memory_sha256"),
            p + "_RETAINED_MEMORY_SHA256",
        )
        if retained != early:
            raise CouplingV3Error(p + "_BROWSER_MEMORY_NOT_RETAINED")
        recovered = _sha64(
            details.get("recovered_state_semantic_sha256"),
            p + "_RECOVERED_STATE_SEMANTIC_SHA256",
        )
        if recovered != true_terminal:
            raise CouplingV3Error(p + "_RECOVERY_NOT_BOUND_TO_TRUE_TERMINAL")
        _true(details, "observable_failure_injected", p)
        _true(details, "recovery_passes", p)
        _true(details, "goal_relevant_state_preserved", p)

    elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        premutation = _sha64(
            details.get("premutation_solution_sha256"),
            p + "_PREMUTATION_SOLUTION_SHA256",
        )
        if premutation != true_upstream:
            raise CouplingV3Error(p + "_PREMUTATION_NOT_BOUND_TO_TRUE_UPSTREAM")
        mutated = _sha64(
            details.get("mutated_failure_sha256"),
            p + "_MUTATED_FAILURE_SHA256",
        )
        if mutated == premutation:
            raise CouplingV3Error(p + "_MUTATION_DID_NOT_CHANGE_SEMANTICS")
        repaired = _sha64(
            details.get("repaired_output_semantic_sha256"),
            p + "_REPAIRED_OUTPUT_SEMANTIC_SHA256",
        )
        if repaired != true_terminal:
            raise CouplingV3Error(p + "_REPAIR_NOT_BOUND_TO_TRUE_TERMINAL")
        _true(details, "debug_localizes_injected_failure", p)
        _true(details, "tool_route_admissible", p)
        _true(details, "repaired_output_passes_original_oracle", p)

    elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        pre = _sha64(
            details.get("pre_mutation_state_sha256"),
            p + "_PRE_MUTATION_STATE_SHA256",
        )
        if pre != true_upstream:
            raise CouplingV3Error(p + "_PRE_STATE_NOT_BOUND_TO_TRUE_UPSTREAM")
        mutated = _sha64(
            details.get("mutated_state_sha256"),
            p + "_MUTATED_STATE_SHA256",
        )
        post = _sha64(
            details.get("post_rollback_state_sha256"),
            p + "_POST_ROLLBACK_STATE_SHA256",
        )
        if pre == mutated:
            raise CouplingV3Error(p + "_MUTATION_DID_NOT_CHANGE_STATE")
        if post != pre:
            raise CouplingV3Error(p + "_ROLLBACK_DID_NOT_RESTORE_STATE")
        if post != true_terminal:
            raise CouplingV3Error(p + "_ROLLBACK_NOT_BOUND_TO_TRUE_TERMINAL")
        _true(details, "state_restoration_independently_verified", p)

    else:
        raise CouplingV3Error(p + "_UNKNOWN_CLASS")


def compile_coupling_v3(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise CouplingV3Error("SCHEMA_INVALID")

        rows = doc.get("classes")
        if not isinstance(rows, list):
            raise CouplingV3Error("CLASSES_INVALID")

        parsed: dict[str, Mapping[str, Any]] = {}
        for index, raw in enumerate(rows):
            if not isinstance(raw, Mapping):
                raise CouplingV3Error(f"CLASS_{index}_INVALID")
            class_id = raw.get("class_id")
            if class_id not in REQUIRED_CLASSES:
                raise CouplingV3Error(f"CLASS_{index}_ID_INVALID")
            class_id = str(class_id)
            if class_id in parsed:
                raise CouplingV3Error("CLASS_ID_DUPLICATE:" + class_id)
            parsed[class_id] = raw

        if set(parsed) != REQUIRED_CLASSES:
            raise CouplingV3Error(
                "CLASS_SET_MISMATCH:MISSING="
                + ",".join(sorted(REQUIRED_CLASSES - set(parsed)))
                + ":EXTRA="
                + ",".join(sorted(set(parsed) - REQUIRED_CLASSES))
            )

        summaries: dict[str, Any] = {}
        for class_id in sorted(REQUIRED_CLASSES):
            raw = parsed[class_id]
            true_run = _run(class_id, "true", raw.get("true_run"))
            ablated = _run(class_id, "ablated", raw.get("ablated_run"))
            rescue = _run(class_id, "rescue", raw.get("rescue_run"))

            if true_run["upstream"] == ablated["upstream"]:
                raise CouplingV3Error(class_id + "_DECOY_NOT_SEMANTICALLY_DISTINCT")
            if rescue["upstream"] != true_run["upstream"]:
                raise CouplingV3Error(class_id + "_RESCUE_UPSTREAM_NOT_RESTORED")
            if not (
                true_run["shape"]
                == ablated["shape"]
                == rescue["shape"]
            ):
                raise CouplingV3Error(class_id + "_UPSTREAM_SHAPE_MISMATCH")
            if true_run["success"] is not True:
                raise CouplingV3Error(class_id + "_TRUE_RUN_NOT_SUCCESS")
            if ablated["success"] is not False:
                raise CouplingV3Error(class_id + "_ABLATION_DID_NOT_FAIL")
            if rescue["success"] is not True:
                raise CouplingV3Error(class_id + "_RESCUE_DID_NOT_PASS")
            if rescue["terminal"] != true_run["terminal"]:
                raise CouplingV3Error(class_id + "_RESCUE_TERMINAL_NOT_RESTORED")
            if ablated["terminal"] == true_run["terminal"]:
                raise CouplingV3Error(class_id + "_ABLATION_TERMINAL_NOT_DISTINCT")

            details, details_sha, details_receipt = _details(class_id, raw)
            _class_specific(
                class_id,
                details,
                true_upstream=true_run["upstream"],
                true_terminal=true_run["terminal"],
            )

            summaries[class_id] = {
                "true_run_semantics_sha256": true_run["run_sha"],
                "ablated_run_semantics_sha256": ablated["run_sha"],
                "rescue_run_semantics_sha256": rescue["run_sha"],
                "details_sha256": details_sha,
                "true_run_receipt": true_run["receipt"],
                "ablated_run_receipt": ablated["receipt"],
                "rescue_run_receipt": rescue["receipt"],
                "details_receipt": details_receipt,
            }

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__CONTENT_BOUND_INTERVENTIONAL_SEMANTIC_COUPLING_V3",
            "class_count": len(summaries),
            "classes": summaries,
            "receipt_acknowledgement_only_sufficient": False,
            "run_receipt_field_binding_required": True,
            "details_receipt_binding_required": True,
            "independent_receipt_bytes_verified": False,
            "independent_exact_receipt_verification_required": True,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    except CouplingV3Error as exc:
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

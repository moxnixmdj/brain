"""Independent structural verifier for GDPval rubric acceptance replay evidence."""
from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Mapping

from canonical.runtime.gdpval_rubric_acceptance_index_v1 import SCHEMA as INDEX_SCHEMA
from canonical.runtime.gdpval_rubric_acceptance_replay_v1 import (
    SCHEMA as REPLAY_SCHEMA,
    EXPECTED_REVISION,
    EXPECTED_TASKS,
    EXPECTED_CRITERIA,
)

SCHEMA = "PROJECT_BRAIN_GDPVAL_RUBRIC_ACCEPTANCE_EVIDENCE_VERIFIER_V1"


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def verify(document: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(document, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False,
                "errors": ["DOCUMENT_NOT_OBJECT"], "terminal_authority": False}

    if document.get("schema") != REPLAY_SCHEMA:
        errors.append("REPLAY_SCHEMA_MISMATCH")
    if document.get("status") != "PASS__EXACT_BOUND_PUBLIC_220_RUBRIC_ACCEPTANCE_INDEX":
        errors.append("REPLAY_STATUS_NOT_PASS")
    dataset = document.get("dataset")
    if not isinstance(dataset, Mapping):
        errors.append("DATASET_BINDING_MISSING")
    else:
        if dataset.get("expected_revision") != EXPECTED_REVISION:
            errors.append("EXPECTED_REVISION_MISMATCH")
        if dataset.get("observed_revision") != EXPECTED_REVISION:
            errors.append("OBSERVED_REVISION_MISMATCH")
        if dataset.get("revision_match") is not True:
            errors.append("REVISION_MATCH_NOT_TRUE")

    index = document.get("index")
    if not isinstance(index, Mapping):
        errors.append("INDEX_MISSING")
        index = {}
    if index.get("schema") != INDEX_SCHEMA:
        errors.append("INDEX_SCHEMA_MISMATCH")
    if index.get("status") != "INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA":
        errors.append("INDEX_STATUS_MISMATCH")
    if index.get("source_revision") != EXPECTED_REVISION:
        errors.append("INDEX_SOURCE_REVISION_MISMATCH")

    tasks = index.get("tasks")
    if not isinstance(tasks, list):
        errors.append("TASKS_NOT_LIST")
        tasks = []
    if len(tasks) != EXPECTED_TASKS:
        errors.append("TASK_COUNT_MISMATCH")

    task_ids: set[str] = set()
    criterion_ids: dict[str, str] = {}
    aggregate = {
        "task_count": len(tasks),
        "criterion_count": 0,
        "human_authored_criterion_count": 0,
        "required_true_count": 0,
        "required_false_count": 0,
        "required_null_count": 0,
        "numeric_score_sum": 0.0,
        "criteria_without_numeric_score": 0,
    }

    for task_index, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            errors.append(f"TASK_NOT_OBJECT:{task_index}")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in task_ids:
            errors.append(f"TASK_ID_INVALID_OR_DUPLICATE:{task_index}")
            continue
        task_ids.add(task_id)
        if task.get("source_revision") != EXPECTED_REVISION:
            errors.append(f"TASK_REVISION_MISMATCH:{task_id}")
        criteria = task.get("criteria")
        if not isinstance(criteria, list):
            errors.append(f"CRITERIA_NOT_LIST:{task_id}")
            continue
        if task.get("criterion_count") != len(criteria):
            errors.append(f"CRITERION_COUNT_FIELD_MISMATCH:{task_id}")

        contract_payload = {
            "task_id": task_id,
            "source_revision": EXPECTED_REVISION,
            "criteria": criteria,
        }
        if task.get("contract_sha256") != _digest(contract_payload):
            errors.append(f"CONTRACT_HASH_MISMATCH:{task_id}")

        for criterion_index, criterion in enumerate(criteria):
            if not isinstance(criterion, Mapping):
                errors.append(f"CRITERION_NOT_OBJECT:{task_id}:{criterion_index}")
                continue
            cid = criterion.get("criterion_id")
            text = criterion.get("criterion")
            if not isinstance(cid, str) or not cid:
                errors.append(f"CRITERION_ID_INVALID:{task_id}:{criterion_index}")
                continue
            if not isinstance(text, str) or not text:
                errors.append(f"CRITERION_TEXT_INVALID:{task_id}:{criterion_index}")
                continue
            if criterion.get("task_id") != task_id:
                errors.append(f"CRITERION_TASK_BINDING_MISMATCH:{cid}")
            if criterion.get("criterion_sha256") != sha256(text.encode("utf-8")).hexdigest():
                errors.append(f"CRITERION_TEXT_HASH_MISMATCH:{cid}")
            payload_hash = _digest(dict(criterion))
            prior = criterion_ids.get(cid)
            if prior is not None and prior != payload_hash:
                errors.append(f"CRITERION_ID_COLLISION:{cid}")
            criterion_ids[cid] = payload_hash

            aggregate["criterion_count"] += 1
            if criterion.get("author_type") == "human":
                aggregate["human_authored_criterion_count"] += 1
            required = criterion.get("required")
            if required is True:
                aggregate["required_true_count"] += 1
            elif required is False:
                aggregate["required_false_count"] += 1
            else:
                aggregate["required_null_count"] += 1
            score = criterion.get("score")
            if score is None:
                aggregate["criteria_without_numeric_score"] += 1
            elif isinstance(score, bool) or not isinstance(score, (int, float)) or (
                isinstance(score, float) and not math.isfinite(score)
            ):
                errors.append(f"CRITERION_SCORE_INVALID:{cid}")
            else:
                aggregate["numeric_score_sum"] += float(score)

    aggregate["numeric_score_sum"] = round(aggregate["numeric_score_sum"], 12)
    if aggregate["criterion_count"] != EXPECTED_CRITERIA:
        errors.append("TOTAL_CRITERION_COUNT_MISMATCH")
    if index.get("aggregate") != aggregate:
        errors.append("AGGREGATE_RECOMPUTATION_MISMATCH")

    population_payload = {
        "source_revision": EXPECTED_REVISION,
        "task_contracts": tasks,
    }
    if index.get("population_contract_sha256") != _digest(population_payload):
        errors.append("POPULATION_CONTRACT_HASH_MISMATCH")

    for flag in (
        "whole_task_semantic_completeness_claim",
        "pairwise_human_preference_adequacy_claim",
        "target_model_equivalence_claim",
        "terminal_authority",
    ):
        if index.get(flag) is not False:
            errors.append("INDEX_UNSAFE_FLAG:" + flag)

    soundness = document.get("soundness")
    if not isinstance(soundness, Mapping):
        errors.append("SOUNDNESS_BLOCK_MISSING")
    else:
        for flag in (
            "whole_task_semantic_completeness_claim",
            "pairwise_human_preference_adequacy_claim",
            "target_model_equivalence_claim",
            "gdpval_scope_closed",
            "u_deletion_authority",
            "terminal_authority",
        ):
            if soundness.get(flag) is not False:
                errors.append("REPLAY_UNSAFE_FLAG:" + flag)

    inference = document.get("inference")
    if not isinstance(inference, Mapping):
        errors.append("INFERENCE_BLOCK_MISSING")
    elif inference.get("fresh_target_model_queries") != 0 or inference.get(
        "provider_evaluation_queries"
    ) != 0:
        errors.append("NONZERO_TARGET_OR_PROVIDER_QUERY_COUNT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__INDEPENDENT_HASH_AND_BOUNDARY_VERIFICATION"
            if not errors
            else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "verified_task_count": len(task_ids),
        "verified_criterion_count": aggregate["criterion_count"],
        "source_revision": EXPECTED_REVISION,
        "terminal_authority": False,
        "u_deletion_authority": False,
    }

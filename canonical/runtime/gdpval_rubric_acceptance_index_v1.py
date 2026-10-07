"""Content-addressed extraction of explicit GDPval rubric acceptance criteria.

This module intentionally does *not* infer task meaning. It converts the rubric_json
already shipped with a GDPval task row into a deterministic, source-preserving contract.

Soundness boundary:
- criterion text is preserved verbatim;
- supplied rubric_item_id values are preserved, otherwise a content hash is used;
- malformed rows/items fail closed;
- no rubric item is treated as a proof of whole-task semantic completeness,
  human-preference adequacy, target-model equivalence, or terminal capability.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_GDPVAL_RUBRIC_ACCEPTANCE_INDEX_V1"


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": list(errors),
        "terminal_authority": False,
    }


def _rubric_items(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"RUBRIC_JSON_INVALID:{exc.msg}") from exc
    if isinstance(value, Mapping):
        if isinstance(value.get("items"), list):
            value = value["items"]
        else:
            raise ValueError("RUBRIC_MAPPING_WITHOUT_ITEMS")
    if not isinstance(value, list):
        raise ValueError("RUBRIC_NOT_LIST")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValueError("RUBRIC_ITEM_NOT_MAPPING")
    return list(value)


def _score(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("RUBRIC_SCORE_NOT_NUMERIC")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("RUBRIC_SCORE_NOT_FINITE")
    return value


def _normalize_item(task_id: str, item: Mapping[str, Any]) -> dict[str, Any]:
    criterion = item.get("criterion")
    if not isinstance(criterion, str) or not criterion.strip():
        raise ValueError("RUBRIC_CRITERION_MISSING")

    tags = item.get("tags")
    if tags is None:
        tags_out: list[str] = []
    elif isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
        tags_out = list(tags)
    else:
        raise ValueError("RUBRIC_TAGS_INVALID")

    supplied_id = item.get("rubric_item_id")
    if supplied_id is not None and (not isinstance(supplied_id, str) or not supplied_id.strip()):
        raise ValueError("RUBRIC_ITEM_ID_INVALID")

    payload = {
        "task_id": task_id,
        "criterion": criterion,
        "score": _score(item.get("score")),
        "required": item.get("required"),
        "author_type": item.get("author_type"),
        "tags": tags_out,
        "read_only": item.get("read_only"),
        "form_content": item.get("form_content"),
    }
    criterion_hash = sha256(_canon(payload).encode("utf-8")).hexdigest()
    criterion_id = supplied_id.strip() if isinstance(supplied_id, str) else f"RUBRIC:{criterion_hash}"

    return {
        "criterion_id": criterion_id,
        "criterion_sha256": sha256(criterion.encode("utf-8")).hexdigest(),
        **payload,
    }


def build_rubric_acceptance_index(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_revision: str,
) -> dict[str, Any]:
    """Compile GDPval task rows into explicit, content-addressed acceptance contracts."""
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        return _fail("ROWS_NOT_SEQUENCE")
    if not isinstance(source_revision, str) or not source_revision.strip():
        return _fail("SOURCE_REVISION_MISSING")

    task_contracts: list[dict[str, Any]] = []
    seen_tasks: set[str] = set()
    seen_criteria: dict[str, str] = {}
    aggregate = {
        "task_count": 0,
        "criterion_count": 0,
        "human_authored_criterion_count": 0,
        "required_true_count": 0,
        "required_false_count": 0,
        "required_null_count": 0,
        "numeric_score_sum": 0.0,
        "criteria_without_numeric_score": 0,
    }

    try:
        for row_index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ValueError(f"ROW_NOT_MAPPING:{row_index}")
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise ValueError(f"TASK_ID_MISSING:{row_index}")
            task_id = task_id.strip()
            if task_id in seen_tasks:
                raise ValueError(f"DUPLICATE_TASK_ID:{task_id}")
            seen_tasks.add(task_id)

            items = [_normalize_item(task_id, item) for item in _rubric_items(row.get("rubric_json"))]
            for item in items:
                item_payload_hash = sha256(_canon(item).encode("utf-8")).hexdigest()
                prior = seen_criteria.get(item["criterion_id"])
                if prior is not None and prior != item_payload_hash:
                    raise ValueError(f"RUBRIC_ITEM_ID_COLLISION:{item['criterion_id']}")
                seen_criteria[item["criterion_id"]] = item_payload_hash

                aggregate["criterion_count"] += 1
                if item["author_type"] == "human":
                    aggregate["human_authored_criterion_count"] += 1
                if item["required"] is True:
                    aggregate["required_true_count"] += 1
                elif item["required"] is False:
                    aggregate["required_false_count"] += 1
                else:
                    aggregate["required_null_count"] += 1
                if item["score"] is None:
                    aggregate["criteria_without_numeric_score"] += 1
                else:
                    aggregate["numeric_score_sum"] += float(item["score"])

            contract_payload = {
                "task_id": task_id,
                "source_revision": source_revision,
                "criteria": items,
            }
            task_contracts.append({
                **contract_payload,
                "criterion_count": len(items),
                "contract_sha256": sha256(_canon(contract_payload).encode("utf-8")).hexdigest(),
            })

        aggregate["task_count"] = len(task_contracts)
        aggregate["numeric_score_sum"] = round(aggregate["numeric_score_sum"], 12)
        population_payload = {
            "source_revision": source_revision,
            "task_contracts": task_contracts,
        }
        return {
            "schema": SCHEMA,
            "status": "INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA",
            "source_revision": source_revision,
            "population_contract_sha256": sha256(_canon(population_payload).encode("utf-8")).hexdigest(),
            "aggregate": aggregate,
            "tasks": task_contracts,
            "one_sided_positive_localization_only": True,
            "whole_task_semantic_completeness_claim": False,
            "pairwise_human_preference_adequacy_claim": False,
            "target_model_equivalence_claim": False,
            "terminal_authority": False,
            "soundness_boundary": (
                "THIS_INDEX PRESERVES EXPLICIT RUBRIC ACCEPTANCE CRITERIA AS SOURCE-BOUND FACTS; "
                "UNSTATED TASK MEANING, HOLISTIC QUALITY, AND HUMAN PREFERENCE REMAIN UNKNOWN."
            ),
        }
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

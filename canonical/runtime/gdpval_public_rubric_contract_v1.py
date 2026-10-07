"""Fail-closed compiler for the public GDPval rubric contract surface.

Binds the exact public rubric_json attached to each GDPval task into
content-addressed source records. It does not infer criterion meaning, prove
policy adequacy, or equate the public rubric with the complete human
pairwise-preference evaluator.
"""
from __future__ import annotations
from hashlib import sha256
import json, math
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_GDPVAL_PUBLIC_RUBRIC_CONTRACT_V1"

def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha(x: str) -> str:
    return sha256(x.encode("utf-8")).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": reason,
            "terminal_authority": False, "policy_adequacy_authority": False, **extra}

def _rubric(raw: Any):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list) or not all(isinstance(x, Mapping) for x in raw):
        return None
    return list(raw)

def compile_task(*, row_idx: int, row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row_idx, int) or row_idx < 0:
        return _fail("INVALID_ROW_INDEX")
    if not isinstance(row, Mapping):
        return _fail("ROW_NOT_MAPPING")
    task_id = row.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        return _fail("TASK_ID_MISSING", row_idx=row_idx)
    rubric = _rubric(row.get("rubric_json"))
    if rubric is None:
        return _fail("RUBRIC_JSON_INVALID", row_idx=row_idx, task_id=task_id)

    records, local_ids = [], set()
    for item_index, item in enumerate(rubric):
        rid, criterion, score = item.get("rubric_item_id"), item.get("criterion"), item.get("score")
        if not isinstance(rid, str) or not rid.strip():
            return _fail("RUBRIC_ITEM_ID_MISSING", row_idx=row_idx, task_id=task_id, item_index=item_index)
        if rid in local_ids:
            return _fail("DUPLICATE_RUBRIC_ITEM_ID_IN_TASK", row_idx=row_idx, task_id=task_id, rubric_item_id=rid)
        local_ids.add(rid)
        if not isinstance(criterion, str) or not criterion.strip():
            return _fail("CRITERION_MISSING", row_idx=row_idx, task_id=task_id, rubric_item_id=rid)
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            return _fail("SCORE_INVALID", row_idx=row_idx, task_id=task_id, rubric_item_id=rid)
        source = [row_idx, task_id, item_index, rid, score, criterion, item.get("required"),
                  item.get("author_type"), item.get("tags"), item.get("read_only"), item.get("form_content")]
        records.append({
            "row_idx": row_idx, "task_id": task_id, "item_index": item_index,
            "rubric_item_id": rid, "score": score, "criterion": criterion,
            "criterion_sha256": _sha(criterion), "required": item.get("required"),
            "author_type": item.get("author_type"), "tags": item.get("tags"),
            "read_only": item.get("read_only"), "form_content": item.get("form_content"),
            "source_record_sha256": _sha(_canon(source)),
        })
    return {
        "schema": SCHEMA, "status": "COMPILED", "row_idx": row_idx, "task_id": task_id,
        "rubric_item_count": len(records), "rubric_score_total": sum(float(r["score"]) for r in records),
        "task_manifest_sha256": _sha("\n".join(r["source_record_sha256"] for r in records)),
        "records": records, "exact_public_evaluator_criteria_bound": True,
        "criterion_semantics_inferred": False, "pairwise_human_preference_law_complete": False,
        "policy_adequacy_authority": False, "terminal_authority": False,
    }

def compile_population(dataset_rows: Sequence[Mapping[str, Any]], *,
                       expected_task_count: int | None = None,
                       expected_item_count: int | None = None) -> dict[str, Any]:
    if not isinstance(dataset_rows, Sequence) or isinstance(dataset_rows, (str, bytes)):
        return _fail("POPULATION_NOT_SEQUENCE")
    if expected_task_count is not None and len(dataset_rows) != expected_task_count:
        return _fail("TASK_COUNT_MISMATCH", expected=expected_task_count, observed=len(dataset_rows))

    task_ids, rubric_ids, task_manifests = set(), set(), []
    item_count, score_total = 0, 0.0
    for expected_idx, container in enumerate(dataset_rows):
        if not isinstance(container, Mapping):
            return _fail("ROW_CONTAINER_NOT_MAPPING", expected_row_idx=expected_idx)
        row_idx, row = container.get("row_idx"), container.get("row")
        if row_idx != expected_idx:
            return _fail("ROW_INDICES_NOT_CONTIGUOUS", expected_row_idx=expected_idx, observed_row_idx=row_idx)
        task = compile_task(row_idx=row_idx, row=row)
        if task.get("status") != "COMPILED":
            return task
        if task["task_id"] in task_ids:
            return _fail("DUPLICATE_TASK_ID", task_id=task["task_id"])
        task_ids.add(task["task_id"])
        for record in task["records"]:
            rid = record["rubric_item_id"]
            if rid in rubric_ids:
                return _fail("DUPLICATE_RUBRIC_ITEM_ID_GLOBAL", rubric_item_id=rid)
            rubric_ids.add(rid)
        item_count += task["rubric_item_count"]
        score_total += task["rubric_score_total"]
        task_manifests.append(task["task_manifest_sha256"])

    if expected_item_count is not None and item_count != expected_item_count:
        return _fail("RUBRIC_ITEM_COUNT_MISMATCH", expected=expected_item_count, observed=item_count)
    return {
        "schema": SCHEMA, "status": "COMPILED", "task_count": len(dataset_rows),
        "unique_task_id_count": len(task_ids), "rubric_item_count": item_count,
        "unique_rubric_item_id_count": len(rubric_ids), "rubric_score_total": score_total,
        "population_manifest_sha256": _sha("\n".join(task_manifests)),
        "exact_public_evaluator_criteria_bound": True, "criterion_semantics_inferred": False,
        "pairwise_human_preference_law_complete": False, "policy_adequacy_authority": False,
        "terminal_authority": False,
        "soundness_boundary": "EXACT_PUBLIC_RUBRIC_RECORDS_ONLY__NO_CRITERION_SEMANTIC_INFERENCE__NO_POLICY_ADEQUACY__NO_HUMAN_PAIRWISE_LAW_COMPLETENESS",
    }

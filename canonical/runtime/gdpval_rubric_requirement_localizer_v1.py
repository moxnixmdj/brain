from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.bounded_imperative_directive_semantics_v2 import parse_directive

SCHEMA = "PROJECT_BRAIN_GDPVAL_RUBRIC_REQUIREMENT_LOCALIZER_V1"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "resolved_requirement_count": 0,
        "unresolved_criterion_count": 0,
        "whole_task_semantic_completeness_claim": False,
        "policy_adequacy_claim": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    out.update(extra)
    return out


def _criterion_id(task_id: str, item: Mapping[str, Any], index: int) -> str:
    cid = item.get("criterion_id")
    if isinstance(cid, str) and cid.strip():
        return cid.strip()
    text = item.get("criterion")
    if not isinstance(text, str):
        text = ""
    return "LOCAL:" + sha256(f"{task_id}\0{index}\0{text}".encode("utf-8")).hexdigest()


def localize(rubric_index: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(rubric_index, Mapping):
        return _fail("RUBRIC_INDEX_MAPPING_REQUIRED")
    if rubric_index.get("status") != "INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA":
        return _fail("RUBRIC_INDEX_NOT_ACCEPTED")
    tasks = rubric_index.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return _fail("RUBRIC_TASKS_REQUIRED")

    resolved = []
    unresolved = []
    task_summaries = []

    for task_pos, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            return _fail("TASK_NOT_MAPPING", task_position=task_pos)
        task_id = task.get("task_id")
        criteria = task.get("criteria")
        if not isinstance(task_id, str) or not task_id.strip():
            return _fail("TASK_ID_INVALID", task_position=task_pos)
        if not isinstance(criteria, list):
            return _fail("TASK_CRITERIA_INVALID", task_id=task_id)

        task_resolved = 0
        task_unresolved = 0
        for idx, item in enumerate(criteria):
            if not isinstance(item, Mapping):
                return _fail("CRITERION_NOT_MAPPING", task_id=task_id, criterion_index=idx)
            text = item.get("criterion")
            if not isinstance(text, str) or not text.strip():
                return _fail("CRITERION_TEXT_INVALID", task_id=task_id, criterion_index=idx)
            cid = _criterion_id(task_id, item, idx)

            modal = parse_clause(text)
            if modal.get("status") == "RESOLVED":
                resolved.append({
                    "task_id": task_id,
                    "criterion_id": cid,
                    "criterion_sha256": sha256(text.encode("utf-8")).hexdigest(),
                    "route": "BOUNDED_MODAL_PREDICATE_ARGUMENT",
                    "requirement": modal["semantic_graph"],
                    "condition": modal.get("condition"),
                    "source_text": text,
                })
                task_resolved += 1
                continue

            imperative = parse_directive(text)
            if imperative.get("status") == "RESOLVED_DIRECTIVE":
                resolved.append({
                    "task_id": task_id,
                    "criterion_id": cid,
                    "criterion_sha256": sha256(text.encode("utf-8")).hexdigest(),
                    "route": "BOUNDED_IMPERATIVE_DIRECTIVE",
                    "requirement": imperative["directive"],
                    "context": imperative.get("context"),
                    "source_text": text,
                })
                task_resolved += 1
                continue

            unresolved.append({
                "task_id": task_id,
                "criterion_id": cid,
                "criterion_sha256": sha256(text.encode("utf-8")).hexdigest(),
                "modal_status": modal.get("status"),
                "modal_reason": modal.get("reason"),
                "imperative_status": imperative.get("status"),
                "imperative_reason": imperative.get("reason"),
            })
            task_unresolved += 1

        task_summaries.append({
            "task_id": task_id,
            "criterion_count": len(criteria),
            "resolved_requirement_count": task_resolved,
            "unresolved_criterion_count": task_unresolved,
        })

    return {
        "schema": SCHEMA,
        "status": "LOCALIZED_EXPLICIT_RUBRIC_REQUIREMENTS",
        "pass": True,
        "task_count": len(tasks),
        "criterion_count": len(resolved) + len(unresolved),
        "resolved_requirement_count": len(resolved),
        "unresolved_criterion_count": len(unresolved),
        "resolved_requirements": resolved,
        "unresolved_criteria": unresolved,
        "tasks": task_summaries,
        "whole_task_semantic_completeness_claim": False,
        "policy_adequacy_claim": False,
        "unresolved_criterion_is_irrelevant": False,
        "next_rule": "ROUTE_ONLY_RESOLVED_SOURCE_BOUND_REQUIREMENTS_TO_EXISTING_BRAIN_CAPABILITY_OR_TOP_LAW_MATCHING;KEEP_UNRESOLVED_CRITERIA_OPEN",
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

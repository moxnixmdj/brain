"""Revision-gated replay of the complete public GDPval rubric acceptance index.

This is a structural localization replay, not target-model evaluation. It refuses to
consume rows unless the public dataset metadata still names the exact revision already
bound by the canonical GDPval population receipt.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
from typing import Any
from urllib.request import Request, urlopen

from canonical.runtime.gdpval_rubric_acceptance_index_v1 import (
    build_rubric_acceptance_index,
)
from canonical.runtime.gdpval_semantic_complement_localizer_v2 import load_public_rows

SCHEMA = "PROJECT_BRAIN_GDPVAL_RUBRIC_ACCEPTANCE_REPLAY_V1"
DATASET_API = "https://huggingface.co/api/datasets/openai/gdpval"
EXPECTED_REVISION = "11e7900cdcac61bc4daf59e65feb238acda98fbf"
EXPECTED_TASKS = 220
EXPECTED_CRITERIA = 10453


def _fetch_dataset_metadata() -> dict[str, Any]:
    req = Request(
        DATASET_API,
        headers={"User-Agent": "project-brain-gdpval-rubric-replay-v1/1.0"},
    )
    with urlopen(req, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("DATASET_METADATA_NOT_OBJECT")
    return payload


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        **detail,
        "inference": {
            "fresh_target_model_queries": 0,
            "provider_evaluation_queries": 0,
        },
        "terminal_authority": False,
        "u_deletion_authority": False,
    }


def execute(
    *,
    metadata_fetcher: Callable[[], Mapping[str, Any]] = _fetch_dataset_metadata,
    rows_loader: Callable[[], Sequence[Mapping[str, Any]]] = load_public_rows,
) -> dict[str, Any]:
    try:
        metadata = metadata_fetcher()
        if not isinstance(metadata, Mapping):
            return _fail("DATASET_METADATA_NOT_OBJECT")
        observed_revision = metadata.get("sha")
        if observed_revision != EXPECTED_REVISION:
            return _fail(
                "DATASET_REVISION_DRIFT",
                expected_revision=EXPECTED_REVISION,
                observed_revision=observed_revision,
            )

        wrapped_rows = rows_loader()
        if not isinstance(wrapped_rows, Sequence) or isinstance(
            wrapped_rows, (str, bytes, bytearray)
        ):
            return _fail("ROWS_LOADER_NOT_SEQUENCE")

        rows: list[dict[str, Any]] = []
        for expected_index, wrapped in enumerate(wrapped_rows):
            if not isinstance(wrapped, Mapping):
                return _fail("WRAPPED_ROW_NOT_OBJECT", row_index=expected_index)
            if wrapped.get("row_idx") != expected_index:
                return _fail(
                    "ROW_INDEX_DRIFT",
                    expected_row_index=expected_index,
                    observed_row_index=wrapped.get("row_idx"),
                )
            raw = wrapped.get("row")
            if not isinstance(raw, Mapping):
                return _fail("RAW_ROW_NOT_OBJECT", row_index=expected_index)
            rows.append(dict(raw))

        if len(rows) != EXPECTED_TASKS:
            return _fail(
                "TASK_COUNT_DRIFT",
                expected_task_count=EXPECTED_TASKS,
                observed_task_count=len(rows),
            )

        index = build_rubric_acceptance_index(
            rows,
            source_revision=EXPECTED_REVISION,
        )
        if index.get("status") != "INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA":
            return _fail(
                "RUBRIC_INDEX_FAILED",
                index_status=index.get("status"),
                index_errors=index.get("errors"),
            )

        aggregate = index.get("aggregate")
        if not isinstance(aggregate, Mapping):
            return _fail("RUBRIC_INDEX_AGGREGATE_MISSING")
        if aggregate.get("task_count") != EXPECTED_TASKS:
            return _fail(
                "INDEX_TASK_COUNT_DRIFT",
                observed_task_count=aggregate.get("task_count"),
            )
        if aggregate.get("criterion_count") != EXPECTED_CRITERIA:
            return _fail(
                "CRITERION_COUNT_DRIFT",
                expected_criterion_count=EXPECTED_CRITERIA,
                observed_criterion_count=aggregate.get("criterion_count"),
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_BOUND_PUBLIC_220_RUBRIC_ACCEPTANCE_INDEX",
            "pass": True,
            "dataset": {
                "owner": "openai",
                "name": "gdpval",
                "expected_revision": EXPECTED_REVISION,
                "observed_revision": observed_revision,
                "revision_match": True,
            },
            "expected_task_count": EXPECTED_TASKS,
            "expected_criterion_count": EXPECTED_CRITERIA,
            "index": index,
            "inference": {
                "fresh_target_model_queries": 0,
                "provider_evaluation_queries": 0,
            },
            "soundness": {
                "explicit_rubric_localization_only": True,
                "whole_task_semantic_completeness_claim": False,
                "pairwise_human_preference_adequacy_claim": False,
                "target_model_equivalence_claim": False,
                "gdpval_scope_closed": False,
                "u_deletion_authority": False,
                "terminal_authority": False,
            },
            "terminal_authority": False,
            "u_deletion_authority": False,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2, sort_keys=True, ensure_ascii=False))

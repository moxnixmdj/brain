"""Replay the source-bound shared-modal AND bridge over public GDPval 220.

Diagnostic only. It measures exact source-bound structural yield and grants no
semantic-completeness, policy-adequacy, GDPval, or terminal credit.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import re
from typing import Any, Iterable
from urllib.request import Request, urlopen

from canonical.runtime.source_bound_shared_modal_and_v1 import bind_shared_modal_and

SCHEMA = "PROJECT_BRAIN_GDPVAL_SHARED_MODAL_AND_PUBLIC_REPLAY_V1"
ROWS_API = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=openai%2Fgdpval&config=default&split=train"
)
EXPECTED_TASKS = 220
_SEGMENT_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|\n|$)")
_MODAL_RE = re.compile(r"\b(?:must|shall|should|required to|is required to)\b", re.I)


def _segments(text: str) -> Iterable[str]:
    for m in _SEGMENT_RE.finditer(text):
        s = m.group(0).strip()
        if s:
            yield s


def _fetch_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "project-brain-gdpval-shared-modal-replay/1.0"})
    with urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def load_public_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset, length in ((0, 100), (100, 100), (200, 20)):
        page = _fetch_json(f"{ROWS_API}&offset={offset}&length={length}").get("rows")
        if not isinstance(page, list):
            raise RuntimeError("ROWS_PAGE_MISSING")
        rows.extend(page)
    if len(rows) != EXPECTED_TASKS:
        raise RuntimeError("TASK_COUNT_MISMATCH")
    if [int(x.get("row_idx")) for x in rows] != list(range(EXPECTED_TASKS)):
        raise RuntimeError("ROW_INDEX_MISMATCH")
    ids = [str((x.get("row") or {}).get("task_id") or "") for x in rows]
    if any(not x for x in ids) or len(set(ids)) != EXPECTED_TASKS:
        raise RuntimeError("TASK_ID_POPULATION_INVALID")
    return rows


def replay_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != EXPECTED_TASKS:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["TASK_COUNT_MISMATCH"],
            "terminal_authority": False,
        }

    failure_reasons: Counter[str] = Counter()
    task_rows = []
    total_modal = 0
    total_bound = 0
    total_obligations = 0
    population_lines = []

    for item in rows:
        idx = int(item.get("row_idx"))
        row = dict(item.get("row") or {})
        task_id = str(row.get("task_id") or "")
        prompt = str(row.get("prompt") or "")
        if not task_id or not prompt:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["TASK_ID_OR_PROMPT_MISSING"],
                "terminal_authority": False,
            }
        population_lines.append(
            f"{idx}:{task_id}:{sha256(prompt.encode('utf-8')).hexdigest()}"
        )
        modal = 0
        bound = 0
        obligations = 0
        for segment in _segments(prompt):
            if not _MODAL_RE.search(segment):
                continue
            modal += 1
            out = bind_shared_modal_and(segment)
            if out.get("status") == "BOUND_SHARED_MODAL_AND":
                bound += 1
                obligations += int(out.get("obligation_count") or 0)
            else:
                failure_reasons[str(out.get("reason") or "UNKNOWN")] += 1
        total_modal += modal
        total_bound += bound
        total_obligations += obligations
        task_rows.append(
            {
                "row_idx": idx,
                "task_id": task_id,
                "modal_segment_count": modal,
                "source_bound_shared_modal_and_count": bound,
                "derived_source_bound_obligation_count": obligations,
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__PUBLIC_220_EXACT_SOURCE_BOUND_SHARED_MODAL_AND_REPLAY__ZERO_CREDIT",
        "population": {
            "task_count": EXPECTED_TASKS,
            "population_manifest_sha256": sha256(
                "\n".join(population_lines).encode("utf-8")
            ).hexdigest(),
        },
        "aggregate": {
            "modal_segment_count": total_modal,
            "source_bound_shared_modal_and_count": total_bound,
            "derived_source_bound_obligation_count": total_obligations,
            "tasks_with_source_bound_shared_modal_and": sum(
                1 for x in task_rows
                if x["source_bound_shared_modal_and_count"] > 0
            ),
            "failure_reasons": dict(sorted(failure_reasons.items())),
        },
        "tasks": task_rows,
        "soundness": {
            "source_span_binding_complete_for_bound_rows": True,
            "semantic_completeness_claim": False,
            "policy_adequacy_proved": False,
            "gdpval_scope_closed": False,
            "u_deletion_authority": False,
            "terminal_authority": False,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "fresh_target_model_queries": 0,
            "terminal_credit_delta": 0,
        },
    }


def main() -> None:
    print(json.dumps(replay_rows(load_public_rows()), sort_keys=True))


if __name__ == "__main__":
    main()

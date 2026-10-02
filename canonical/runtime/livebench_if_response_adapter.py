"""Fail-closed Brain response adapter for the frozen LiveBench IF evaluator shape.

No benchmark questions are read here. The adapter only converts already-produced Brain
responses into the exact model_answers structure consumed by LiveBench at the pinned
upstream commit.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence


def adapt_responses(records: Sequence[Mapping[str, Any]], *, model_id: str = "brain") -> dict:
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_id must be nonempty")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise TypeError("records must be a sequence")

    out: dict[Any, dict] = {}
    for i, row in enumerate(records):
        if not isinstance(row, Mapping):
            raise TypeError(f"record[{i}] must be an object")
        if "question_id" not in row or "response" not in row:
            raise ValueError(f"record[{i}] requires question_id and response")
        qid = row["question_id"]
        response = row["response"]
        if isinstance(qid, bool) or not isinstance(qid, (int, str)):
            raise TypeError(f"record[{i}] question_id must be int or str")
        if isinstance(qid, str) and not qid.strip():
            raise ValueError(f"record[{i}] question_id empty")
        if not isinstance(response, str):
            raise TypeError(f"record[{i}] response must be str")
        if qid in out:
            raise ValueError(f"duplicate question_id: {qid!r}")
        out[qid] = {
            "question_id": qid,
            "choices": [{"turns": [response]}],
        }
    return {model_id: out}


def validate_against_questions(model_answers: Mapping[str, Any], questions: Sequence[Mapping[str, Any]], *, model_id: str = "brain") -> dict:
    """Preflight IDs only. It intentionally does not inspect prompt/task content."""
    if model_id not in model_answers or not isinstance(model_answers[model_id], Mapping):
        return {"status": "FAIL_CLOSED", "reason": "MODEL_ID_MISSING"}
    answer_ids=set(model_answers[model_id])
    question_ids=[]
    for i,q in enumerate(questions):
        if not isinstance(q, Mapping) or "question_id" not in q:
            return {"status":"FAIL_CLOSED","reason":f"QUESTION_ID_MISSING:{i}"}
        question_ids.append(q["question_id"])
    if len(question_ids)!=len(set(question_ids)):
        return {"status":"FAIL_CLOSED","reason":"QUESTION_IDS_DUPLICATE"}
    expected=set(question_ids)
    if answer_ids!=expected:
        return {
            "status":"FAIL_CLOSED",
            "reason":"QUESTION_RESPONSE_ID_SET_MISMATCH",
            "missing":sorted(expected-answer_ids,key=str),
            "extra":sorted(answer_ids-expected,key=str),
        }
    return {"status":"PASS","count":len(expected),"content_inspected":False}

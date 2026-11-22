#!/usr/bin/env python3
"""One purpose gate: a question is legal only when a real run separates answers.

The OSWorld intake compiles an authorized answer into a guest assertion. This
module supplies the missing half: before asking, it tests the candidate
statements against real runs from an environment that was not used to fit them.
A typed authorized answer can then select one compiled statement; free prose,
untrusted authors, stale digests and invented candidate ids are refused.

Nothing here parses English, ranks statements, or calls a model. Knowledge is
an external JSON file, keyed by the instruction digest and the question's
content address; deleting the file is the whole unlearning operation.

Authority: NONE. Producer-run sandbox. Zero parameters.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping, Sequence

from intake import authorized_answer_intake_v1 as answers
from intake import residual_question_gate_v1 as gate

SCHEMA = "BRAIN_PURPOSE_GATE_V1"
ANSWER_KIND = "RESIDUAL_STATEMENT_CHOICE"

ASK = "ASK_USER"
ASK_USER = ASK
NO_QUESTION = gate.NO_QUESTION
ACCEPTED = "ANSWER_ACCEPTED"


def question_fingerprint(decision: Mapping[str, Any]) -> str:
    material = json.dumps({
        "candidate_texts": decision.get("candidate_texts") or [],
        "traces": decision.get("traces"),
        "questions": decision.get("questions"),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def decide(state: Mapping[str, Any], candidates: Sequence[gate.Candidate],
           traces: Sequence[gate.Trace], *, goal_judge: gate.Predicate | None = None
           ) -> dict[str, Any]:
    """Ask only on a real contrast; accept only a typed, authorized selection."""
    decision = gate.decide(candidates, traces, goal_judge=goal_judge)
    fingerprint = question_fingerprint(decision)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "gate": decision,
        "question_fingerprint": fingerprint,
        "instruction_sha256": answers.instruction_sha256(str(state.get("instruction") or "")),
        "external_model_dependency": False,
        "parameters_stored": 0,
    }
    if decision["action"] != gate.ASK_USER:
        receipt["action"] = NO_QUESTION
        receipt["reason"] = decision["reason"]
        return receipt

    receipt["action"] = ASK
    receipt["payload"] = gate.ask_payload(decision)
    raw = state.get("purpose_answer")
    if raw is None:
        receipt["reason"] = "NO_AUTHORIZED_ANSWER"
        return receipt
    if not isinstance(raw, Mapping):
        receipt["reason"] = "ANSWER_NOT_OBJECT"
        return receipt

    allowed = set(state.get("authorized_users") or ())
    if not allowed or str(raw.get("author") or "") not in allowed:
        receipt["reason"] = "ANSWER_AUTHOR_NOT_AUTHORIZED"
        return receipt
    if str(raw.get("instruction_sha256") or "") != receipt["instruction_sha256"]:
        receipt["reason"] = "ANSWER_INSTRUCTION_DIGEST_STALE"
        return receipt
    if str(raw.get("kind") or "") != ANSWER_KIND:
        receipt["reason"] = "ANSWER_KIND_UNSUPPORTED"
        return receipt
    if str(raw.get("question_fingerprint") or "") != fingerprint:
        receipt["reason"] = "ANSWER_QUESTION_STALE"
        return receipt
    options = {option["candidate_id"] for option in receipt["payload"]["options"]}
    chosen = str(raw.get("candidate_id") or "")
    if chosen not in options:
        receipt["reason"] = "CANDIDATE_NOT_IN_COMPUTED_RESIDUAL"
        return receipt

    receipt["action"] = ACCEPTED
    receipt["chosen_candidate_id"] = chosen
    receipt["chosen_text"] = next(
        option["text"] for option in receipt["payload"]["options"]
        if option["candidate_id"] == chosen)
    return receipt


def persist(state: Mapping[str, Any], decision: Mapping[str, Any], path: pathlib.Path
            ) -> dict[str, Any]:
    """Write only a typed selection, keyed by instruction and question digests."""
    if decision.get("action") != ACCEPTED:
        raise ValueError("only an accepted typed answer may be persisted")
    raw = state["purpose_answer"]
    record = {
        "schema": SCHEMA,
        "author": str(raw["author"]),
        "instruction_sha256": str(raw["instruction_sha256"]),
        "question_fingerprint": str(raw["question_fingerprint"]),
        "kind": ANSWER_KIND,
        "candidate_id": str(raw["candidate_id"]),
        "text": decision["chosen_text"],
    }
    rows = load(path)
    key = (record["instruction_sha256"], record["question_fingerprint"])
    rows = [row for row in rows
            if (row.get("instruction_sha256"), row.get("question_fingerprint")) != key]
    rows.append(record)
    rows.sort(key=lambda row: (row["instruction_sha256"], row["question_fingerprint"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return {"schema": SCHEMA, "written": 1, "path": str(path)}


def load(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("PURPOSE_STORE_NOT_A_LIST_OF_OBJECTS")
    return [dict(row) for row in rows]


def stored_answer(path: pathlib.Path, fingerprint: str) -> dict[str, Any] | None:
    return next((row for row in load(path)
                 if str(row.get("question_fingerprint")) == fingerprint), None)


def as_state_answer(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reload a stored selection into the exact typed shape `decide` accepts."""
    return {
        "author": record.get("author"),
        "instruction_sha256": record.get("instruction_sha256"),
        "question_fingerprint": record.get("question_fingerprint"),
        "kind": ANSWER_KIND,
        "candidate_id": record.get("candidate_id"),
    }

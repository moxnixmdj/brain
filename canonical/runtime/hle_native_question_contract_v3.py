#!/usr/bin/env python3
"""Brain-native HLE question contract V3.

V3 hardens answer-slot classification against common predicate-first wh forms,
interrogative punctuation noise, and embedded clue clauses. It emits the same
answer-key-blind multi-query views as V2 plus a deterministic answer subtype.
No retrieval, model call, gold access, or answer authority occurs here.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from canonical.runtime import hle_native_question_contract_v2 as v2

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_QUESTION_CONTRACT_V3"

def _sha(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def _clean_scope(question: str) -> str:
    q = " ".join(str(question or "").strip().split())
    # Trivia/public QA occasionally contains punctuation immediately after the
    # interrogative ("Which. Australian city ..."). Treat it as transcription
    # noise for slot parsing, not as a sentence boundary.
    q = re.sub(r"^(Who|What|Which|Where|When|How)[.!,:;]+\s+", r"\1 ", q, flags=re.I)
    return q

def classify_answer_slot(question: str) -> dict[str, Any]:
    q = _clean_scope(question)
    low = q.casefold()
    kind = None
    subtype = None

    if re.search(r"\bwhat\s+relation\b|\bhow\s+(?:was|is|were|are)\b.{0,80}\brelated\b", low):
        kind, subtype = "RELATION_TERM", "KINSHIP_OR_RELATION"
    elif re.match(r"^\s*who\b", q, re.I) or re.search(
        r"\bwhich\b(?:\s+[\w'-]+){0,6}\s+"
        r"(?:composer|author|artist|mountaineer|president|scientist|inventor|discoverer|"
        r"explorer|actor|actress|writer|poet|daughter|son|brother|sister|person)\b", q, re.I
    ) or re.match(r"^\s*what\s+author\b", q, re.I):
        kind, subtype = "PERSON", "PERSON"
    elif re.match(r"^\s*where\b", q, re.I):
        kind, subtype = "LOCATION", "LOCATION"
    elif re.search(r"\bwhat\s+is\s+the\s+capital\b|\bcapital\s+of\b", low):
        kind, subtype = "LOCATION", "CAPITAL"
    elif re.search(r"\bcountry\s+of\s+origin\b|\bwhich\s+country\b", low):
        kind, subtype = "LOCATION", "COUNTRY"
    elif re.search(r"\bwhich\b(?:\s+[\w'-]+){0,6}\s+city\b", q, re.I):
        kind, subtype = "LOCATION", "CITY"
    elif re.search(r"\bwhich\b(?:\s+[\w'-]+){0,6}\s+region\b", q, re.I):
        kind, subtype = "LOCATION", "REGION"
    elif re.search(r"\bwhich\b(?:\s+[\w'-]+){0,6}\s+(?:university|college)\b", q, re.I):
        kind, subtype = "LOCATION", "UNIVERSITY"
    elif re.search(r"\b(?:what|which)\s+year\b|\bin\s+(?:what|which)\s+year\b", low):
        kind, subtype = "YEAR", "YEAR"
    elif re.search(r"\bhow\s+(?:many|much)\b", low):
        kind, subtype = "NUMBER", "NUMBER"
    elif (
        re.search(r"\bwhich\s+of\b.{0,80}\b(?:plays?|films?|movies?|operas?|books?|novels?|songs?|albums?|games?)\b", q, re.I)
        or re.search(r"\b(?:in|from)\s+which\b.{0,80}\b(?:film|movie|play|opera|book|novel|song|album|game)\b", q, re.I)
        or re.match(r"^\s*which\b(?:\s+[\w'-]+){0,7}\s+(?:film|movie|play|opera|book|novel|song|album|game)\b", q, re.I)
    ):
        kind, subtype = "WORK_TITLE", "WORK_TITLE"
    elif (
        re.search(r"\bwhat\s+name\b|\bname\s+(?:is\s+)?given\b|\balso\s+known\s+as\b", low)
        or re.search(r"\bwhat\b.{0,100}\bcalled\b", low)
        or re.search(r"\bwhat\s+does\b.{0,100}\b(?:equal|mean)\b", low)
    ):
        kind, subtype = "TERM", "TERM"
    elif re.search(r"\bwhich\b(?:\s+[\w'-]+){0,6}\s+(?:dynasty|family|cocktail|bone|compound|material|species|gene|protein|enzyme)\b", q, re.I):
        kind, subtype = "ENTITY_OR_TERM", "ENTITY_OR_TERM"
    elif re.search(r"\bcollection\s+of\s+games\b", low):
        kind, subtype = "WORK_TITLE", "GAME_COLLECTION"

    if kind is None:
        old = v2.classify_answer_slot(q)
        kind = str(old.get("kind") or "OPEN_TEXT")
        subtype = kind

    return {
        "kind": kind,
        "subtype": subtype,
        "normalized_scope": q,
        "normalized_scope_sha256": _sha(q),
    }

def compile_question(*, task_id: str, question: str, has_nonempty_image_payload: bool = False) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise ValueError("IMAGE_FLAG_INVALID")

    # Preserve V1/V2's verified MCQ semantics exactly.
    if v2.v1._MC_MARKER.search(question):
        old = dict(v2.compile_question(
            task_id=task_id, question=question,
            has_nonempty_image_payload=has_nonempty_image_payload
        ))
        old["schema"] = SCHEMA
        old["contract_version"] = "V3_REUSES_VERIFIED_MCQ_V2"
        return old

    slot = classify_answer_slot(question)
    normalized = slot["normalized_scope"]
    views = v2.compile_research_views(normalized, slot["kind"])
    return {
        "schema": SCHEMA,
        "status": "COMPILED__ROBUST_ANSWER_SLOT_AND_MULTI_QUERY_VIEWS",
        "pass": True,
        "task_id": task_id.strip(),
        "question_sha256": _sha(question),
        "normalized_scope_sha256": slot["normalized_scope_sha256"],
        "question_kind": slot["kind"],
        "answer_subtype": slot["subtype"],
        "answer_contract": {
            "kind": slot["kind"],
            "subtype": slot["subtype"],
            "format_authority": False,
        },
        "research_views": views,
        "research_view_count": len(views),
        "has_nonempty_image_payload": has_nonempty_image_payload,
        "gold_accessed": False,
        "answer_type_metadata_consumed": False,
        "external_model_calls": 0,
        "external_reasoning_model_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "candidate_answer_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_rules": [
            "ANSWER_SLOT_IS_DERIVED_ONLY_FROM_VISIBLE_QUESTION_SURFACE",
            "PUNCTUATION_NOISE_NORMALIZATION_DOES_NOT_CHANGE_SEMANTIC_CONTENT",
            "FULL_QUESTION_VERBATIM_SEARCH_IS_FORBIDDEN",
            "RESEARCH_VIEW_COMPILATION_HAS_ZERO_ANSWER_AUTHORITY",
        ],
    }

if __name__ == "__main__":
    cases = [
        ("What is the capital of the Dominican Republic?", "LOCATION"),
        ("Which. Australian city is named after the Scotsman who was Governor?", "LOCATION"),
        ("Which composer wrote the operas 'A' and 'B'?", "PERSON"),
        ("Which of Shakespeare's plays is set in Vienna?", "WORK_TITLE"),
        ("Business magnate X dropped out which US university?", "LOCATION"),
        ("What relation was X to Y?", "RELATION_TERM"),
    ]
    for i,(q,k) in enumerate(cases):
        x=compile_question(task_id=str(i),question=q)
        assert x["question_kind"]==k,(q,x)
    print("SELF_TEST_PASS")

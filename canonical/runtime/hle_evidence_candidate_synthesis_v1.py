#!/usr/bin/env python3
"""Brain-native typed evidence -> candidate synthesis V1.

This is a bounded relation extractor, not a general semantic judge.
Candidates have zero correctness authority until downstream verification.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_HLE_EVIDENCE_CANDIDATE_SYNTHESIS_V1"

_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_NUM = re.compile(r"(?<![A-Za-z0-9])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:e[-+]?\d+)?%?(?![A-Za-z0-9])", re.I)
_YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2}|21[0-9]{2})(?!\d)")
_TITLE_NAME = re.compile(
    r"(?:(?:Dr|Prof|Professor|Sir|Dame)\.\s+)?"
    r"[A-Z][\w'’.-]+(?:\s+(?:[A-Z][\w'’.-]+|[A-Z]\.)){1,5}"
)
_CAP_PHRASE = re.compile(
    r"\b[A-Z][\w'’.-]*(?:\s+(?:[A-Z][\w'’.-]+|[a-z][\w'’.-]*)){0,7}"
)
_NEG = re.compile(r"\b(?:not|never|no|invalid|false|incorrect)\b", re.I)


class EvidenceCandidateError(ValueError):
    pass


def _canon(v: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(v or "")).strip().split())


def _sha(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def _tokens(v: str) -> list[str]:
    out = []
    for x in _WORD.findall(_canon(v)):
        t = x.casefold().strip("-/")
        if len(t) >= 2 and t not in out:
            out.append(t)
    return out


def _anchor_coverage(focus: Sequence[str], evidence: str) -> tuple[list[str], float]:
    if not isinstance(focus, Sequence) or isinstance(focus, (str, bytes)):
        raise EvidenceCandidateError("FOCUS_MUST_BE_SEQUENCE")
    normalized = []
    for raw in focus:
        t = _canon(raw).casefold()
        if t and t not in normalized:
            normalized.append(t)
    if not normalized:
        raise EvidenceCandidateError("FOCUS_EMPTY")
    low = _canon(evidence).casefold()
    matched = [t for t in normalized if t in low]
    return matched, len(matched) / len(normalized)


def _clean_phrase(value: str) -> str | None:
    x = _canon(value).strip(" ,;:.()[]{}")
    x = re.split(
        r"\b(?:because|although|while|whereas|after|before|during|near|when|which|that|who)\b",
        x,
        maxsplit=1,
        flags=re.I,
    )[0].strip(" ,;:.")
    if not x or len(x) > 160 or len(x.split()) > 16:
        return None
    return x


def _relation_capture(patterns: Sequence[re.Pattern[str]], evidence: str) -> list[str]:
    out = []
    for p in patterns:
        for m in p.finditer(evidence):
            x = _clean_phrase(m.group(1))
            if x and x not in out:
                out.append(x)
    return out


_PERSON_PATTERNS = (
    re.compile(r"\b(?:discovered|invented|developed|introduced|proposed|founded|identified)\s+by\s+(.+?)(?=[.;]|$)", re.I),
    re.compile(r"\b(?:discoverer|inventor|developer|founder|author)\s+(?:was|is)\s+(.+?)(?=[.;]|$)", re.I),
)
_LOCATION_PATTERNS = (
    re.compile(r"\b(?:is|was|are|were)\s+located\s+in\s+(.+?)(?=[.;]|$)", re.I),
    re.compile(r"\b(?:is|was|are|were)\s+situated\s+in\s+(.+?)(?=[.;]|$)", re.I),
    re.compile(r"\b(?:is|was|are|were)\s+based\s+in\s+(.+?)(?=[.;]|$)", re.I),
)
_TERM_PATTERNS = (
    re.compile(r"\b(?:is|was|are|were)\s+(?:called|named|termed|designated|known\s+as)\s+(?:the\s+)?(.+?)(?=[.;]|$)", re.I),
    re.compile(r"\b(?:called|named|termed|designated)\s+(?:the\s+)?(.+?)(?=[.;]|$)", re.I),
)


def _extract_person(evidence: str) -> list[str]:
    out = []
    for raw in _relation_capture(_PERSON_PATTERNS, evidence):
        # Keep a relation-bound name, not arbitrary capitals elsewhere.
        names = _TITLE_NAME.findall(raw)
        if len(names) == 1:
            out.append(names[0])
        elif not names:
            clean = _clean_phrase(raw)
            if clean and 1 <= len(clean.split()) <= 6:
                out.append(clean)
    return list(dict.fromkeys(out))


def _extract_location(evidence: str) -> list[str]:
    out = []
    for raw in _relation_capture(_LOCATION_PATTERNS, evidence):
        # Stop at adjunct prepositions that typically start context, not the location name.
        x = re.split(r"\b(?:near|beside|within|during|after|before)\b", raw, maxsplit=1, flags=re.I)[0]
        x = _clean_phrase(x)
        if x:
            out.append(x)
    return list(dict.fromkeys(out))


def _extract_term(evidence: str) -> list[str]:
    return list(dict.fromkeys(_relation_capture(_TERM_PATTERNS, evidence)))


def _extract_number(evidence: str, *, year_only: bool) -> list[str]:
    vals = _YEAR.findall(evidence) if year_only else _NUM.findall(evidence)
    out = []
    for x in vals:
        x = str(x).replace(",", "")
        if x not in out:
            out.append(x)
    return out


def _extract_boolean(evidence: str, focus: Sequence[str]) -> list[str]:
    # Require an explicit validity/truth/existence relation near a focus-bearing sentence.
    rows = [x.strip() for x in re.split(r"(?<=[.!?;])\s+", _canon(evidence)) if x.strip()]
    focus_low = [str(x).casefold() for x in focus]
    decisions = []
    for row in rows:
        low = row.casefold()
        if sum(1 for t in focus_low if t and t in low) < max(1, min(2, len(focus_low))):
            continue
        if re.search(r"\b(?:valid|true|holds?|exists?|present|applicable|satisfied)\b", row, re.I):
            decisions.append("No" if _NEG.search(row) else "Yes")
        elif re.search(r"\b(?:invalid|false|absent|inapplicable|violated)\b", row, re.I):
            decisions.append("No")
    uniq = list(dict.fromkeys(decisions))
    return uniq if len(uniq) == 1 else []


def _extract_explanation(evidence: str) -> list[str]:
    out = []
    for m in re.finditer(r"\b(because\s+.+?)(?=[.;]|$)", evidence, re.I):
        x = _clean_phrase(m.group(1))
        if x and x.casefold().startswith("because "):
            out.append(x)
    return list(dict.fromkeys(out))


def synthesize(
    *,
    contract: Mapping[str, Any],
    focus_terms: Sequence[str],
    evidence: str,
) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        raise EvidenceCandidateError("CONTRACT_REQUIRED")
    kind = str(contract.get("kind") or "").upper()
    polarity = str(contract.get("polarity") or "POSITIVE").upper()
    if polarity not in {"POSITIVE", "NEGATIVE"}:
        raise EvidenceCandidateError("POLARITY_INVALID")
    if not isinstance(evidence, str) or not evidence.strip():
        raise EvidenceCandidateError("EVIDENCE_REQUIRED")

    matched, coverage = _anchor_coverage(focus_terms, evidence)
    base = {
        "schema": SCHEMA,
        "kind": kind,
        "polarity": polarity,
        "evidence_sha256": _sha(evidence),
        "matched_focus_terms": matched,
        "focus_coverage": coverage,
        "candidate_answer_authority": False,
        "semantic_truth_authority": False,
        "gold_accessed": False,
        "external_model_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    min_matches = 1 if len(list(focus_terms)) <= 1 else 2
    if len(matched) < min_matches:
        return {
            **base,
            "status": "NO_CANDIDATE__INSUFFICIENT_OBJECTIVE_ANCHOR_COVERAGE",
            "candidates": [],
        }

    if kind == "PERSON":
        candidates = _extract_person(evidence)
        relation = "EXPLICIT_AGENT_RELATION"
    elif kind == "YEAR":
        candidates = _extract_number(evidence, year_only=True)
        relation = "EXPLICIT_YEAR_LITERAL"
    elif kind in {"NUMBER", "NUMBER_OR_EXPRESSION", "SYMBOLIC_OR_NUMBER"}:
        candidates = _extract_number(evidence, year_only=False)
        relation = "EXPLICIT_NUMERIC_LITERAL"
    elif kind == "LOCATION":
        candidates = _extract_location(evidence)
        relation = "EXPLICIT_LOCATION_RELATION"
    elif kind in {"ENTITY_OR_TERM", "SYMBOLIC_EXPRESSION"}:
        candidates = _extract_term(evidence)
        relation = "EXPLICIT_NAMING_RELATION"
    elif kind == "BOOLEAN":
        candidates = _extract_boolean(evidence, focus_terms)
        relation = "EXPLICIT_BOOLEAN_RELATION"
    elif kind == "EXPLANATION":
        candidates = _extract_explanation(evidence)
        relation = "EXPLICIT_CAUSAL_CONNECTIVE"
    else:
        return {
            **base,
            "status": "NO_CANDIDATE__ANSWER_KIND_NOT_IN_V1",
            "candidates": [],
        }

    candidates = list(dict.fromkeys(x for x in candidates if x))
    if len(candidates) != 1:
        return {
            **base,
            "status": "NO_CANDIDATE__RELATION_ABSENT_OR_AMBIGUOUS",
            "relation_class": relation,
            "candidates": [],
            "raw_candidate_count": len(candidates),
        }

    candidate = candidates[0]
    return {
        **base,
        "status": "ONE_RELATION_BOUND_CANDIDATE",
        "relation_class": relation,
        "candidates": [{
            "answer": candidate,
            "answer_sha256": _sha(candidate),
            "relation": "SUPPORTS" if polarity == "POSITIVE" else "REQUIRES_NEGATED_TARGET_REASONING",
            "support_authority": polarity == "POSITIVE",
            "correctness_authority": False,
        }],
        "hard_nonclaim": "RELATION_BOUND_EXTRACTION_IS_A_PROPOSAL_AND_NOT_A_PROOF_THAT_THE_CANDIDATE_ANSWERS_THE_FULL_QUESTION",
    }


if __name__ == "__main__":
    out = synthesize(
        contract={"kind":"YEAR","polarity":"POSITIVE"},
        focus_terms=["meridian","protocol","published"],
        evidence="The fictional Meridian protocol was first published in 2042.",
    )
    assert out["status"] == "ONE_RELATION_BOUND_CANDIDATE"
    assert out["candidates"][0]["answer"] == "2042"
    print("SELF_TEST_PASS")

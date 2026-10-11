#!/usr/bin/env python3
"""Brain-native typed evidence -> candidate synthesis V2.

V2 broadens the verified V1 relation vocabulary while preserving the same hard
boundary: deterministic extraction only, no model calls, no gold, and no
correctness authority. It additionally rejects candidates that merely repeat the
query/focus entities, which was a principal false-positive class in HLE V5.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Mapping, Sequence

from canonical.runtime import hle_evidence_candidate_synthesis_v1 as v1

SCHEMA = "PROJECT_BRAIN_HLE_EVIDENCE_CANDIDATE_SYNTHESIS_V2"

_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_PERSON = (
    r"(?:(?:Dr|Prof|Professor|Sir|Dame|Saint|St)\.?\s+)?"
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+"
    r"(?:\s+(?:(?:de|del|da|di|la|le|van|von|of|the)\s+)?"
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+){0,5}"
)
_PHRASE = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+){0,7}"
_KINSHIP = (
    "nephew|niece|son|daughter|brother|sister|uncle|aunt|"
    "grandson|granddaughter|grandfather|grandmother|cousin|husband|wife"
)
_DEMONYM = {
    "german":"Germany","french":"France","italian":"Italy","spanish":"Spain",
    "japanese":"Japan","chinese":"China","canadian":"Canada","australian":"Australia",
    "american":"United States","british":"United Kingdom","english":"United Kingdom",
    "scottish":"Scotland","irish":"Ireland","dutch":"Netherlands","swedish":"Sweden",
    "norwegian":"Norway","danish":"Denmark","finnish":"Finland","swiss":"Switzerland",
    "austrian":"Austria","belgian":"Belgium","greek":"Greece","portuguese":"Portugal",
    "russian":"Russia","indian":"India","brazilian":"Brazil","mexican":"Mexico",
}

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

def _clean(v: str) -> str | None:
    x = _canon(v).strip(" \t\r\n,;:.()[]{}\"'“”‘’")
    x = re.split(
        r"\b(?:because|although|while|whereas|after|before|during|near|when|which|that|who)\b",
        x, maxsplit=1, flags=re.I,
    )[0].strip(" ,;:.")
    if not x or len(x) > 140 or len(x.split()) > 12:
        return None
    return x

def _focus_replay(candidate: str, focus_terms: Sequence[str]) -> bool:
    ct = set(_tokens(candidate))
    if not ct:
        return False
    ft: set[str] = set()
    for raw in focus_terms:
        ft.update(_tokens(str(raw)))
    return bool(ft) and ct.issubset(ft)

def _emit(out: list[tuple[str,str]], raw: str, relation: str, focus_terms: Sequence[str]) -> None:
    x = _clean(raw)
    if x and not _focus_replay(x, focus_terms):
        key = x.casefold()
        if key not in {a.casefold() for a,_ in out}:
            out.append((x, relation))

def _relation_candidates(kind: str, evidence: str, focus_terms: Sequence[str]) -> list[tuple[str,str]]:
    out: list[tuple[str,str]] = []
    text = _canon(evidence)
    low = text.casefold()

    if kind == "PERSON":
        patterns = [
            r"\b(?:written|composed|created|painted|founded|invented|discovered|directed|performed|recorded)\s+by\s+(" + _PERSON + r")",
            r"\b(?:author|composer|creator|founder|inventor|discoverer|director|artist)\s+(?:was|is)\s+(" + _PERSON + r")",
            r"\b(" + _PERSON + r")\s+(?:was|is)\s+(?:an?\s+|the\s+)?(?:composer|author|artist|mountaineer|president|inventor|discoverer|explorer|writer|poet)\b",
            r"\bfirst\s+(?:person|man|woman|mountaineer|president|explorer)\s+[^.;]{0,90}?\b(?:was|is)\s+(" + _PERSON + r")",
        ]
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                _emit(out, m.group(1), "EXPLICIT_PERSON_RELATION", focus_terms)

    elif kind in {"LOCATION","LOCATION_OR_ENTITY"}:
        patterns = [
            r"\bcapital(?:\s+and\s+largest\s+city)?\s+(?:of\s+[^,.;]{1,60}\s+)?(?:is|was)\s+(" + _PHRASE + r")(?=[,.;]|$)",
            r"\b(" + _PHRASE + r")\s+(?:is|was)\s+the\s+capital\s+of\b",
            r"\bborn\s+(?:on\s+[^,;]{1,35}\s+)?(?:in|at)\s+(" + _PHRASE + r")(?=[,.;]|$)",
            r"\b(?:originated|originates|came|comes)\s+from\s+(" + _PHRASE + r")(?=[,.;]|$)",
            r"\b(?:is|was)\s+(?:located|situated|based)\s+in\s+(" + _PHRASE + r")(?=[,.;]|$)",
        ]
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                _emit(out, m.group(1), "EXPLICIT_LOCATION_RELATION", focus_terms)
        for dem,country in _DEMONYM.items():
            if re.search(r"\b"+re.escape(dem)+r"\b", low):
                _emit(out, country, "DEMONYM_COUNTRY_RELATION", focus_terms)

    elif kind == "RELATION_TERM":
        for m in re.finditer(r"\b(?:was|is)\s+(?:the\s+)?("+_KINSHIP+r")\s+of\b", text, re.I):
            _emit(out, m.group(1), "EXPLICIT_KINSHIP_RELATION", focus_terms)

    elif kind in {"TERM","ENTITY_OR_TERM","SHORT_TEXT"}:
        patterns = [
            r"\b(?:also\s+known\s+as|known\s+as|called|termed|designated|named)\s+(?:a|an|the)?\s*([^,.;]{1,90})(?=[,.;]|$)",
            r"\b(?:name|term)\s+(?:given|used)\s+(?:for|to)\s+[^.;]{1,100}?\s+(?:is|was)\s+([^,.;]{1,90})(?=[,.;]|$)",
            r"\b(?:equals?|equal\s+to|gives?)\s+(?:the\s+)?([^,.;]{1,70})(?=[,.;]|$)",
        ]
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                _emit(out, m.group(1), "EXPLICIT_TERM_RELATION", focus_terms)
        if "mass" in low and "acceleration" in low and "force" in low:
            _emit(out, "Force", "NEWTON_SECOND_LAW_RELATION", focus_terms)

    elif kind == "WORK_TITLE":
        patterns = [
            r"\b(?:play|film|movie|opera|novel|book|song|album)\s+([A-Z][^,.;]{1,90}?)(?=[,.;]|\s+(?:was|is|by|set|written|composed|released)\b)",
            r"\b([A-Z][A-Za-z0-9'’:\- ]{1,90}?)\s+(?:is|was)\s+(?:a|an|the)\s+(?:play|film|movie|opera|novel|book|song|album)\b",
        ]
        for p in patterns:
            for m in re.finditer(p, text):
                _emit(out, m.group(1), "EXPLICIT_WORK_TITLE_RELATION", focus_terms)

    return out

def synthesize(*, contract: Mapping[str,Any], focus_terms: Sequence[str], evidence: str) -> dict[str,Any]:
    if not isinstance(contract, Mapping):
        raise ValueError("CONTRACT_REQUIRED")
    kind = str(contract.get("kind") or "").upper()
    polarity = str(contract.get("polarity") or "POSITIVE").upper()
    if polarity != "POSITIVE":
        return {
            "schema":SCHEMA,"status":"NO_CANDIDATE__NONPOSITIVE_POLARITY",
            "kind":kind,"polarity":polarity,"candidates":[],
            "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,
            "model_dependency_count":0,"candidate_answer_authority":False,
            "semantic_truth_authority":False,"terminal_authority":False,
        }
    matched, coverage = v1._anchor_coverage(focus_terms, evidence)
    base = {
        "schema":SCHEMA,"kind":kind,"polarity":polarity,
        "evidence_sha256":_sha(evidence),"matched_focus_terms":matched,
        "focus_coverage":coverage,"candidate_answer_authority":False,
        "semantic_truth_authority":False,"gold_accessed":False,
        "external_model_calls":0,"external_reasoning_model_calls":0,
        "model_dependency_count":0,"incremental_spend_usd":0,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    # V1 required two matched anchors whenever a query had more than one term.
    # That is too strict for short evidence windows: an explicit answer relation
    # can be locally valid while only one discriminative query anchor survives
    # into the same sentence/window. V2 therefore requires at least one visible
    # objective anchor, while the relation extractor and focus-replay rejection
    # remain the precision gates.
    if len(matched) < 1:
        return {**base,"status":"NO_CANDIDATE__INSUFFICIENT_OBJECTIVE_ANCHOR_COVERAGE","candidates":[]}

    # Preserve every V1 relation that already worked.
    try:
        legacy = v1.synthesize(contract={**dict(contract),"polarity":"POSITIVE"},
                               focus_terms=focus_terms,evidence=evidence)
    except Exception:
        legacy = {}
    if legacy.get("status") == "ONE_RELATION_BOUND_CANDIDATE":
        rows = legacy.get("candidates") or []
        if len(rows) == 1:
            ans = str(rows[0].get("answer") or "")
            if ans and not _focus_replay(ans, focus_terms):
                return {
                    **base,"status":"ONE_RELATION_BOUND_CANDIDATE",
                    "relation_class":str(legacy.get("relation_class") or "V1_RELATION"),
                    "candidates":[{
                        "answer":ans,"answer_sha256":_sha(ans),"relation":"SUPPORTS",
                        "support_authority":True,"correctness_authority":False,
                    }],
                    "legacy_v1_relation_reused":True,
                    "hard_nonclaim":"RELATION_EXTRACTION_IS_A_PROPOSAL_NOT_FULL_QUESTION_CORRECTNESS",
                }

    rows = _relation_candidates(kind, evidence, focus_terms)
    if len(rows) != 1:
        return {
            **base,"status":"NO_CANDIDATE__RELATION_ABSENT_OR_AMBIGUOUS",
            "candidates":[],"raw_candidate_count":len(rows),
            "relation_classes_seen":sorted({r for _,r in rows}),
        }
    answer, relation = rows[0]
    return {
        **base,"status":"ONE_RELATION_BOUND_CANDIDATE","relation_class":relation,
        "candidates":[{
            "answer":answer,"answer_sha256":_sha(answer),"relation":"SUPPORTS",
            "support_authority":True,"correctness_authority":False,
        }],
        "legacy_v1_relation_reused":False,
        "hard_nonclaim":"RELATION_EXTRACTION_IS_A_PROPOSAL_NOT_FULL_QUESTION_CORRECTNESS",
    }

if __name__ == "__main__":
    x=synthesize(contract={"kind":"RELATION_TERM","polarity":"POSITIVE"},
                 focus_terms=["napoleon","france"],
                 evidence="Napoleon III was the nephew of Napoleon I of France.")
    assert x["candidates"][0]["answer"].casefold()=="nephew"
    print("SELF_TEST_PASS")

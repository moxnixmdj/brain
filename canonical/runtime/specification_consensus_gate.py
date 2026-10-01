"""Fail-closed source-trace and cross-extractor consensus gate.

Semantic extractors are untrusted, replaceable cognition substrates. This module
owns the deterministic protocol around them:
1) every source sentence must be classified by every extractor,
2) every extracted requirement must anchor to exact source text,
3) independent extractors must agree on requirement/non-requirement status,
4) requirement semantics must agree on a normalized behavioral signature,
5) any disagreement or missing coverage returns UNKNOWN/fail-closed.

This module does not itself perform natural-language understanding.
"""
from __future__ import annotations

import re
from typing import Any


def source_sentences(text: str) -> list[dict[str, Any]]:
    parts=[]
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        raw=m.group(0)
        stripped=raw.strip()
        if not stripped:
            continue
        start=m.start()+len(raw)-len(raw.lstrip())
        end=start+len(stripped)
        parts.append({"id":f"S{len(parts)+1}","start":start,"end":end,"text":stripped})
    return parts


def _signature(item: dict[str, Any]) -> tuple[Any, ...]:
    def norm(v: Any) -> str:
        return " ".join(str(v or "").lower().split())
    constraints=tuple(sorted(norm(x) for x in item.get("constraints",[]) or []))
    return (
        norm(item.get("actor")),
        norm(item.get("action")),
        norm(item.get("object")),
        norm(item.get("condition")),
        bool(item.get("negated",False)),
        constraints,
    )


def assess_consensus(source_text: str, extractor_outputs: list[dict[str, Any]]) -> dict[str, Any]:
    sentences=source_sentences(source_text)
    expected={s["id"]:s for s in sentences}
    failures: list[str]=[]

    if len(extractor_outputs)<2:
        failures.append("FEWER_THAN_TWO_INDEPENDENT_EXTRACTORS")

    names=[str(x.get("extractor_id","")).strip() for x in extractor_outputs]
    if any(not x for x in names):
        failures.append("MISSING_EXTRACTOR_ID")
    if len(set(names))!=len(names):
        failures.append("DUPLICATE_EXTRACTOR_ID")

    by_extractor: dict[str,dict[str,dict[str,Any]]]={}
    for output in extractor_outputs:
        eid=str(output.get("extractor_id","")).strip()
        items=output.get("sentences")
        if not isinstance(items,list):
            failures.append(f"INVALID_SENTENCE_LIST:{eid}")
            continue
        mapped={}
        for item in items:
            sid=str(item.get("source_sentence_id",""))
            if sid in mapped:
                failures.append(f"DUPLICATE_SENTENCE_CLASSIFICATION:{eid}:{sid}")
            mapped[sid]=item
            src=expected.get(sid)
            if src is None:
                failures.append(f"UNKNOWN_SOURCE_SENTENCE:{eid}:{sid}")
                continue
            quote=str(item.get("source_quote",""))
            if quote!=src["text"]:
                failures.append(f"SOURCE_QUOTE_MISMATCH:{eid}:{sid}")
            cls=str(item.get("class",""))
            if cls not in {"requirement","non_requirement"}:
                failures.append(f"INVALID_CLASS:{eid}:{sid}")
            if cls=="requirement":
                if not str(item.get("requirement_id","")).strip():
                    failures.append(f"MISSING_REQUIREMENT_ID:{eid}:{sid}")
                if not any(_signature(item)):
                    failures.append(f"EMPTY_REQUIREMENT_SIGNATURE:{eid}:{sid}")
        missing=sorted(set(expected)-set(mapped))
        for sid in missing:
            failures.append(f"UNCLASSIFIED_SOURCE_SENTENCE:{eid}:{sid}")
        by_extractor[eid]=mapped

    if by_extractor:
        for sid in expected:
            observed=[]
            for eid,mapped in by_extractor.items():
                if sid in mapped:
                    observed.append((eid,mapped[sid]))
            classes={str(item.get("class","")) for _,item in observed}
            if len(classes)>1:
                failures.append(f"CLASS_DISAGREEMENT:{sid}")
                continue
            if classes=={"requirement"}:
                signatures={_signature(item) for _,item in observed}
                if len(signatures)>1:
                    failures.append(f"SEMANTIC_SIGNATURE_DISAGREEMENT:{sid}")

    failures=sorted(set(failures))
    accepted=[]
    if not failures and extractor_outputs:
        first=by_extractor[names[0]]
        for sid,src in expected.items():
            item=first[sid]
            if item.get("class")=="requirement":
                accepted.append({
                    "source_sentence_id":sid,
                    "source_quote":src["text"],
                    "requirement_id":item["requirement_id"],
                    "actor":item.get("actor"),
                    "action":item.get("action"),
                    "object":item.get("object"),
                    "condition":item.get("condition"),
                    "negated":bool(item.get("negated",False)),
                    "constraints":sorted(str(x) for x in item.get("constraints",[]) or []),
                })

    return {
        "schema":"BRAIN_SPECIFICATION_CONSENSUS_RESULT_V1",
        "pass":not failures,
        "status":"PASS" if not failures else "UNKNOWN",
        "source_sentence_count":len(sentences),
        "extractor_count":len(extractor_outputs),
        "accepted_requirements":accepted,
        "failures":failures,
    }

"""Deterministic source-obligation inventory for acceptance-model completeness.

This is not a natural-language requirement interpreter. It inventories source spans
that contain high-risk scope quantifiers / explicit variation language and checks
that each span is mapped to a normalized requirement with a non-example scenario.

Purpose: prevent a builder from validating only visible examples when the source
explicitly quantifies over future/arbitrary populations. It preserves the semantic
residual rather than guessing what the source means.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable, Mapping, Sequence

_SENTENCE_RE=re.compile(r"(?<=[.!?])\s+|\n\s*\n+")
_HIGH_RISK_PATTERNS=(
    ("FUTURE", re.compile(r"\bfuture\b",re.I)),
    ("ARBITRARY", re.compile(r"\barbitrary\b",re.I)),
    ("ANY", re.compile(r"\bany\b",re.I)),
    ("EVERY", re.compile(r"\bevery\b",re.I)),
    ("ALL", re.compile(r"\ball\b",re.I)),
    ("MAY_VARY", re.compile(r"\bmay\s+(?:have|contain|vary|differ)\b",re.I)),
    ("DIFFERENT", re.compile(r"\bdifferent\b",re.I)),
    ("NUMBER_VARIATION", re.compile(r"\bdifferent\s+numbers?\b",re.I)),
    ("MISSING_OPTIONAL", re.compile(r"\bmissing\s+optional\b",re.I)),
)
_NORMATIVE_RE=re.compile(r"\b(must|must not|should|required|require|assume|treat)\b",re.I)

@dataclass(frozen=True)
class SourceObligation:
    obligation_id:str
    source:str
    excerpt:str
    tags:tuple[str,...]
    normative:bool

@dataclass(frozen=True)
class RequirementBinding:
    requirement_id:str
    source_obligation_ids:tuple[str,...]
    scenario_kinds:tuple[str,...]

def _norm_space(s:str)->str:
    return " ".join(s.split())

def inventory_source_obligations(text:str, source:str)->list[SourceObligation]:
    if not isinstance(text,str) or not text.strip():
        raise ValueError("source text must be non-empty")
    out=[]
    for raw in _SENTENCE_RE.split(text):
        excerpt=_norm_space(raw.strip())
        if not excerpt:
            continue
        tags=tuple(name for name,pat in _HIGH_RISK_PATTERNS if pat.search(excerpt))
        if not tags:
            continue
        digest=hashlib.sha256((source+"\0"+excerpt).encode()).hexdigest()[:16]
        out.append(SourceObligation(
            obligation_id="SRC-"+digest,
            source=source,
            excerpt=excerpt,
            tags=tags,
            normative=bool(_NORMATIVE_RE.search(excerpt)),
        ))
    return out

def validate_source_coverage(
    obligations:Sequence[SourceObligation],
    bindings:Sequence[RequirementBinding],
)->list[str]:
    errors=[]
    by_obligation:dict[str,list[RequirementBinding]]={}
    for b in bindings:
        for oid in b.source_obligation_ids:
            by_obligation.setdefault(oid,[]).append(b)
    known={o.obligation_id for o in obligations}
    for b in bindings:
        for oid in b.source_obligation_ids:
            if oid not in known:
                errors.append(f"UNKNOWN_SOURCE_OBLIGATION:{oid}:{b.requirement_id}")
    for o in obligations:
        bs=by_obligation.get(o.obligation_id,[])
        if not bs:
            errors.append(f"UNMAPPED_SOURCE_OBLIGATION:{o.obligation_id}")
            continue
        high_scope=bool(set(o.tags)&{"FUTURE","ARBITRARY","ANY","EVERY","ALL","MAY_VARY","DIFFERENT","NUMBER_VARIATION","MISSING_OPTIONAL"})
        if high_scope and not any(
            any(k in {"METAMORPHIC","GENERATIVE","HELDOUT_VARIATION","COUNTEREXAMPLE"} for k in b.scenario_kinds)
            for b in bs
        ):
            errors.append(f"SCOPE_CLAIM_WITHOUT_NONEXAMPLE_SCENARIO:{o.obligation_id}")
    return sorted(set(errors))

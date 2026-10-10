"""Fail-closed semantic identifiability gate.

This gate never invents or scores interpretations. Upstream mechanisms may propose
source-grounded interpretations. This module only decides whether the supplied
evidence identifies exactly one materially distinct interpretation.

It therefore prevents "pick the most plausible guess" from being counted as
semantic understanding when the source does not discriminate among alternatives.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_SEMANTIC_IDENTIFIABILITY_GATE_V1"

def _norm_text(v: Any) -> str:
    return " ".join(str(v or "").split())

def adjudicate(
    interpretations: Sequence[Mapping[str, Any]],
    *,
    authorized_context_ids: Sequence[str] = (),
) -> dict[str, Any]:
    if not isinstance(interpretations, Sequence) or isinstance(interpretations, (str, bytes)):
        raise ValueError("interpretations must be a sequence")
    ctx = sorted({_norm_text(x) for x in authorized_context_ids if _norm_text(x)})
    rows=[]
    errors=[]
    seen=set()
    for i,row in enumerate(interpretations):
        if not isinstance(row, Mapping):
            errors.append(f"INTERPRETATION_NOT_OBJECT:{i}")
            continue
        iid=_norm_text(row.get("id"))
        meaning=_norm_text(row.get("meaning"))
        if not iid or not meaning:
            errors.append(f"INTERPRETATION_ID_OR_MEANING_MISSING:{i}")
            continue
        if iid in seen:
            errors.append("DUPLICATE_INTERPRETATION_ID:"+iid)
            continue
        seen.add(iid)
        source_ok=row.get("consistent_with_source")
        context_ok=row.get("consistent_with_authorized_context")
        material=row.get("materially_distinct")
        if source_ok not in (True,False):
            errors.append("SOURCE_CONSISTENCY_UNKNOWN:"+iid)
        if context_ok not in (True,False):
            errors.append("CONTEXT_CONSISTENCY_UNKNOWN:"+iid)
        if material not in (True,False):
            errors.append("MATERIALITY_UNKNOWN:"+iid)
        discriminator=_norm_text(row.get("discriminator"))
        rows.append({
            "id":iid,
            "meaning":meaning,
            "consistent_with_source":source_ok is True,
            "consistent_with_authorized_context":context_ok is True,
            "materially_distinct":material is True,
            "discriminator":discriminator or None,
        })
    if errors:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "terminal_authority":False,
        }
    viable=[
        r for r in rows
        if r["consistent_with_source"]
        and r["consistent_with_authorized_context"]
        and r["materially_distinct"]
    ]
    if len(viable)==1:
        return {
            "schema":SCHEMA,
            "status":"UNIQUE",
            "interpretation":viable[0],
            "authorized_context_ids":ctx,
            "terminal_authority":False,
            "rule":"UNIQUE_ONLY_AFTER_UPSTREAM_EVIDENCE_MARKS_ALL_MATERIAL_ALTERNATIVES",
        }
    if not viable:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "error":"NO_SOURCE_AND_CONTEXT_CONSISTENT_MATERIAL_INTERPRETATION",
            "authorized_context_ids":ctx,
            "terminal_authority":False,
        }
    missing=[r["id"] for r in viable if not r["discriminator"]]
    return {
        "schema":SCHEMA,
        "status":"AMBIGUOUS",
        "ambiguity_witness":[
            {"id":r["id"],"meaning":r["meaning"],"discriminator":r["discriminator"]}
            for r in viable
        ],
        "missing_discriminators":missing,
        "authorized_context_ids":ctx,
        "terminal_authority":False,
        "next":"ACQUIRE_AUTHORIZED_DISCRIMINATING_EVIDENCE",
    }

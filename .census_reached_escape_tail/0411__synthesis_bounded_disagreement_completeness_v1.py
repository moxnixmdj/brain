from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from canonical.runtime.bounded_claim_support import parse_fact

SCHEMA="PROJECT_BRAIN_SYNTHESIS_BOUNDED_DISAGREEMENT_COMPLETENESS_V1"


def _fail(reason:str, *, details:Any=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "required_uncertainty_units":[],
        "scope_complete":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if details is not None:
        out["details"]=details
    return out


def compile_required_uncertainty(
    evidence:Sequence[Mapping[str,Any]],
)->dict[str,Any]:
    if isinstance(evidence,(str,bytes)) or not isinstance(evidence,Sequence):
        return _fail("EVIDENCE_SEQUENCE_REQUIRED")
    parsed=[]
    seen=set()
    for i,row in enumerate(evidence):
        if not isinstance(row,Mapping):
            return _fail("EVIDENCE_ROW_INVALID",details={"index":i})
        eid=row.get("evidence_id")
        text=row.get("text")
        provenance=row.get("provenance")
        if not isinstance(eid,str) or not eid or eid in seen:
            return _fail("EVIDENCE_ID_INVALID_OR_DUPLICATE",details={"index":i})
        seen.add(eid)
        if not isinstance(text,str) or not text.strip():
            return _fail("EVIDENCE_TEXT_INVALID",details={"evidence_id":eid})
        if not isinstance(provenance,list) or not provenance:
            return _fail("EVIDENCE_PROVENANCE_REQUIRED",details={"evidence_id":eid})
        p=parse_fact(text,default_source=eid)
        if p.get("status")!="RESOLVED":
            return _fail(
                "EVIDENCE_OUTSIDE_BOUNDED_FACT_GRAMMAR",
                details={"evidence_id":eid,"parse":p},
            )
        fact=p["fact"]
        parsed.append({
            "evidence_id":eid,
            "entity":fact["entity"],
            "field":fact["field"],
            "value":fact["value"],
            "text":text,
            "provenance":provenance,
        })

    groups=defaultdict(list)
    for row in parsed:
        groups[(row["entity"],row["field"])].append(row)

    units=[]
    for (entity,field),rows in sorted(groups.items()):
        values=sorted({r["value"] for r in rows})
        if len(values)<=1:
            continue
        rows=sorted(rows,key=lambda r:(r["value"],r["evidence_id"]))
        provenance=[]
        seen_prov=set()
        for r in rows:
            for p in r["provenance"]:
                if not isinstance(p,Mapping):
                    return _fail("PROVENANCE_ROW_INVALID",details={"evidence_id":r["evidence_id"]})
                source_id=p.get("source_id")
                locator=p.get("locator")
                if not isinstance(source_id,str) or not source_id:
                    return _fail("PROVENANCE_SOURCE_ID_INVALID",details={"evidence_id":r["evidence_id"]})
                key=(source_id,str(locator or ""))
                if key in seen_prov:
                    continue
                seen_prov.add(key)
                item={"source_id":source_id}
                if locator is not None:
                    item["locator"]=str(locator)
                provenance.append(item)
        uid=f"{entity}::{field}"
        text=(
            f"Conflicting verified evidence reports different values for "
            f"{entity} {field}: "+", ".join(values)+"."
        )
        units.append({
            "uncertainty_id":uid,
            "entity":entity,
            "field":field,
            "values":values,
            "evidence_ids":[r["evidence_id"] for r in rows],
            "text":text,
            "provenance":provenance,
        })

    return {
        "schema":SCHEMA,
        "status":"PASS__COMPLETE_FOR_BOUNDED_FACT_DISAGREEMENT_SEMANTICS",
        "required_uncertainty_units":units,
        "required_uncertainty_unit_count":len(units),
        "parsed_evidence_count":len(parsed),
        "scope_complete":True,
        "scope":"ALL_VERIFIED_EVIDENCE_ROWS_RESOLVE_TO_EXPLICIT_ENTITY_FIELD_VALUE_FACTS__MATERIAL_DISAGREEMENT_DEFINED_AS_MULTIPLE_DISTINCT_VALUES_FOR_THE_SAME_ENTITY_FIELD_KEY",
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }

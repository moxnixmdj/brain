"""Certified bounded OEWN decision-evidence clauses V1.

Recognizes exact standalone source lines:

  Sense terminal <sense-id>: <canonical-json-object>
  Sense observation <observation-id> cost <canonical-json-number> for <sense-id>: <canonical-json>
  Sense observed <observation-id>: <canonical-json>

These clauses prove only their literal bounded coordinates. They do not prove
open-world sense completeness, observation completeness, or semantic truth
outside the exact source span.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="BRAIN_CERTIFIED_OEWN_DECISION_EVIDENCE_V1"
_TOKEN=r"[A-Za-z0-9_.:%+-]+"
_RE_TERMINAL=re.compile(rf"^Sense terminal (?P<sid>{_TOKEN}): (?P<value>.+)$")
_RE_OBS=re.compile(
    rf"^Sense observation (?P<oid>{_TOKEN}) cost (?P<cost>.+?) for "
    rf"(?P<sid>{_TOKEN}): (?P<value>.+)$"
)
_RE_OBSERVED=re.compile(rf"^Sense observed (?P<oid>{_TOKEN}): (?P<value>.+)$")


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _json(raw:str,name:str)->Any:
    try:value=json.loads(raw)
    except Exception as exc: raise ValueError(name+"_JSON_INVALID") from exc
    if _canon(value)!=raw: raise ValueError(name+"_JSON_NOT_CANONICAL")
    return value


def _record(source:str,kind:str,payload:Mapping[str,Any],c0:int,c1:int,b0:int,b1:int,raw:bytes)->dict[str,Any]:
    digest=sha256(raw).hexdigest()
    cid="SENSE-EVID-"+sha256(
        (source+"\0"+kind+"\0"+str(b0)+"\0"+str(b1)+"\0"+_canon(dict(payload))).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "clause_id":cid,"source_id":source,"kind":kind,**dict(payload),
        "source_span_chars":[c0,c1],"source_span_bytes":[b0,b1],
        "source_text_sha256":digest,
    }


def parse_sense_evidence(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_TEXT_MISSING","terminal_authority":False}
    if not isinstance(source,str) or not source.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_ID_MISSING","terminal_authority":False}

    clauses=[]; seen=set(); co=0; bo=0
    try:
        for line in text.splitlines(keepends=True):
            body=line.rstrip("\r\n"); raw=body.encode("utf-8")
            m=_RE_TERMINAL.match(body)
            if m:
                sid=m.group("sid"); value=_json(m.group("value"),"TERMINAL_SIGNATURE")
                if not isinstance(value,Mapping): raise ValueError("TERMINAL_SIGNATURE_NOT_OBJECT")
                slot=("TERMINAL",sid)
                if slot in seen: raise ValueError("DUPLICATE_TERMINAL_SLOT:"+sid)
                seen.add(slot)
                clauses.append(_record(source,"TERMINAL_SIGNATURE",{"sense_id":sid,"terminal_signature":dict(value)},co,co+len(body),bo,bo+len(raw),raw))
            else:
                m=_RE_OBS.match(body)
                if m:
                    oid=m.group("oid"); sid=m.group("sid")
                    cost=_json(m.group("cost"),"OBSERVATION_COST")
                    if isinstance(cost,bool) or not isinstance(cost,(int,float)) or float(cost)<0:
                        raise ValueError("OBSERVATION_COST_INVALID")
                    value=_json(m.group("value"),"OBSERVATION_OUTCOME")
                    slot=("OBSERVATION",oid,sid)
                    if slot in seen: raise ValueError("DUPLICATE_OBSERVATION_SLOT:"+oid+":"+sid)
                    seen.add(slot)
                    clauses.append(_record(source,"OBSERVATION_OUTCOME",{
                        "observation_id":oid,"sense_id":sid,
                        "cost_units":float(cost),"outcome":value,
                    },co,co+len(body),bo,bo+len(raw),raw))
                else:
                    m=_RE_OBSERVED.match(body)
                    if m:
                        oid=m.group("oid"); value=_json(m.group("value"),"OBSERVED_OUTCOME")
                        slot=("OBSERVED",oid)
                        if slot in seen: raise ValueError("DUPLICATE_OBSERVED_OUTCOME:"+oid)
                        seen.add(slot)
                        clauses.append(_record(source,"OBSERVED_OUTCOME",{
                            "observation_id":oid,"observed_outcome":value,
                        },co,co+len(body),bo,bo+len(raw),raw))
            co+=len(line); bo+=len(line.encode("utf-8"))
    except Exception as exc:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":type(exc).__name__+":"+str(exc),"terminal_authority":False}

    return {
        "schema":SCHEMA,"status":"PARSED","clauses":clauses,
        "terminal_authority":False,
        "scope":"BOUNDED_EXACT_OEWN_DECISION_EVIDENCE_CLAUSES_ONLY",
    }

"""Provenance-bound relational/aggregate receipt dataflow V3.

V3 adds a deliberately small relational language over structured prior receipts:
- count of <collection> from <source>
- first/last <field> from <source>
- all <field> values from <source>
- <field> from <source> where <other_field> is "<value>"

Every result is derived only from explicit structured receipts. Sensitive fields,
missing collections, multiple matching records, heterogeneous projections, and
oversized outputs fail closed.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

from canonical.runtime.osworld_v21_receipt_dataflow_v2 import (
    SCHEMA as V2_SCHEMA,
    materialize_explicit_references as materialize_scalar_references,
)

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_RECEIPT_DATAFLOW_V3"
MAX_DEPTH=10
MAX_ITEMS=512
MAX_OUTPUT_CHARS=20000
SENSITIVE={
    "password","passwd","secret","token","api key","apikey","authorization",
    "cookie","private key","access key","session id",
}

_COUNT=re.compile(
    r"\bthe\s+count\s+of\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+from\s+"
    r"(Mailhub|TeamChat|CloudCRM|VaultBank|BudgetWise|Calendar|browser|the browser|workbook)\b",
    re.I,
)
_PROJECTION=re.compile(
    r"\bthe\s+(first|last|all)\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)"
    r"(?:\s+values?)?\s+from\s+"
    r"(Mailhub|TeamChat|CloudCRM|VaultBank|BudgetWise|Calendar|browser|the browser|workbook)\b",
    re.I,
)
_FILTERED=re.compile(
    r"\bthe\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+from\s+"
    r"(Mailhub|TeamChat|CloudCRM|VaultBank|BudgetWise|Calendar|browser|the browser|workbook)\s+"
    r"where\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+"
    r"(?:is|equals|=)\s+[\x22“]([^\x22”]{1,1000})[\x22”]",
    re.I,
)

class RelationalDataflowError(ValueError):
    pass

def _norm(value:str)->str:
    return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",value).casefold()).strip()

def _sensitive(name:str)->bool:
    n=_norm(name)
    return any(n==x or x in n for x in SENSITIVE)

def _source_rows(prior_rows:Sequence[Mapping[str,Any]],source_hint:str):
    hint=_norm(source_hint)
    aliases={
        "mailhub":{"mailhub"},
        "teamchat":{"teamchat"},
        "cloudcrm":{"cloudcrm"},
        "vaultbank":{"vaultbank"},
        "budgetwise":{"budgetwise"},
        "calendar":{"calendar","calendar web","calendar_web"},
        "browser":{"browser"},
        "the browser":{"browser"},
        "workbook":{"libreoffice calc","libreoffice_calc","workbook"},
    }.get(hint,{hint})
    out=[]
    for row_index,row in enumerate(prior_rows):
        if not isinstance(row,Mapping):
            continue
        for key in ("web_app_result","browser_result","app_result"):
            src=row.get(key)
            if not isinstance(src,Mapping) or src.get("ok") is not True:
                continue
            labels={_norm(key)}
            for lk in ("app","type","operation"):
                lv=src.get(lk)
                if isinstance(lv,str):
                    labels.add(_norm(lv))
            if key=="browser_result":
                labels.add("browser")
            if labels.isdisjoint(aliases):
                continue
            payload=src.get("result",src)
            out.append((row_index,key,payload))
    return out

def _walk_collections(value:Any,path=(),depth=0):
    if depth>MAX_DEPTH:
        return
    if isinstance(value,Mapping):
        for k,v in value.items():
            if isinstance(k,str):
                if isinstance(v,Sequence) and not isinstance(v,(str,bytes,bytearray)):
                    yield path+(k,),list(v)
                yield from _walk_collections(v,path+(k,),depth+1)
    elif isinstance(value,Sequence) and not isinstance(value,(str,bytes,bytearray)):
        for i,v in enumerate(value):
            yield from _walk_collections(v,path+(str(i),),depth+1)

def _walk_records(value:Any,path=(),depth=0):
    if depth>MAX_DEPTH:
        return
    if isinstance(value,Mapping):
        yield path,value
        for k,v in value.items():
            if isinstance(k,str):
                yield from _walk_records(v,path+(k,),depth+1)
    elif isinstance(value,Sequence) and not isinstance(value,(str,bytes,bytearray)):
        if len(value)>MAX_ITEMS:
            return
        for i,v in enumerate(value):
            yield from _walk_records(v,path+(str(i),),depth+1)

def _field(record:Mapping[str,Any],name:str):
    wanted=_norm(name)
    matches=[]
    for k,v in record.items():
        if isinstance(k,str) and _norm(k)==wanted:
            if _sensitive(k):
                return []
            if v is None or isinstance(v,(bool,int,float,str)):
                matches.append((k,v))
    return matches

def resolve_count(prior_rows,collection_name:str,source_hint:str)->dict[str,Any]:
    if _sensitive(collection_name):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__SENSITIVE_FIELD"}
    wanted=_norm(collection_name)
    matches=[]
    for row_index,source,payload in _source_rows(prior_rows,source_hint):
        for path,items in _walk_collections(payload):
            if path and _norm(path[-1])==wanted and len(items)<=MAX_ITEMS:
                matches.append({"row_index":row_index,"source":source,"path":list(path),"count":len(items)})
    distinct={m["count"] for m in matches}
    if not matches:
        return {"schema":SCHEMA,"pass":False,"status":"OPEN__COLLECTION_NOT_FOUND","collection":wanted}
    if len(distinct)!=1:
        return {"schema":SCHEMA,"pass":False,"status":"OPEN__AGGREGATE_AMBIGUOUS","collection":wanted,"matches":matches}
    return {
        "schema":SCHEMA,"pass":True,"status":"PASS__RECEIPTED_COLLECTION_COUNT",
        "value":next(iter(distinct)),"collection":wanted,
        "provenance":[{k:m[k] for k in ("row_index","source","path")} for m in matches],
    }

def resolve_projection(prior_rows,mode:str,field_name:str,source_hint:str)->dict[str,Any]:
    if mode not in {"first","last","all"}:
        raise RelationalDataflowError("PROJECTION_MODE_INVALID")
    if _sensitive(field_name):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__SENSITIVE_FIELD"}
    candidates=[]
    for row_index,source,payload in _source_rows(prior_rows,source_hint):
        for path,record in _walk_records(payload):
            found=_field(record,field_name)
            for key,value in found:
                candidates.append({
                    "row_index":row_index,"source":source,"path":list(path)+(key,),"value":value
                })
    if not candidates:
        return {"schema":SCHEMA,"pass":False,"status":"OPEN__FIELD_NOT_FOUND","field":_norm(field_name)}
    if mode=="first":
        chosen=[candidates[0]]
        value=candidates[0]["value"]
    elif mode=="last":
        chosen=[candidates[-1]]
        value=candidates[-1]["value"]
    else:
        chosen=candidates
        value=[c["value"] for c in candidates]
        if len(value)>MAX_ITEMS:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__PROJECTION_TOO_LARGE"}
    encoded=json.dumps(value,ensure_ascii=False,default=str)
    if len(encoded)>MAX_OUTPUT_CHARS:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__PROJECTION_TOO_LARGE"}
    return {
        "schema":SCHEMA,"pass":True,"status":"PASS__RECEIPTED_RELATIONAL_PROJECTION",
        "mode":mode,"field":_norm(field_name),"value":value,
        "provenance":[{k:c[k] for k in ("row_index","source","path")} for c in chosen],
    }

def resolve_filtered_scalar(prior_rows,field_name:str,source_hint:str,filter_field:str,filter_value:str)->dict[str,Any]:
    if _sensitive(field_name) or _sensitive(filter_field):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__SENSITIVE_FIELD"}
    matches=[]
    for row_index,source,payload in _source_rows(prior_rows,source_hint):
        for path,record in _walk_records(payload):
            filters=_field(record,filter_field)
            if len(filters)!=1 or str(filters[0][1])!=filter_value:
                continue
            values=_field(record,field_name)
            if len(values)==1:
                matches.append({
                    "row_index":row_index,"source":source,
                    "path":list(path)+(values[0][0],),"value":values[0][1],
                })
    if not matches:
        return {"schema":SCHEMA,"pass":False,"status":"OPEN__RELATION_NOT_FOUND"}
    distinct={json.dumps(m["value"],sort_keys=True,ensure_ascii=False) for m in matches}
    if len(distinct)!=1:
        return {"schema":SCHEMA,"pass":False,"status":"OPEN__RELATION_AMBIGUOUS","matches":matches}
    return {
        "schema":SCHEMA,"pass":True,"status":"PASS__UNIQUE_FILTERED_RECEIPT_SCALAR",
        "field":_norm(field_name),"filter_field":_norm(filter_field),
        "filter_value":filter_value,"value":matches[0]["value"],
        "provenance":[{k:m[k] for k in ("row_index","source","path")} for m in matches],
    }

def _relational_refs(text:str):
    refs=[]
    for kind,pat in (("count",_COUNT),("projection",_PROJECTION),("filtered",_FILTERED)):
        for m in pat.finditer(text):
            refs.append((m.start(),m.end(),kind,m))
    refs.sort(key=lambda x:(x[0],-(x[1]-x[0])))
    out=[];cursor=-1
    for item in refs:
        if item[0]>=cursor:
            out.append(item);cursor=item[1]
    return out

def materialize_explicit_references(text:str,prior_rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        raise RelationalDataflowError("TEXT_REQUIRED")
    refs=_relational_refs(text)
    if not refs:
        scalar=materialize_scalar_references(text,prior_rows)
        return {**scalar,"schema":SCHEMA,"parent_schema":V2_SCHEMA}

    chunks=[];bindings=[];cursor=0
    for start,end,kind,m in refs:
        if kind=="count":
            resolved=resolve_count(prior_rows,m.group(1),m.group(2))
        elif kind=="projection":
            resolved=resolve_projection(prior_rows,m.group(1).lower(),m.group(2),m.group(3))
        else:
            resolved=resolve_filtered_scalar(prior_rows,m.group(1),m.group(2),m.group(3),m.group(4))
        if resolved.get("pass") is not True:
            return {
                "schema":SCHEMA,"status":"OPEN__RELATIONAL_REFERENCE_UNRESOLVED","pass":False,
                "resolution":resolved,"text":text,"bindings":bindings,
            }
        value=resolved["value"]
        chunks.append(text[cursor:start])
        if isinstance(value,list):
            chunks.append(json.dumps(value,ensure_ascii=False))
        else:
            chunks.append(json.dumps(str(value),ensure_ascii=False))
        cursor=end
        bindings.append({
            "kind":kind,"value":value,"status":resolved["status"],
            "provenance":resolved.get("provenance",[]),
        })
    chunks.append(text[cursor:])
    interim="".join(chunks)
    scalar=materialize_scalar_references(interim,prior_rows)
    if scalar.get("pass") is not True:
        return {**scalar,"schema":SCHEMA,"relational_bindings":bindings}
    return {
        "schema":SCHEMA,"status":"PASS__RELATIONAL_REFERENCES_MATERIALIZED","pass":True,
        "text":scalar.get("text",interim),
        "bindings":bindings+list(scalar.get("bindings") or []),
    }

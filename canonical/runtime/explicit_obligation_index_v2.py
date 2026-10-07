from __future__ import annotations
from hashlib import sha256
import json
from typing import Any,Mapping
from canonical.runtime.explicit_obligation_index_v1 import _segments,_shift
from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.bounded_imperative_predicate_argument_semantics_v1 import parse_imperative

SCHEMA="BRAIN_EXPLICIT_OBLIGATION_INDEX_V2"

def _canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def build_index(source_text:str,*,source_id:str)->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["SOURCE_TEXT_MISSING"],"terminal_authority":False}
    source_sha=sha256(source_text.encode()).hexdigest()
    obligations=[]; unresolved=[]; ignored=[]
    for i,(start,end,segment) in enumerate(_segments(source_text)):
        parsed=parse_clause(segment); route="MODAL"
        if parsed.get("status")!="RESOLVED":
            ip=parse_imperative(segment)
            if ip.get("status")=="RESOLVED":
                parsed=ip; route="IMPERATIVE"
        if parsed.get("status")=="RESOLVED":
            g=parsed["semantic_graph"]
            graph=dict(g)
            for k in ("subject_span","predicate_span","object_span"):
                if graph.get(k) is not None: graph[k]=_shift(graph[k],start)
            condition=None
            if isinstance(parsed.get("condition"),Mapping):
                c=parsed["condition"]; condition={"relation":c["relation"],"text":c["text"],"span":_shift(c["span"],start)}
            payload={"source_id":source_id,"source_sha256":source_sha,"segment_span":[start,end],"semantic_graph":graph,"condition":condition,"route":route}
            obligations.append({
              "obligation_id":"OBL:"+sha256(_canon(payload).encode()).hexdigest(),
              "source_id":source_id,"source_sha256":source_sha,"segment_index":i,"segment_span":[start,end],
              "segment_sha256":sha256(segment.encode()).hexdigest(),"semantic_graph":graph,"condition":condition,"route":route
            })
        else:
            unresolved.append({"segment_index":i,"segment_span":[start,end],"segment_sha256":sha256(segment.encode()).hexdigest(),
              "parse_status":parsed.get("status"),"parse_reason":parsed.get("reason")})
    return {"schema":SCHEMA,"status":"INDEXED_WITH_UNRESOLVED" if unresolved else "INDEXED",
      "source_id":source_id,"source_sha256":source_sha,"segment_count":len(_segments(source_text)),
      "obligation_count":len(obligations),"obligations":obligations,"unresolved_segments":unresolved,
      "ignored_nonobligation_segments":ignored,"one_sided_sound_discovery":True,
      "absence_of_indexed_obligation_proves_no_obligation":False,"semantic_completeness_claim":False,
      "terminal_authority":False}

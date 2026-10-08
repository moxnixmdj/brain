"""Exact set-inclusion membership closure v1.

This runtime proves a controlled membership claim from a finite graph of:
  * direct membership facts:
      "<SET> contains <ITEM>."
      "The complete members of <SET> are {a, b, ...}."
  * explicit subset facts:
      "<SUBSET> is a subset of <SUPERSET>."

Optional evidence prefixes "<SOURCE> states that ..." and "<SOURCE> reports that ..."
are accepted.

For claim "<ITEM> is a member of <TARGET_SET>.", the runtime performs exact BFS
from every set directly containing ITEM through explicit subset edges. A support
certificate contains one shortest proof path and every evidence_id used by it.

No taxonomy, lexical category, superclass inference, synonymy, or external ontology
is consulted. Any evidence row outside the controlled grammar leaves the whole
closure unresolved rather than being silently ignored.
"""
from __future__ import annotations

from collections import deque
import re
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_BOUNDED_SET_INCLUSION_MEMBERSHIP_CLOSURE_V1"

_CLAIM=re.compile(
    r"^(?P<item>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+is\s+a\s+member\s+of\s+"
    r"(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s*\.?$",
    re.I,
)
_CONTAINS=re.compile(
    r"^(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+contains\s+"
    r"(?P<item>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s*\.?$",
    re.I,
)
_COMPLETE=re.compile(
    r"^The\s+complete\s+members\s+of\s+"
    r"(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+are\s+\{(?P<members>[^{}]*)\}\s*\.?$",
    re.I,
)
_SUBSET=re.compile(
    r"^(?P<subset>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+is\s+a\s+subset\s+of\s+"
    r"(?P<superset>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s*\.?$",
    re.I,
)
_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+states\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
)

def _norm(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().casefold().split())

def _strip_source(text:str)->tuple[str|None,str]:
    raw=" ".join(text.strip().split())
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            return " ".join(m.group("source").split()),m.group("body")
    return None,raw

def _parse_claim(text:Any)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED"}
    m=_CLAIM.fullmatch(" ".join(text.strip().split()))
    if not m:
        return {"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_SET_MEMBERSHIP_GRAMMAR"}
    return {"status":"RESOLVED","item":_norm(m.group("item")),"set":_norm(m.group("set"))}

def _parse_members(raw:str)->tuple[list[str]|None,str|None]:
    if not raw.strip(): return [],None
    xs=[_norm(x) for x in raw.split(",")]
    if any(not x for x in xs): return None,"EMPTY_MEMBER_TOKEN"
    if len(xs)!=len(set(xs)): return None,"DUPLICATE_MEMBER_TOKEN"
    return xs,None

def _parse_evidence(text:Any)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED"}
    source,body=_strip_source(text)

    m=_COMPLETE.fullmatch(body)
    if m:
        members,error=_parse_members(m.group("members"))
        if error: return {"status":"FAIL_CLOSED","reason":error}
        return {"status":"RESOLVED","kind":"COMPLETE","set":_norm(m.group("set")),
                "members":members,"source":source}

    m=_CONTAINS.fullmatch(body)
    if m:
        return {"status":"RESOLVED","kind":"MEMBER","set":_norm(m.group("set")),
                "item":_norm(m.group("item")),"source":source}

    m=_SUBSET.fullmatch(body)
    if m:
        a=_norm(m.group("subset"));b=_norm(m.group("superset"))
        if a==b:
            return {"status":"RESOLVED","kind":"SUBSET","subset":a,"superset":b,
                    "source":source,"reflexive":True}
        return {"status":"RESOLVED","kind":"SUBSET","subset":a,"superset":b,
                "source":source,"reflexive":False}

    return {"status":"UNRESOLVED","reason":"EVIDENCE_OUTSIDE_SET_MEMBERSHIP_CLOSURE_GRAMMAR"}

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":"PAYLOAD_MAPPING_REQUIRED","terminal_authority":False}
    claim=_parse_claim(payload.get("claim_text"))
    rows=payload.get("evidence")
    if claim.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","pass":False,"reason":claim.get("reason"),
                "predicate_truth":"UNKNOWN","terminal_authority":False}
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":"EVIDENCE_SEQUENCE_REQUIRED","terminal_authority":False}

    memberships:dict[str,list[tuple[str,str]]]={}
    complete:dict[str,tuple[set[str],str]]={}
    edges:dict[str,list[tuple[str,str]]]={}
    audit=[]
    seen_ids=set()

    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":f"EVIDENCE_ROW_INVALID:{i}","terminal_authority":False}
        eid=row.get("evidence_id")
        text=row.get("text")
        if not isinstance(eid,str) or not eid.strip() or eid in seen_ids:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":f"EVIDENCE_ID_INVALID_OR_DUPLICATE:{i}","terminal_authority":False}
        seen_ids.add(eid)
        parsed=_parse_evidence(text)
        if parsed.get("status")=="FAIL_CLOSED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":parsed.get("reason"),"evidence_id":eid,"terminal_authority":False}
        if parsed.get("status")!="RESOLVED":
            return {"schema":SCHEMA,"status":"UNRESOLVED","pass":False,
                    "reason":"ONE_OR_MORE_EVIDENCE_ROWS_OUTSIDE_CONTROLLED_CLOSURE_GRAMMAR",
                    "unresolved_evidence_id":eid,"predicate_truth":"UNKNOWN","terminal_authority":False}
        audit.append({"evidence_id":eid,**{k:v for k,v in parsed.items() if k not in {"status","source"}}})

        if parsed["kind"]=="MEMBER":
            memberships.setdefault(parsed["item"],[]).append((parsed["set"],eid))
        elif parsed["kind"]=="COMPLETE":
            key=parsed["set"];members=set(parsed["members"])
            if key in complete and complete[key][0]!=members:
                return {"schema":SCHEMA,"status":"UNRESOLVED__CONFLICTING_COMPLETE_SET_DEFINITIONS",
                        "pass":False,"predicate_truth":"UNKNOWN","set":key,"terminal_authority":False}
            complete[key]=(members,eid)
            for member in members:
                memberships.setdefault(member,[]).append((key,eid))
        else:
            edges.setdefault(parsed["subset"],[]).append((parsed["superset"],eid))

    item=claim["item"];target=claim["set"]

    direct_starts=sorted(memberships.get(item,[]))
    queue=deque()
    visited=set()
    parent:dict[str,tuple[str|None,str|None]]={}
    for start,eid in direct_starts:
        if start not in visited:
            visited.add(start);queue.append(start);parent[start]=(None,eid)

    found=target in visited
    while queue and not found:
        current=queue.popleft()
        for nxt,eid in sorted(edges.get(current,[])):
            if nxt in visited: continue
            visited.add(nxt);parent[nxt]=(current,eid);queue.append(nxt)
            if nxt==target:
                found=True;break

    target_complete=complete.get(target)
    explicit_absence=target_complete is not None and item not in target_complete[0]

    if found and explicit_absence:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED__EVIDENCE_INCONSISTENT",
            "pass":False,"predicate_truth":"UNKNOWN",
            "reason":"SUPPORT_PATH_CONFLICTS_WITH_COMPLETE_TARGET_ENUMERATION",
            "claim":{"item":item,"set":target},
            "complete_target_evidence_id":target_complete[1],
            "terminal_authority":False,
        }

    if explicit_absence:
        return {
            "schema":SCHEMA,"status":"RESOLVED","pass":True,"predicate_truth":"FALSE",
            "relation":"CONFLICTS","claim":{"item":item,"set":target},
            "conflict_evidence_ids":[target_complete[1]],
            "proof":{"rule":"COMPLETE_TARGET_SET_EXCLUDES_ITEM",
                     "complete_members":sorted(target_complete[0])},
            "evidence_audit":audit,"terminal_authority":False,
        }

    if not found:
        return {
            "schema":SCHEMA,"status":"RESOLVED","pass":True,"predicate_truth":"FALSE",
            "relation":"UNSUPPORTED_OPEN_WORLD","claim":{"item":item,"set":target},
            "support_evidence_ids":[],
            "proof":{"rule":"NO_EXPLICIT_MEMBERSHIP_PATH_FOUND",
                     "absence_not_interpreted_as_nonmembership":True},
            "evidence_audit":audit,"terminal_authority":False,
        }

    # Reconstruct one shortest proof path from target back to a direct membership.
    set_path=[target]
    edge_eids=[]
    cur=target
    while parent[cur][0] is not None:
        prev,eid=parent[cur]
        assert prev is not None and eid is not None
        edge_eids.append(eid);set_path.append(prev);cur=prev
    membership_eid=parent[cur][1]
    assert membership_eid is not None
    set_path.reverse();edge_eids.reverse()
    support_ids=[membership_eid]+edge_eids

    return {
        "schema":SCHEMA,"status":"RESOLVED","pass":True,"predicate_truth":"TRUE",
        "relation":"SUPPORTS","claim":{"item":item,"set":target},
        "support_evidence_ids":support_ids,
        "proof":{
            "rule":"DIRECT_MEMBERSHIP_PLUS_SUBSET_TRANSITIVE_CLOSURE",
            "item":item,"set_path":set_path,
            "membership_evidence_id":membership_eid,
            "subset_evidence_ids":edge_eids,
            "path_length":len(edge_eids),
        },
        "evidence_audit":audit,
        "terminal_authority":False,
        "scope":"FINITE_EXPLICIT_MEMBERSHIP_AND_SUBSET_GRAPH_ONLY",
    }

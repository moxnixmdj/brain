"""Wikidata P279 ontology entailment verifier V1.

Given two already-bound Wikidata class QIDs, find a bounded path of non-deprecated
P279 (subclass of) statements using Special:EntityData JSON.

A successful path proves only this ontology-scoped consequence:
  instance(x, left) => instance(x, right)
under Wikidata's documented P279 semantics.

It does not bind natural-language surface forms to QIDs, prove real-world truth,
or prove non-entailment when no bounded path is found.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Callable

SCHEMA="PROJECT_BRAIN_WIKIDATA_P279_ONTOLOGY_ENTAILMENT_V1"
_QID=re.compile(r"^Q[1-9][0-9]*$")
_HOST="www.wikidata.org"
_UA="ProjectBrain-WikidataOntologyEntailment/1.0"

class OntologyRelationError(ValueError):
    pass

def _qid(value:Any)->str:
    q=str(value or "").strip()
    if _QID.fullmatch(q) is None:
        raise OntologyRelationError("WIKIDATA_QID_INVALID")
    return q

def _url(qid:str)->str:
    return f"https://{_HOST}/wiki/Special:EntityData/{qid}.json"

def _default_fetch(qid:str,timeout:int)->tuple[bytes,str,int]:
    req=urllib.request.Request(
        _url(qid),
        headers={"User-Agent":_UA,"Accept":"application/json"},
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(4_000_000)
        final=r.geturl()
        host=(urllib.parse.urlsplit(final).hostname or "").lower()
        if host not in {_HOST,"wikidata.org"}:
            raise OntologyRelationError("WIKIDATA_REDIRECT_OUTSIDE_AUTHORITY")
        return raw,final,int(getattr(r,"status",200))

def _parse_entity(qid:str,raw:bytes,final_url:str,http_status:int)->tuple[list[str],dict[str,Any]]:
    try:
        data=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise OntologyRelationError("WIKIDATA_ENTITY_JSON_INVALID") from exc
    entities=data.get("entities")
    row=entities.get(qid) if isinstance(entities,dict) else None
    if not isinstance(row,dict) or str(row.get("id") or "")!=qid:
        raise OntologyRelationError("WIKIDATA_ENTITY_IDENTITY_MISMATCH")
    claims=row.get("claims")
    p279=claims.get("P279",[]) if isinstance(claims,dict) else []
    if not isinstance(p279,list):
        raise OntologyRelationError("WIKIDATA_P279_CLAIMS_INVALID")
    parents=[]
    for stmt in p279:
        if not isinstance(stmt,dict) or stmt.get("rank")=="deprecated":
            continue
        snak=stmt.get("mainsnak")
        if not isinstance(snak,dict) or snak.get("snaktype")!="value":
            continue
        dv=snak.get("datavalue")
        value=dv.get("value") if isinstance(dv,dict) else None
        target=value.get("id") if isinstance(value,dict) else None
        if isinstance(target,str) and _QID.fullmatch(target) and target not in parents:
            parents.append(target)
    receipt={
        "qid":qid,
        "entity_json_sha256":sha256(raw).hexdigest(),
        "lastrevid":row.get("lastrevid"),
        "modified":row.get("modified"),
        "final_url":final_url,
        "http_status":http_status,
        "nondeprecated_p279_targets":sorted(parents),
    }
    return sorted(parents),receipt

def prove_subclass_path(
    left_qid:Any,
    right_qid:Any,
    *,
    max_depth:int=6,
    max_nodes:int=64,
    timeout:int=15,
    fetch:Callable[[str,int],tuple[bytes,str,int]]|None=None,
)->dict[str,Any]:
    try:
        left=_qid(left_qid); right=_qid(right_qid)
        if left==right:
            raise OntologyRelationError("DISTINCT_QIDS_REQUIRED")
        if isinstance(max_depth,bool) or not isinstance(max_depth,int) or not 1<=max_depth<=12:
            raise OntologyRelationError("MAX_DEPTH_INVALID")
        if isinstance(max_nodes,bool) or not isinstance(max_nodes,int) or not 2<=max_nodes<=256:
            raise OntologyRelationError("MAX_NODES_INVALID")
        fetch=fetch or _default_fetch
        queue=deque([(left,[left],0)])
        seen={left}
        receipts={}
        nodes=0
        while queue and nodes<max_nodes:
            qid,path,depth=queue.popleft()
            raw,final,status=fetch(qid,timeout)
            parents,receipt=_parse_entity(qid,raw,final,status)
            receipts[qid]=receipt
            nodes+=1
            if right in parents:
                proof_path=path+[right]
                return {
                    "schema":SCHEMA,
                    "status":"PASS__WIKIDATA_P279_PATH_PROVED",
                    "pass":True,
                    "left_qid":left,
                    "right_qid":right,
                    "relation":"LEFT_ENTAILS_RIGHT",
                    "relation_scope":"WIKIDATA_CLASS_MEMBERSHIP_ENTAILMENT",
                    "p279_path":proof_path,
                    "edge_count":len(proof_path)-1,
                    "fetched_node_count":nodes,
                    "fetch_receipts":[receipts[x] for x in path],
                    "ontology_semantics":"P279_SUBCLASS_INCLUSION__ALL_INSTANCES_OF_LEFT_ARE_INSTANCES_OF_RIGHT",
                    "surface_to_qid_binding_proved":False,
                    "real_world_factual_truth_proved":False,
                    "non_entailment_authority":False,
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                    "terminal_authority":False,
                    "terminal_credit_delta":0,
                }
            if depth>=max_depth:
                continue
            for parent in parents:
                if parent not in seen:
                    seen.add(parent)
                    queue.append((parent,path+[parent],depth+1))
        return {
            "schema":SCHEMA,
            "status":"OPEN__P279_PATH_NOT_ESTABLISHED_WITHIN_BOUND",
            "pass":False,
            "left_qid":left,
            "right_qid":right,
            "relation_scope":"WIKIDATA_CLASS_MEMBERSHIP_ENTAILMENT",
            "max_depth":max_depth,
            "max_nodes":max_nodes,
            "fetched_node_count":nodes,
            "fetch_receipts":[receipts[x] for x in sorted(receipts)],
            "reason":"BOUNDED_SEARCH_DID_NOT_PROVE_PATH",
            "non_entailment_authority":False,
            "surface_to_qid_binding_proved":False,
            "real_world_factual_truth_proved":False,
            "model_dependency_count":0,
            "incremental_spend_usd":0,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "non_entailment_authority":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }

"""Producer-independent verifier for cross-document effect hypothesis world sets V1."""
from __future__ import annotations

from itertools import combinations, product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_HYPOTHESIS_WORLDSET_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_HYPOTHESIS_WORLDSET_V1"
MAX_DOCUMENTS=32
MAX_SLOTS=16
MAX_HYPOTHESES_PER_SLOT=16
MAX_WORLDS=4096
_NO_VALUE={"kind":"NO_APPLICABLE_EFFECT"}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _effect(v:Any)->dict[str,Any]:
    if not isinstance(v,Mapping):
        raise ValueError("EFFECT_NOT_OBJECT")
    allowed={"effect_id","target_id","effect_class","value","conditions","valid_from","valid_until","supersedes","source_locator"}
    if set(v)!=allowed:
        raise ValueError("EFFECT_FIELD_SET_NOT_EXACT")
    return calculus._validate_effect(v)


def _parse(problem:Mapping[str,Any]):
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","hypothesis_set_complete","documents","query"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    if problem.get("hypothesis_set_complete") is not True:
        raise ValueError("HYPOTHESIS_SET_NOT_COMPLETE")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    docs=problem.get("documents")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)) or not docs or len(docs)>MAX_DOCUMENTS:
        raise ValueError("DOCUMENTS_INVALID")
    clean=[]; dids=set(); sids=set(); slots=0; worlds=1
    for doc in docs:
        if not isinstance(doc,Mapping) or set(doc)!={"document_id","effect_slots"}:
            raise ValueError("DOCUMENT_INVALID")
        did=_token(doc.get("document_id"),"DOCUMENT_ID")
        if did in dids: raise ValueError("DOCUMENT_ID_DUPLICATE")
        dids.add(did)
        rows=doc.get("effect_slots")
        if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
            raise ValueError("SLOTS_INVALID")
        cslots=[]
        for slot in rows:
            slots+=1
            if slots>MAX_SLOTS: raise ValueError("SLOT_BOUND_EXCEEDED")
            if not isinstance(slot,Mapping) or set(slot)!={"slot_id","hypothesis_set_complete","hypotheses"}:
                raise ValueError("SLOT_INVALID")
            sid=_token(slot.get("slot_id"),"SLOT_ID")
            if sid in sids: raise ValueError("SLOT_ID_DUPLICATE")
            sids.add(sid)
            if slot.get("hypothesis_set_complete") is not True:
                raise ValueError("SLOT_SET_NOT_COMPLETE")
            hs=slot.get("hypotheses")
            if not isinstance(hs,Sequence) or isinstance(hs,(str,bytes)) or not hs or len(hs)>MAX_HYPOTHESES_PER_SLOT:
                raise ValueError("HYPOTHESES_INVALID")
            ch=[]; hids=set(); effs=set()
            for hyp in hs:
                if not isinstance(hyp,Mapping) or set(hyp)!={"hypothesis_id","effect"}:
                    raise ValueError("HYPOTHESIS_INVALID")
                hid=_token(hyp.get("hypothesis_id"),"HYPOTHESIS_ID")
                if hid in hids: raise ValueError("HYPOTHESIS_ID_DUPLICATE")
                hids.add(hid)
                eff=_effect(hyp.get("effect"))
                ce=_canon(eff)
                if ce in effs: raise ValueError("SEMANTIC_HYPOTHESIS_DUPLICATE")
                effs.add(ce)
                ch.append({"hypothesis_id":hid,"effect":eff})
            ch.sort(key=lambda x:x["hypothesis_id"])
            worlds*=len(ch)
            if worlds>MAX_WORLDS: raise ValueError("WORLD_BOUND_EXCEEDED")
            cslots.append({"slot_id":sid,"hypotheses":ch})
        cslots.sort(key=lambda x:x["slot_id"])
        clean.append({"document_id":did,"effect_slots":cslots})
    q=problem.get("query")
    if not isinstance(q,Mapping) or set(q)!={"target_id","as_of","context"}:
        raise ValueError("QUERY_INVALID")
    _token(q.get("target_id"),"TARGET_ID"); _token(q.get("as_of"),"AS_OF")
    if not isinstance(q.get("context"),Mapping): raise ValueError("CONTEXT_INVALID")
    _canon(q)
    clean.sort(key=lambda x:x["document_id"])
    return case_id,clean,dict(q)


def _world_outcomes(result:Mapping[str,Any])->tuple[str,...]:
    if result.get("pass") is True:
        return (_canon(result.get("effective_value")),)
    if result.get("status")=="OPEN__INCOMPARABLE_EFFECTS_REQUIRE_DISCRIMINATOR":
        vals=sorted({_canon(x.get("value")) for x in result.get("surviving_effects",[]) if isinstance(x,Mapping)})
        if vals:return tuple(vals)
    if result.get("status")=="OPEN__NO_APPLICABLE_EFFECT":
        return (_canon(_NO_VALUE),)
    return (_canon({"status":result.get("status")}),)


def _minimum_slots(worlds:Sequence[Mapping[str,Any]])->list[str]:
    pairs={(i,j) for i in range(len(worlds)) for j in range(i+1,len(worlds))
           if worlds[i]["outcome_signature"]!=worlds[j]["outcome_signature"]}
    if not pairs:return []
    slots=sorted({s for w in worlds for s in w["selection"]})
    covers={s:{(i,j) for i,j in pairs if worlds[i]["selection"].get(s)!=worlds[j]["selection"].get(s)} for s in slots}
    for width in range(1,len(slots)+1):
        for subset in combinations(slots,width):
            cov=set()
            for s in subset: cov.update(covers[s])
            if cov==pairs:return list(subset)
    return []


def _recompute(problem:Mapping[str,Any])->dict[str,Any]:
    case_id,docs,query=_parse(problem)
    slots=[]
    for doc in docs:
        for slot in doc["effect_slots"]:
            slots.append((doc["document_id"],slot["slot_id"],slot["hypotheses"]))
    worlds=[]; union={}
    for selected in product(*(row[2] for row in slots)):
        selection={sid:h["hypothesis_id"] for (_,sid,_),h in zip(slots,selected)}
        bydoc={d["document_id"]:[] for d in docs}
        for (did,_,_),h in zip(slots,selected):
            bydoc[did].append(dict(h["effect"]))
        typed={}; specs=[]
        for did in sorted(bydoc):
            path="compiled/"+did+".json"
            doc={"schema":calculus.DOC_SCHEMA,"document_id":did,"effects":sorted(bydoc[did],key=lambda x:x["effect_id"])}
            typed[path]=doc
            specs.append({"path":path,"sha256":calculus._sha(doc)})
        case={"schema":calculus.CASE_SCHEMA,"case_id":case_id,"documents":specs,"query":query}
        result=calculus.compute(case,typed)
        outs=_world_outcomes(result)
        for key in outs:
            union[key]=json.loads(key)
        worlds.append({
            "selection":dict(sorted(selection.items())),
            "outcome_signature":list(outs),
            "calculus_status":result.get("status"),
            "effective_value":result.get("effective_value"),
            "surviving_effect_ids":list(result.get("surviving_effect_ids") or []),
        })
    worlds.sort(key=lambda x:_canon(x))
    keys=sorted(union)
    if len(keys)==1 and union[keys[0]]!=_NO_VALUE:
        return {
            "status":"PASS__EFFECT_AMBIGUITY_TERMINALLY_IRRELEVANT",
            "pass":True,
            "world_count":len(worlds),
            "effective_value":union[keys[0]],
            "minimum_discriminator_slots":[],
        }
    return {
        "status":"OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
        "pass":False,
        "world_count":len(worlds),
        "possible_outcomes":[union[k] for k in keys],
        "minimum_discriminator_slots":_minimum_slots(worlds),
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        for key,val in expected.items():
            if result.get(key)!=val:
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
        if result.get("hypothesis_set_complete_relative_to_declared_universe") is not True:
            errors.append("DECLARED_UNIVERSE_COMPLETENESS_FLAG_MISSING")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_WORLDSET_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_RECOMPUTATION_RELATIVE_TO_DECLARED_COMPLETE_FINITE_TYPED_EFFECT_HYPOTHESIS_UNIVERSE",
    }

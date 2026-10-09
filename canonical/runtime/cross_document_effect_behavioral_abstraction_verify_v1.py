"""Independent verifier for cross-document effect behavioral abstraction V1."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from itertools import combinations, product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_semantic_lattice_v5 as lattice

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_BEHAVIORAL_ABSTRACTION_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_BEHAVIORAL_ABSTRACTION_V1"
MAX_EFFECTS=8
MAX_BEHAVIORAL_WORLDS=4096
MAX_RELEVANCE_VARIABLES=16


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _exact(component:Any)->tuple[bool,Any]:
    if not isinstance(component,Mapping) or component.get("kind")=="TOP":
        return False,None
    if "value" not in component:
        return False,None
    return True,deepcopy(component.get("value"))


def _app_domain(components:Mapping[str,Any],as_of:date,context:Mapping[str,Any])->tuple[bool,...]:
    c_ok,conditions=_exact(components.get("conditions"))
    f_ok,start=_exact(components.get("valid_from"))
    u_ok,end=_exact(components.get("valid_until"))
    if c_ok:
        if not isinstance(conditions,Mapping):
            raise ValueError("EXACT_CONDITIONS_NOT_OBJECT")
        for key,val in conditions.items():
            if key not in context or _canon(context[key])!=_canon(val):
                return (False,)
    if f_ok and start is not None and as_of<date.fromisoformat(str(start)):
        return (False,)
    if u_ok and end is not None and as_of>=date.fromisoformat(str(end)):
        return (False,)
    if c_ok and f_ok and u_ok:
        return (True,)
    return (False,True)


def _powerset(items:Sequence[str])->list[tuple[str,...]]:
    ordered=tuple(sorted(items))
    out=[]
    for width in range(len(ordered)+1):
        out.extend(combinations(ordered,width))
    return [tuple(x) for x in out]


def _acyclic(graph:Mapping[str,Sequence[str]])->bool:
    visiting=set(); done=set()
    def visit(node:str)->bool:
        if node in done: return True
        if node in visiting: return False
        visiting.add(node)
        for child in graph.get(node,()):
            if not visit(str(child)): return False
        visiting.remove(node); done.add(node)
        return True
    return all(visit(n) for n in sorted(graph))


def _dominates(a:str,b:str,graph:Mapping[str,Sequence[str]])->bool:
    stack=list(graph.get(a,()))
    seen=set()
    while stack:
        x=str(stack.pop())
        if x==b: return True
        if x in seen: continue
        seen.add(x); stack.extend(graph.get(x,()))
    return False


def _minimum_vars(worlds:Sequence[Mapping[str,Any]])->list[str]:
    pairs=[
        (i,j) for i in range(len(worlds)) for j in range(i+1,len(worlds))
        if worlds[i]["outcome_signature"]!=worlds[j]["outcome_signature"]
    ]
    if not pairs: return []
    vars_=sorted({k for w in worlds for k in w["selection"]})
    if len(vars_)>MAX_RELEVANCE_VARIABLES:
        return vars_
    covers={
        var:{
            (i,j) for i,j in pairs
            if worlds[i]["selection"].get(var)!=worlds[j]["selection"].get(var)
        }
        for var in vars_
    }
    universe=set(pairs)
    for width in range(1,len(vars_)+1):
        for subset in combinations(vars_,width):
            covered=set()
            for var in subset: covered.update(covers[var])
            if covered==universe:
                return list(subset)
    return vars_


def _v5_problem(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","query"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    return {
        "schema":lattice.SCHEMA,
        "case_id":problem["case_id"],
        "source_documents":deepcopy(list(problem["source_documents"])),
        "query":deepcopy(dict(problem["query"])),
    }


def _recompute(problem:Mapping[str,Any])->dict[str,Any]:
    v5p=_v5_problem(problem)
    base=lattice.evaluate(v5p)
    if base.get("status")=="FAIL_CLOSED":
        return {"status":"FAIL_CLOSED__V5_FIELD_LATTICE","pass":False}
    if base.get("pass") is True:
        return {
            "status":"PASS__EXACT_V5_LATTICE_ALREADY_CLOSED",
            "pass":True,
            "effective_value":deepcopy(base.get("effective_value")),
            "behavioral_world_count":1,
            "behavioral_outcome_signatures":[
                "EXACT::"+_canon(base.get("effective_value"))
            ],
        }

    atoms=[x for x in (base.get("open_lattice_atoms") or []) if isinstance(x,Mapping)]
    if any(x.get("dimension")=="EFFECT_ID_INVENTORY" for x in atoms):
        return {"status":"OPEN__FINITE_EFFECT_ID_UNIVERSE_NOT_PROVED","pass":False}

    query=v5p["query"]
    as_of=date.fromisoformat(str(query["as_of"]))
    context=query["context"]

    effects={}
    docs={}
    tops={}
    for doc in base.get("lattice_documents") or []:
        if not isinstance(doc,Mapping) or doc.get("query_status")=="PROVED_QUERY_IRRELEVANT":
            continue
        inv=doc.get("query_effect_id_inventory")
        if not isinstance(inv,Mapping) or inv.get("kind")!="FINITE":
            continue
        states=doc.get("effect_states")
        if not isinstance(states,Mapping):
            raise ValueError("EFFECT_STATES_MISSING")
        for raw_eid in inv.get("values") or []:
            eid=str(raw_eid)
            if eid in effects:
                raise ValueError("EFFECT_ID_DUPLICATE")
            state=states.get(eid)
            if not isinstance(state,Mapping) or not isinstance(state.get("components"),Mapping):
                raise ValueError("EFFECT_COMPONENTS_MISSING")
            effects[eid]=deepcopy(dict(state["components"]))
            docs[eid]=str(doc.get("document_id") or "")
            tops[eid]=sorted(
                k for k,v in state["components"].items()
                if isinstance(v,Mapping) and v.get("kind")=="TOP"
            )

    ids=sorted(effects)
    if not ids:
        return {"status":"OPEN__NO_QUERY_EFFECT_ID","pass":False}
    if len(ids)>MAX_EFFECTS:
        return {"status":"OPEN__BEHAVIORAL_EFFECT_BOUND_EXCEEDED","pass":False}

    apps={}; sups={}; value_keys={}; exact_values={}
    ignored=[]

    for eid in ids:
        comp=effects[eid]
        apps[eid]=_app_domain(comp,as_of,context)
        class_ok,class_value=_exact(comp.get("effect_class"))
        sup_ok,sup=_exact(comp.get("supersedes"))
        if sup_ok:
            clean=tuple(sorted(str(x) for x in sup))
            if eid in clean or set(clean)-set(ids):
                raise ValueError("EXACT_SUPERSEDES_INVALID")
            if class_ok and str(class_value)!="DEFINE" and not clean:
                raise ValueError("EXACT_NON_DEFINE_WITH_EMPTY_SUPERSEDES")
            sups[eid]=[clean]
        else:
            domain=_powerset([x for x in ids if x!=eid])
            if class_ok and str(class_value)!="DEFINE":
                domain=[x for x in domain if x]
            if not domain:
                raise ValueError("NO_VALID_SUPERSESSION_COMPLETION")
            sups[eid]=domain
        vok,val=_exact(comp.get("value"))
        if vok:
            key="EXACT::"+_canon(val)
            value_keys[eid]=key; exact_values[key]=deepcopy(val)
        else:
            value_keys[eid]="TOP_VALUE::"+eid
        if not class_ok:
            ignored.append({
                "document_id":docs[eid],"effect_id":eid,"field":"effect_class",
                "reason":"EXECUTION_CALCULUS_EFFECTIVE_VALUE_IS_CLASS_INVARIANT_AFTER_VALIDATION",
            })

    upper=1
    for eid in ids:
        upper*=len(apps[eid])*len(sups[eid])
        if upper>MAX_BEHAVIORAL_WORLDS:
            return {"status":"OPEN__BEHAVIORAL_WORLD_BOUND_EXCEEDED","pass":False}

    worlds=[]; signatures=set(); top_survivors=set()
    app_rows=list(product(*(apps[eid] for eid in ids)))
    for sup_choice in product(*(sups[eid] for eid in ids)):
        graph={eid:list(sup_choice[i]) for i,eid in enumerate(ids)}
        if not _acyclic(graph): continue
        for app_choice in app_rows:
            applicable=[eid for i,eid in enumerate(ids) if app_choice[i]]
            selection={}
            for i,eid in enumerate(ids):
                if len(apps[eid])>1:
                    selection["APPLICABILITY::"+eid]=bool(app_choice[i])
                if len(sups[eid])>1:
                    selection["SUPERSEDES::"+eid]=list(sup_choice[i])
            if not applicable:
                sig="NO_APPLICABLE_EFFECT"; maxima=[]
            else:
                maxima=[
                    eid for eid in applicable
                    if not any(other!=eid and _dominates(other,eid,graph) for other in applicable)
                ]
                maxima.sort()
                keys=sorted({value_keys[eid] for eid in maxima})
                for eid in maxima:
                    if value_keys[eid].startswith("TOP_VALUE::"):
                        top_survivors.add(eid)
                sig=keys[0] if len(keys)==1 else "AMBIGUOUS::"+_canon(keys)
            worlds.append({"selection":selection,"outcome_signature":sig})
            signatures.add(sig)

    if not worlds:
        return {"status":"FAIL_CLOSED__NO_VALID_BEHAVIORAL_COMPLETION","pass":False}

    sigs=sorted(signatures)
    if len(sigs)==1 and sigs[0].startswith("EXACT::"):
        return {
            "status":"PASS__BEHAVIORAL_TOP_IRRELEVANT_COMMON_VALUE",
            "pass":True,
            "effective_value":deepcopy(exact_values[sigs[0]]),
            "behavioral_world_count":len(worlds),
            "behavioral_outcome_signatures":sigs,
        }

    relevant=_minimum_vars(worlds)
    obligations=[]
    for eid in sorted(top_survivors):
        obligations.append({
            "kind":"PROVE_EFFECT_VALUE","document_id":docs[eid],
            "effect_id":eid,"field":"value",
        })
    for var in relevant:
        kind,eid=var.split("::",1)
        if kind=="APPLICABILITY":
            obligations.append({
                "kind":"RESOLVE_EFFECT_APPLICABILITY_AT_QUERY",
                "document_id":docs[eid],"effect_id":eid,
                "as_of":query["as_of"],"context":deepcopy(dict(query["context"])),
                "underlying_top_fields":[
                    x for x in ("conditions","valid_from","valid_until") if x in tops[eid]
                ],
            })
        elif kind=="SUPERSEDES":
            obligations.append({
                "kind":"PROVE_SUPERSESSION_SET_FOR_EFFECT",
                "document_id":docs[eid],"effect_id":eid,
                "candidate_target_ids":[x for x in ids if x!=eid],
            })
    dedup=[]; seen=set()
    for row in obligations:
        key=_canon(row)
        if key not in seen:
            seen.add(key); dedup.append(row)

    return {
        "status":"OPEN__BEHAVIORAL_COMPLETIONS_HAVE_DISTINCT_OUTCOMES",
        "pass":False,
        "behavioral_world_count":len(worlds),
        "behavioral_outcome_signatures":sigs,
        "minimum_behavioral_discriminator_variables":relevant,
        "top_value_surviving_effect_ids":sorted(top_survivors),
        "next_behavioral_obligations":dedup,
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        keys=["status","pass"]
        if expected.get("pass") is True:
            keys+=["effective_value","behavioral_world_count","behavioral_outcome_signatures"]
        elif expected.get("status")=="OPEN__BEHAVIORAL_COMPLETIONS_HAVE_DISTINCT_OUTCOMES":
            keys+=[
                "behavioral_world_count","behavioral_outcome_signatures",
                "minimum_behavioral_discriminator_variables",
                "top_value_surviving_effect_ids","next_behavioral_obligations",
            ]
        for key in keys:
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_BEHAVIORAL_ABSTRACTION_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_V5_PARTIAL_STATE_TO_COMPLETE_FINITE_BEHAVIORAL_OVERAPPROXIMATION",
    }

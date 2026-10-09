"""Decision-relative behavioral abstraction over cross-document effect field TOPs V1.

This layer consumes the source-proved V5 field lattice, then replaces unresolved
raw semantics only with the complete finite behaviors observable by the current
execution calculus:

- effect_class is behaviorally irrelevant to effective-value computation after
  validation; when unresolved it grants no semantic claim.
- unresolved conditions/validity become applicability in {false,true}, unless
  exact proved fields already force one side.
- unresolved supersedes becomes every valid subset of the finite source-proved
  query-target effect-ID inventory, subject to exact class constraints and DAG
  acyclicity.
- unresolved values become stable opaque distinct symbols. They can never be
  returned as a verified value; if an opaque value can survive, value proof
  remains required.

All combinations are an overapproximation. Impossible source interpretations may
remain and cause abstention; they cannot create a false pass.

A pass requires every valid behavioral completion to return the same one exact
source-proved value.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from itertools import combinations, product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_semantic_lattice_v5 as lattice

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_BEHAVIORAL_ABSTRACTION_V1"
MAX_EFFECTS=8
MAX_BEHAVIORAL_WORLDS=4096
MAX_RELEVANCE_VARIABLES=16


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _exact(component:Any)->tuple[bool,Any]:
    if not isinstance(component,Mapping):
        return False,None
    if component.get("kind")=="TOP":
        return False,None
    if "value" not in component:
        return False,None
    return True,deepcopy(component.get("value"))


def _forced_applicability(
    components:Mapping[str,Any],
    *,
    as_of:date,
    context:Mapping[str,Any],
)->tuple[bool,...]:
    c_ok,conditions=_exact(components.get("conditions"))
    f_ok,valid_from=_exact(components.get("valid_from"))
    u_ok,valid_until=_exact(components.get("valid_until"))

    if c_ok:
        if not isinstance(conditions,Mapping):
            raise ValueError("EXACT_CONDITIONS_NOT_OBJECT")
        for key,expected in conditions.items():
            if key not in context or _canon(context[key])!=_canon(expected):
                return (False,)

    if f_ok and valid_from is not None:
        start=date.fromisoformat(str(valid_from))
        if as_of<start:
            return (False,)

    if u_ok and valid_until is not None:
        end=date.fromisoformat(str(valid_until))
        if as_of>=end:
            return (False,)

    if c_ok and f_ok and u_ok:
        return (True,)
    return (False,True)


def _powerset(items:Sequence[str])->list[tuple[str,...]]:
    rows=[]
    ordered=tuple(sorted(items))
    for width in range(len(ordered)+1):
        for subset in combinations(ordered,width):
            rows.append(tuple(subset))
    return rows


def _acyclic(graph:Mapping[str,Sequence[str]])->bool:
    visiting=set(); done=set()
    def visit(node:str)->bool:
        if node in done:
            return True
        if node in visiting:
            return False
        visiting.add(node)
        for child in graph.get(node,()):
            if not visit(str(child)):
                return False
        visiting.remove(node); done.add(node)
        return True
    return all(visit(node) for node in sorted(graph))


def _dominates(stronger:str,weaker:str,graph:Mapping[str,Sequence[str]])->bool:
    stack=list(graph.get(stronger,()))
    seen=set()
    while stack:
        node=str(stack.pop())
        if node==weaker:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node,()))
    return False


def _minimum_behavior_variables(worlds:Sequence[Mapping[str,Any]])->list[str]:
    pairs=[
        (i,j)
        for i in range(len(worlds))
        for j in range(i+1,len(worlds))
        if worlds[i]["outcome_signature"]!=worlds[j]["outcome_signature"]
    ]
    if not pairs:
        return []
    vars_=sorted({
        key
        for world in worlds
        for key in world["selection"]
    })
    if len(vars_)>MAX_RELEVANCE_VARIABLES:
        return vars_
    covers={}
    for var in vars_:
        covers[var]={
            (i,j) for i,j in pairs
            if worlds[i]["selection"].get(var)!=worlds[j]["selection"].get(var)
        }
    universe=set(pairs)
    for width in range(1,len(vars_)+1):
        for subset in combinations(vars_,width):
            covered=set()
            for var in subset:
                covered.update(covers[var])
            if covered==universe:
                return list(subset)
    return vars_


def _validate_problem(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","query"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    docs=problem.get("source_documents")
    query=problem.get("query")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)) or not docs:
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    if not isinstance(query,Mapping) or set(query)!={"target_id","as_of","context"}:
        raise ValueError("QUERY_INVALID")
    _token(query.get("target_id"),"QUERY_TARGET_ID")
    as_of=_token(query.get("as_of"),"QUERY_AS_OF")
    date.fromisoformat(as_of)
    if not isinstance(query.get("context"),Mapping):
        raise ValueError("QUERY_CONTEXT_INVALID")
    _canon(query.get("context"))
    return {
        "schema":lattice.SCHEMA,
        "case_id":case_id,
        "source_documents":deepcopy(list(docs)),
        "query":deepcopy(dict(query)),
    }


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        v5_problem=_validate_problem(problem)
        base_result=lattice.evaluate(v5_problem)
        if base_result.get("status")=="FAIL_CLOSED":
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__V5_FIELD_LATTICE",
                "pass":False,
                "reason":base_result.get("reason"),
                "v5_lattice_result":base_result,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        if base_result.get("pass") is True:
            return {
                "schema":SCHEMA,
                "status":"PASS__EXACT_V5_LATTICE_ALREADY_CLOSED",
                "pass":True,
                "case_id":v5_problem["case_id"],
                "effective_value":deepcopy(base_result.get("effective_value")),
                "behavioral_world_count":1,
                "behavioral_outcome_signatures":[
                    "EXACT::"+_canon(base_result.get("effective_value"))
                ],
                "ignored_top_fields":[],
                "next_behavioral_obligations":[],
                "v5_lattice_result":base_result,
                "behavioral_world_universe_complete_relative_to_v5_abstraction":True,
                "semantic_truth_authority":False,
                "terminal_authority":False,
                "boundary":"EXACT_V5_SOURCE_PROOF_PATH__NO_BEHAVIORAL_APPROXIMATION_REQUIRED",
            }

        open_atoms=[
            x for x in (base_result.get("open_lattice_atoms") or [])
            if isinstance(x,Mapping)
        ]
        if any(x.get("dimension")=="EFFECT_ID_INVENTORY" for x in open_atoms):
            return {
                "schema":SCHEMA,
                "status":"OPEN__FINITE_EFFECT_ID_UNIVERSE_NOT_PROVED",
                "pass":False,
                "case_id":v5_problem["case_id"],
                "v5_lattice_result":base_result,
                "next_behavioral_obligations":[
                    deepcopy(x.get("proof_obligation"))
                    for x in open_atoms
                    if x.get("dimension")=="EFFECT_ID_INVENTORY"
                ],
                "behavioral_world_universe_complete_relative_to_v5_abstraction":False,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        query=v5_problem["query"]
        as_of=date.fromisoformat(query["as_of"])
        context=query["context"]

        effect_rows={}
        doc_by_effect={}
        top_fields_by_effect={}
        for doc in base_result.get("lattice_documents") or []:
            if not isinstance(doc,Mapping):
                continue
            if doc.get("query_status")=="PROVED_QUERY_IRRELEVANT":
                continue
            inv=doc.get("query_effect_id_inventory")
            if not isinstance(inv,Mapping) or inv.get("kind")!="FINITE":
                continue
            states=doc.get("effect_states")
            if not isinstance(states,Mapping):
                raise ValueError("FINITE_INVENTORY_EFFECT_STATES_MISSING")
            for eid in inv.get("values") or []:
                eid=_token(eid,"EFFECT_ID")
                if eid in effect_rows:
                    raise ValueError("EFFECT_ID_DUPLICATE_ACROSS_DOCUMENTS:"+eid)
                state=states.get(eid)
                if not isinstance(state,Mapping):
                    raise ValueError("EFFECT_STATE_MISSING:"+eid)
                components=state.get("components")
                if not isinstance(components,Mapping):
                    raise ValueError("EFFECT_COMPONENTS_MISSING:"+eid)
                effect_rows[eid]=deepcopy(dict(components))
                doc_by_effect[eid]=str(doc.get("document_id") or "")
                top_fields_by_effect[eid]=sorted(
                    field for field,component in components.items()
                    if isinstance(component,Mapping) and component.get("kind")=="TOP"
                )

        effect_ids=sorted(effect_rows)
        if not effect_ids:
            return {
                "schema":SCHEMA,
                "status":"OPEN__NO_QUERY_EFFECT_ID",
                "pass":False,
                "case_id":v5_problem["case_id"],
                "v5_lattice_result":base_result,
                "next_behavioral_obligations":[],
                "behavioral_world_universe_complete_relative_to_v5_abstraction":True,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }
        if len(effect_ids)>MAX_EFFECTS:
            return {
                "schema":SCHEMA,
                "status":"OPEN__BEHAVIORAL_EFFECT_BOUND_EXCEEDED",
                "pass":False,
                "case_id":v5_problem["case_id"],
                "effect_count":len(effect_ids),
                "max_effects":MAX_EFFECTS,
                "v5_lattice_result":base_result,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        app_domains={}
        sup_domains={}
        value_keys={}
        exact_values={}
        ignored_top=[]

        for eid in effect_ids:
            components=effect_rows[eid]
            app_domains[eid]=_forced_applicability(
                components,as_of=as_of,context=context
            )
            cls_ok,cls=_exact(components.get("effect_class"))
            sup_ok,sup=_exact(components.get("supersedes"))
            if sup_ok:
                if (
                    not isinstance(sup,Sequence)
                    or isinstance(sup,(str,bytes))
                ):
                    raise ValueError("EXACT_SUPERSEDES_INVALID:"+eid)
                clean=tuple(str(x) for x in sup)
                if len(clean)!=len(set(clean)):
                    raise ValueError("EXACT_SUPERSEDES_DUPLICATE:"+eid)
                if eid in clean:
                    raise ValueError("EXACT_SELF_SUPERSESSION:"+eid)
                unknown=sorted(set(clean)-set(effect_ids))
                if unknown:
                    raise ValueError(
                        "EXACT_SUPERSESSION_OUTSIDE_PROVED_EFFECT_UNIVERSE:"
                        +eid+":"+",".join(unknown)
                    )
                if cls_ok and str(cls)!="DEFINE" and not clean:
                    raise ValueError("EXACT_NON_DEFINE_WITH_EMPTY_SUPERSEDES:"+eid)
                sup_domains[eid]=[tuple(sorted(clean))]
            else:
                candidates=_powerset([x for x in effect_ids if x!=eid])
                if cls_ok and str(cls)!="DEFINE":
                    candidates=[x for x in candidates if x]
                if not candidates:
                    raise ValueError("NO_VALID_SUPERSESSION_COMPLETION:"+eid)
                sup_domains[eid]=candidates

            val_ok,val=_exact(components.get("value"))
            if val_ok:
                key="EXACT::"+_canon(val)
                value_keys[eid]=key
                exact_values[key]=deepcopy(val)
            else:
                value_keys[eid]="TOP_VALUE::"+eid

            if not cls_ok:
                ignored_top.append({
                    "document_id":doc_by_effect[eid],
                    "effect_id":eid,
                    "field":"effect_class",
                    "reason":"EXECUTION_CALCULUS_EFFECTIVE_VALUE_IS_CLASS_INVARIANT_AFTER_VALIDATION",
                })

        raw_world_count=1
        for eid in effect_ids:
            raw_world_count*=len(app_domains[eid])
            raw_world_count*=len(sup_domains[eid])
            if raw_world_count>MAX_BEHAVIORAL_WORLDS:
                return {
                    "schema":SCHEMA,
                    "status":"OPEN__BEHAVIORAL_WORLD_BOUND_EXCEEDED",
                    "pass":False,
                    "case_id":v5_problem["case_id"],
                    "raw_behavioral_world_upper_bound":raw_world_count,
                    "max_behavioral_worlds":MAX_BEHAVIORAL_WORLDS,
                    "v5_lattice_result":base_result,
                    "semantic_truth_authority":False,
                    "terminal_authority":False,
                }

        worlds=[]
        outcome_signatures=set()
        top_value_survivors=set()

        app_products=list(product(*(app_domains[eid] for eid in effect_ids)))
        sup_products=product(*(sup_domains[eid] for eid in effect_ids))
        for sup_choice in sup_products:
            graph={
                eid:list(sup_choice[i])
                for i,eid in enumerate(effect_ids)
            }
            if not _acyclic(graph):
                continue
            for app_choice in app_products:
                applicable=[
                    eid for i,eid in enumerate(effect_ids)
                    if app_choice[i]
                ]
                selection={}
                for i,eid in enumerate(effect_ids):
                    if len(app_domains[eid])>1:
                        selection["APPLICABILITY::"+eid]=bool(app_choice[i])
                    if len(sup_domains[eid])>1:
                        selection["SUPERSEDES::"+eid]=list(sup_choice[i])

                if not applicable:
                    signature="NO_APPLICABLE_EFFECT"
                    maxima=[]
                else:
                    maxima=[]
                    for eid in applicable:
                        if not any(
                            other!=eid and _dominates(other,eid,graph)
                            for other in applicable
                        ):
                            maxima.append(eid)
                    maxima.sort()
                    keys=sorted({value_keys[eid] for eid in maxima})
                    for eid in maxima:
                        if value_keys[eid].startswith("TOP_VALUE::"):
                            top_value_survivors.add(eid)
                    if len(keys)==1:
                        signature=keys[0]
                    else:
                        signature="AMBIGUOUS::"+_canon(keys)

                worlds.append({
                    "selection":selection,
                    "outcome_signature":signature,
                    "applicable_effect_ids":applicable,
                    "surviving_effect_ids":maxima,
                })
                outcome_signatures.add(signature)
                if len(worlds)>MAX_BEHAVIORAL_WORLDS:
                    raise ValueError("BEHAVIORAL_WORLD_BOUND_INTERNAL")

        if not worlds:
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__NO_VALID_BEHAVIORAL_COMPLETION",
                "pass":False,
                "case_id":v5_problem["case_id"],
                "v5_lattice_result":base_result,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        signatures=sorted(outcome_signatures)
        if len(signatures)==1 and signatures[0].startswith("EXACT::"):
            value=exact_values[signatures[0]]
            all_top_atoms=[
                {
                    "document_id":doc_by_effect[eid],
                    "effect_id":eid,
                    "field":field,
                }
                for eid in effect_ids
                for field in top_fields_by_effect[eid]
            ]
            ignored_keys={(x["effect_id"],x["field"]) for x in ignored_top}
            for atom in all_top_atoms:
                key=(atom["effect_id"],atom["field"])
                if key in ignored_keys:
                    continue
                ignored_top.append({
                    **atom,
                    "reason":"ALL_VALID_BEHAVIORAL_COMPLETIONS_HAVE_ONE_COMMON_EXACT_VALUE",
                })
            return {
                "schema":SCHEMA,
                "status":"PASS__BEHAVIORAL_TOP_IRRELEVANT_COMMON_VALUE",
                "pass":True,
                "case_id":v5_problem["case_id"],
                "effective_value":value,
                "behavioral_world_count":len(worlds),
                "behavioral_outcome_signatures":signatures,
                "ignored_top_fields":sorted(
                    ignored_top,key=lambda x:(x["document_id"],x["effect_id"],x["field"])
                ),
                "next_behavioral_obligations":[],
                "v5_lattice_result":base_result,
                "behavioral_world_universe_complete_relative_to_v5_abstraction":True,
                "opaque_value_overapproximation_used":any(
                    value_keys[eid].startswith("TOP_VALUE::") for eid in effect_ids
                ),
                "semantic_truth_authority":False,
                "terminal_authority":False,
                "boundary":"ALL_VALID_FINITE_BEHAVIORAL_COMPLETIONS_OF_V5_TOP_RETURN_ONE_EXACT_SOURCE_PROVED_VALUE",
            }

        relevant_vars=_minimum_behavior_variables(worlds)
        obligations=[]
        for eid in sorted(top_value_survivors):
            obligations.append({
                "kind":"PROVE_EFFECT_VALUE",
                "document_id":doc_by_effect[eid],
                "effect_id":eid,
                "field":"value",
            })
        for var in relevant_vars:
            kind,eid=var.split("::",1)
            if kind=="APPLICABILITY":
                fields=[
                    x for x in ("conditions","valid_from","valid_until")
                    if x in top_fields_by_effect[eid]
                ]
                obligations.append({
                    "kind":"RESOLVE_EFFECT_APPLICABILITY_AT_QUERY",
                    "document_id":doc_by_effect[eid],
                    "effect_id":eid,
                    "as_of":query["as_of"],
                    "context":deepcopy(dict(query["context"])),
                    "underlying_top_fields":fields,
                })
            elif kind=="SUPERSEDES":
                obligations.append({
                    "kind":"PROVE_SUPERSESSION_SET_FOR_EFFECT",
                    "document_id":doc_by_effect[eid],
                    "effect_id":eid,
                    "candidate_target_ids":[x for x in effect_ids if x!=eid],
                })

        seen=set(); clean_obligations=[]
        for row in obligations:
            key=_canon(row)
            if key in seen:
                continue
            seen.add(key); clean_obligations.append(row)

        load_bearing={(str(x.get("effect_id")),str(x.get("field"))) for x in clean_obligations if x.get("field")}
        for eid in effect_ids:
            for field in top_fields_by_effect[eid]:
                key=(eid,field)
                if field=="effect_class":
                    continue
                if key in load_bearing:
                    continue
                if field=="value" and eid in top_value_survivors:
                    continue
                if field in {"conditions","valid_from","valid_until"} and any(
                    x.get("kind")=="RESOLVE_EFFECT_APPLICABILITY_AT_QUERY"
                    and x.get("effect_id")==eid
                    for x in clean_obligations
                ):
                    continue
                if field=="supersedes" and any(
                    x.get("kind")=="PROVE_SUPERSESSION_SET_FOR_EFFECT"
                    and x.get("effect_id")==eid
                    for x in clean_obligations
                ):
                    continue
                ignored_top.append({
                    "document_id":doc_by_effect[eid],
                    "effect_id":eid,
                    "field":field,
                    "reason":"NONINTERFERING_OVER_COMPLETE_FINITE_BEHAVIORAL_WORLD_OVERAPPROXIMATION",
                })

        return {
            "schema":SCHEMA,
            "status":"OPEN__BEHAVIORAL_COMPLETIONS_HAVE_DISTINCT_OUTCOMES",
            "pass":False,
            "case_id":v5_problem["case_id"],
            "behavioral_world_count":len(worlds),
            "behavioral_outcome_signatures":signatures,
            "minimum_behavioral_discriminator_variables":relevant_vars,
            "top_value_surviving_effect_ids":sorted(top_value_survivors),
            "ignored_top_fields":sorted(
                ignored_top,key=lambda x:(x["document_id"],x["effect_id"],x["field"])
            ),
            "next_behavioral_obligations":clean_obligations,
            "v5_lattice_result":base_result,
            "behavioral_world_universe_complete_relative_to_v5_abstraction":True,
            "opaque_value_overapproximation_used":any(
                value_keys[eid].startswith("TOP_VALUE::") for eid in effect_ids
            ),
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "boundary":"DISTINCT_OUTCOMES_REMAIN_ACROSS_COMPLETE_FINITE_BEHAVIORAL_OVERAPPROXIMATION",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }

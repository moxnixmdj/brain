"""Independent semantic-graph consensus gate for M0A contextual proposals.

This module is deliberately not a semantic generator. Deterministic parsers and
white-box learned donors may propose bindings/relations/obligations. This gate:
- validates every proposal against exact source spans;
- counts independent mechanism groups, not duplicate route instances;
- admits a contextual decision only with predeclared independent support;
- fails closed on material alternative bindings;
- preserves unresolved decisions explicitly.

A donor's score or confidence is never semantic authority.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_M0A_SEMANTIC_GRAPH_CONSENSUS_V1"


def _span(raw:Any,n:int,label:str)->tuple[int,int]:
    if not isinstance(raw,(list,tuple)) or len(raw)!=2:
        raise ValueError(f"{label}: span must be [start,end]")
    s,e=raw
    if not isinstance(s,int) or isinstance(s,bool) or not isinstance(e,int) or isinstance(e,bool):
        raise ValueError(f"{label}: span indices must be integers")
    if not (0<=s<e<=n):
        raise ValueError(f"{label}: span out of bounds")
    return s,e


def _binding_key(row:Mapping[str,Any],n:int):
    mention=_span(row.get("mention_span"),n,"binding.mention")
    target=_span(row.get("target_span"),n,"binding.target")
    kind=str(row.get("kind") or "reference")
    return (mention,kind),target


def _relation_key(row:Mapping[str,Any],n:int):
    left=_span(row.get("left_span"),n,"relation.left")
    right=_span(row.get("right_span"),n,"relation.right")
    kind=str(row.get("kind") or "").strip()
    if not kind:
        raise ValueError("relation kind missing")
    return (kind,left,right)


def _obligation_key(row:Mapping[str,Any],n:int):
    subject=_span(row.get("subject_span"),n,"obligation.subject")
    predicate=_span(row.get("predicate_span"),n,"obligation.predicate")
    obj=None
    cond=None
    if row.get("object_span") is not None:
        obj=_span(row.get("object_span"),n,"obligation.object")
    if row.get("condition_span") is not None:
        cond=_span(row.get("condition_span"),n,"obligation.condition")
    modality=str(row.get("modality") or "").strip().lower()
    return (subject,predicate,obj,cond,modality)


def _groups(proposals, field, key_fn, n):
    support=defaultdict(set)
    provenance=defaultdict(list)
    for proposal in proposals:
        group=proposal["independence_group"]
        route=proposal["route_id"]
        for row in proposal.get(field,[]):
            key=key_fn(row,n)
            support[key].add(group)
            provenance[key].append(route)
    return support,provenance


def compile_consensus(
    source:str,
    proposals:Sequence[Mapping[str,Any]],
    *,
    min_independent_support:int=2,
)->dict[str,Any]:
    if not isinstance(source,str) or not source:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["SOURCE_EMPTY"]}
    if min_independent_support<2:
        raise ValueError("min_independent_support must be >=2")
    if not isinstance(proposals,Sequence) or isinstance(proposals,(str,bytes)):
        raise ValueError("proposals must be a sequence")

    clean=[]
    seen_routes=set()
    errors=[]
    for i,p in enumerate(proposals):
        if not isinstance(p,Mapping):
            errors.append(f"PROPOSAL_NOT_OBJECT:{i}"); continue
        route=str(p.get("route_id") or "").strip()
        group=str(p.get("independence_group") or "").strip()
        if not route or route in seen_routes:
            errors.append(f"ROUTE_ID_INVALID_OR_DUPLICATE:{i}:{route}"); continue
        if not group:
            errors.append(f"INDEPENDENCE_GROUP_MISSING:{route}"); continue
        seen_routes.add(route)
        row={
            "route_id":route,
            "independence_group":group,
            "bindings":list(p.get("bindings") or []),
            "relations":list(p.get("relations") or []),
            "obligations":list(p.get("obligations") or []),
        }
        # Validate every source-dependent claim before admitting the route.
        try:
            for x in row["bindings"]: _binding_key(x,len(source))
            for x in row["relations"]: _relation_key(x,len(source))
            for x in row["obligations"]: _obligation_key(x,len(source))
        except Exception as exc:
            errors.append(f"PROPOSAL_INVALID:{route}:{type(exc).__name__}:{exc}")
            continue
        clean.append(row)

    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors))}

    b_support,b_prov=_groups(clean,"bindings",_binding_key,len(source))
    r_support,r_prov=_groups(clean,"relations",_relation_key,len(source))
    o_support,o_prov=_groups(clean,"obligations",_obligation_key,len(source))

    # Binding alternatives are mutually exclusive for a mention+kind slot.
    alternatives=defaultdict(list)
    for (slot,target),groups in b_support.items():
        alternatives[slot].append((target,groups,b_prov[(slot,target)]))

    accepted_bindings=[]
    unresolved=[]
    ambiguity=[]
    for slot,alts in sorted(alternatives.items()):
        material=[a for a in alts if len(a[1])>=1]
        if len(material)>1:
            ambiguity.append({
                "mention_span":list(slot[0]),
                "kind":slot[1],
                "alternatives":[
                    {
                        "target_span":list(target),
                        "independent_groups":sorted(groups),
                        "routes":sorted(routes),
                    }
                    for target,groups,routes in material
                ],
            })
            continue
        target,groups,routes=material[0]
        if len(groups)>=min_independent_support:
            accepted_bindings.append({
                "mention_span":list(slot[0]),"kind":slot[1],
                "target_span":list(target),
                "independent_groups":sorted(groups),
                "routes":sorted(routes),
            })
        else:
            unresolved.append({
                "type":"binding","mention_span":list(slot[0]),"kind":slot[1],
                "candidate_target_span":list(target),
                "independent_support":len(groups),
                "required":min_independent_support,
            })

    def accepted_generic(support,prov,kind):
        accepted=[]
        missing=[]
        for key,groups in sorted(support.items(),key=lambda x:repr(x[0])):
            if len(groups)>=min_independent_support:
                accepted.append({
                    "key":key,
                    "independent_groups":sorted(groups),
                    "routes":sorted(prov[key]),
                })
            else:
                missing.append({
                    "type":kind,"key":key,
                    "independent_support":len(groups),
                    "required":min_independent_support,
                })
        return accepted,missing

    accepted_relations,miss_r=accepted_generic(r_support,r_prov,"relation")
    accepted_obligations,miss_o=accepted_generic(o_support,o_prov,"obligation")
    unresolved.extend(miss_r); unresolved.extend(miss_o)

    status="AMBIGUOUS" if ambiguity else ("CONSENSUS" if not unresolved else "PARTIAL")
    return {
        "schema":SCHEMA,
        "status":status,
        "accepted":{
            "bindings":accepted_bindings,
            "relations":accepted_relations,
            "obligations":accepted_obligations,
        },
        "ambiguity_witness":ambiguity,
        "unresolved":unresolved,
        "independence_groups":sorted({p["independence_group"] for p in clean}),
        "route_count":len(clean),
        "terminal_authority":False,
        "rule":"INDEPENDENT_MECHANISM_SUPPORT_AND_SOURCE_TRACEABILITY_REQUIRED__MODEL_CONFIDENCE_IS_NOT_AUTHORITY",
    }

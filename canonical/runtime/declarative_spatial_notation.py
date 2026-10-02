"""Safe declarative spatial-notation graph matcher.

Brain owns generic exact graph matching. A notation standard supplies JIT knowledge:
role predicates plus required spatial/topological relations. Upstream vision supplies
observed nodes and relation facts. No eval, regex hooks, weights, or heuristic ranking.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_DECLARATIVE_SPATIAL_NOTATION_V1"
_ALLOWED_PREDICATES={"kind","token","symbol","class"}
_ALLOWED_RELATIONS={
    "LEFT_OF","RIGHT_OF","ABOVE","BELOW","INSIDE","CONTAINS",
    "TOUCHES","CONNECTED_TO","ALIGNED_X","ALIGNED_Y","NEAR"
}

def _norm(v:Any)->str:
    return " ".join(str(v or "").split()).upper()

def validate_rule(rule:Mapping[str,Any])->list[str]:
    errors=[]
    rid=_norm(rule.get("id"))
    roles=rule.get("roles")
    rels=rule.get("relations",[])
    if not rid: errors.append("RULE_ID_MISSING")
    if not isinstance(roles,Mapping) or not roles:
        return errors+["ROLES_INVALID:"+rid]
    for role,pred in roles.items():
        if not _norm(role): errors.append("ROLE_ID_INVALID:"+rid)
        if not isinstance(pred,Mapping): errors.append("ROLE_PREDICATE_INVALID:"+rid+":"+str(role)); continue
        if not pred: errors.append("ROLE_PREDICATE_EMPTY:"+rid+":"+str(role))
        for k,v in pred.items():
            if k not in _ALLOWED_PREDICATES:
                errors.append("PREDICATE_KEY_UNSUPPORTED:"+rid+":"+str(k))
            if isinstance(v,(list,tuple)):
                if not v: errors.append("PREDICATE_VALUES_EMPTY:"+rid+":"+str(k))
            elif not isinstance(v,(str,int,float)):
                errors.append("PREDICATE_VALUE_INVALID:"+rid+":"+str(k))
    if not isinstance(rels,Sequence) or isinstance(rels,(str,bytes)):
        errors.append("RELATIONS_INVALID:"+rid)
    else:
        for i,e in enumerate(rels):
            if not isinstance(e,Mapping):
                errors.append(f"RELATION_NOT_OBJECT:{rid}:{i}"); continue
            a=_norm(e.get("from")); b=_norm(e.get("to")); typ=_norm(e.get("type"))
            role_ids={_norm(x) for x in roles}
            if a not in role_ids or b not in role_ids:
                errors.append(f"RELATION_UNKNOWN_ROLE:{rid}:{i}")
            if typ not in _ALLOWED_RELATIONS:
                errors.append(f"RELATION_TYPE_UNSUPPORTED:{rid}:{i}:{typ}")
    return sorted(set(errors))

def validate_grammar(rules:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(rules,Sequence) or isinstance(rules,(str,bytes)):
        raise ValueError("rules must be a sequence")
    errors=[]; ids=set()
    for r in rules:
        if not isinstance(r,Mapping): errors.append("RULE_NOT_OBJECT"); continue
        rid=_norm(r.get("id"))
        if rid in ids: errors.append("RULE_ID_DUPLICATE:"+rid)
        ids.add(rid)
        errors.extend(validate_rule(r))
    return {"schema":SCHEMA,"valid":not errors,"errors":sorted(set(errors))}

def _node_ok(node:Mapping[str,Any], pred:Mapping[str,Any])->bool:
    for k,expected in pred.items():
        actual=_norm(node.get(k))
        vals=expected if isinstance(expected,(list,tuple)) else [expected]
        if actual not in {_norm(v) for v in vals}:
            return False
    return True

def match(
    nodes:Sequence[Mapping[str,Any]],
    relations:Sequence[Mapping[str,Any]],
    rules:Sequence[Mapping[str,Any]],
    *,
    max_matches:int=2
)->dict[str,Any]:
    verdict=validate_grammar(rules)
    if not verdict["valid"]:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GRAMMAR_INVALID","details":verdict["errors"]}
    if max_matches<2: raise ValueError("max_matches must be >=2")
    by_id={}
    for i,n in enumerate(nodes):
        if not isinstance(n,Mapping):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":f"NODE_NOT_OBJECT:{i}"}
        nid=_norm(n.get("id"))
        if not nid or nid in by_id:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":f"BAD_OR_DUPLICATE_NODE_ID:{i}:{nid}"}
        by_id[nid]=n
    relset=set()
    for i,e in enumerate(relations):
        if not isinstance(e,Mapping):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":f"RELATION_NOT_OBJECT:{i}"}
        a=_norm(e.get("from")); b=_norm(e.get("to")); typ=_norm(e.get("type"))
        if a not in by_id or b not in by_id or typ not in _ALLOWED_RELATIONS:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":f"BAD_OBSERVED_RELATION:{i}"}
        relset.add((a,typ,b))

    matches=[]
    for rule in rules:
        roles={_norm(k):v for k,v in rule["roles"].items()}
        domains={}
        for role,pred in roles.items():
            domains[role]=sorted(nid for nid,n in by_id.items() if _node_ok(n,pred))
            if not domains[role]: break
        else:
            rels=[(_norm(e["from"]),_norm(e["type"]),_norm(e["to"])) for e in rule.get("relations",[])]
            order=sorted(roles,key=lambda r:(len(domains[r]),r))
            def consistent(assign):
                if len(assign.values())!=len(set(assign.values())): return False
                for a,t,b in rels:
                    if a in assign and b in assign and (assign[a],t,assign[b]) not in relset:
                        return False
                return True
            def dfs(k,assign):
                if len(matches)>=max_matches: return
                if k==len(order):
                    matches.append({"rule_id":rule["id"],"kind":rule.get("kind"),"roles":dict(assign)})
                    return
                role=order[k]
                for nid in domains[role]:
                    assign[role]=nid
                    if consistent(assign): dfs(k+1,assign)
                    assign.pop(role,None)
                    if len(matches)>=max_matches:return
            dfs(0,{})
        if len(matches)>=max_matches: break

    if not matches:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_RULE_MATCH","terminal_authority":False}
    if len(matches)>1:
        return {"schema":SCHEMA,"status":"AMBIGUOUS","matches":matches[:2],
                "next":"ACQUIRE_DISCRIMINATING_VISUAL_OR_STANDARD_EVIDENCE","terminal_authority":False}
    return {"schema":SCHEMA,"status":"PARSED","match":matches[0],
            "scope":"FORMAL_SPATIAL_NOTATION_EXPRESSIBLE_AS_FINITE_TYPED_RELATION_GRAPH",
            "terminal_authority":False}

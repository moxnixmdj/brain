"""Brain-owned normalized-rule to complete calculation-graph candidate.

This route begins *after* semantic extraction has produced normalized applicable-rule
candidates.  It must independently resolve applicability, dependency order, types,
dimensions, invariants, exclusions and edge-level acceptance consequences.  It does
not import the evaluator or hidden oracle.
"""
from __future__ import annotations
from math import isfinite
from typing import Any, Mapping

BEHAVIOR_ID = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
ORIGINS = {"formula", "constraint", "schema", "standard", "feature_callout"}
COND_OPS = {"always", "eq", "neq", "ge", "gt", "le", "lt", "in"}
OPS = {"identity","negate","add","sub","max","min","mul","div","eq","ge","gt","le","lt","all"}

class CandidateError(ValueError):
    pass

def _dim(v: Any) -> dict[str,int]:
    if v is None:
        return {}
    if not isinstance(v, Mapping):
        raise CandidateError("DIMENSION_NOT_MAPPING")
    out: dict[str,int] = {}
    for k,x in v.items():
        if not isinstance(k,str) or not k or not isinstance(x,int) or isinstance(x,bool):
            raise CandidateError("DIMENSION_INVALID")
        if x:
            out[k]=x
    return dict(sorted(out.items()))

def _dim_add(a: Mapping[str,int], b: Mapping[str,int], sign: int=1) -> dict[str,int]:
    out=dict(a)
    for k,v in b.items():
        out[k]=out.get(k,0)+sign*v
        if out[k]==0:
            del out[k]
    return dict(sorted(out.items()))

def _value_ok(value: Any, typ: str) -> bool:
    if typ=="number": return isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(float(value))
    if typ=="bool": return isinstance(value,bool)
    if typ=="string": return isinstance(value,str)
    return False

def _condition(cond: Mapping[str,Any] | None, branch: Mapping[str,Any]) -> bool:
    if cond is None:
        return True
    if not isinstance(cond,Mapping):
        raise CandidateError("CONDITION_INVALID")
    op=cond.get("op","always")
    if op not in COND_OPS:
        raise CandidateError("CONDITION_OP_INVALID")
    if op=="always": return True
    key=cond.get("key")
    if not isinstance(key,str) or key not in branch:
        raise CandidateError("CONDITION_KEY_INVALID")
    lhs=branch[key]; rhs=cond.get("value")
    if op=="eq": return lhs==rhs
    if op=="neq": return lhs!=rhs
    if op=="in": return isinstance(rhs,list) and lhs in rhs
    if isinstance(lhs,bool) or isinstance(rhs,bool) or not isinstance(lhs,(int,float)) or not isinstance(rhs,(int,float)):
        raise CandidateError("CONDITION_ORDER_TYPE_INVALID")
    if op=="ge": return lhs>=rhs
    if op=="gt": return lhs>rhs
    if op=="le": return lhs<=rhs
    if op=="lt": return lhs<rhs
    raise CandidateError("CONDITION_UNREACHABLE")

def _derive(op: str, args: list[dict[str,Any]]) -> tuple[str,dict[str,int]]:
    if op not in OPS or not args:
        raise CandidateError("OP_OR_ARGUMENTS_INVALID")
    types=[x["type"] for x in args]; dims=[x["dimension"] for x in args]
    if op in {"identity","negate"}:
        if len(args)!=1 or (op=="negate" and types[0]!="number"):
            raise CandidateError("UNARY_SIGNATURE_INVALID")
        return types[0],dict(dims[0])
    if op in {"add","sub","max","min"}:
        if len(args)<2 or any(t!="number" for t in types) or any(d!=dims[0] for d in dims[1:]):
            raise CandidateError("SAME_DIMENSION_SIGNATURE_INVALID")
        return "number",dict(dims[0])
    if op=="mul":
        if len(args)!=2 or any(t!="number" for t in types): raise CandidateError("MUL_SIGNATURE_INVALID")
        return "number",_dim_add(dims[0],dims[1])
    if op=="div":
        if len(args)!=2 or any(t!="number" for t in types): raise CandidateError("DIV_SIGNATURE_INVALID")
        return "number",_dim_add(dims[0],dims[1],-1)
    if op in {"eq","ge","gt","le","lt"}:
        if len(args)!=2 or types[0]!=types[1] or dims[0]!=dims[1]: raise CandidateError("COMPARE_SIGNATURE_INVALID")
        if op!="eq" and types[0]!="number": raise CandidateError("ORDER_COMPARE_NONNUMERIC")
        return "bool",{}
    if op=="all":
        if len(args)<1 or any(t!="bool" for t in types): raise CandidateError("ALL_SIGNATURE_INVALID")
        return "bool",{}
    raise CandidateError("OP_UNREACHABLE")

def _invariant(inv: Mapping[str,Any], node: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(inv,Mapping): raise CandidateError("INVARIANT_INVALID")
    kind=inv.get("kind")
    if kind not in {"nonzero","nonnegative","positive","finite","member"}: raise CandidateError("INVARIANT_KIND_INVALID")
    if kind=="member":
        vals=inv.get("values")
        if not isinstance(vals,list) or not vals: raise CandidateError("MEMBER_VALUES_INVALID")
        return {"node":node["id"],"kind":kind,"values":vals}
    if node["type"]!="number": raise CandidateError("NUMERIC_INVARIANT_ON_NONNUMERIC")
    return {"node":node["id"],"kind":kind}

def solve(public: Mapping[str,Any]) -> dict[str,Any]:
    if public.get("behavior_id")!=BEHAVIOR_ID: raise CandidateError("BEHAVIOR_ID_MISMATCH")
    task=public.get("task")
    if not isinstance(task,Mapping): raise CandidateError("TASK_INVALID")
    branch=task.get("branch_values")
    inputs=task.get("inputs"); rules=task.get("rules"); required_outputs=task.get("required_outputs")
    if not isinstance(branch,Mapping) or not isinstance(inputs,Mapping) or not isinstance(rules,list) or not isinstance(required_outputs,list):
        raise CandidateError("TASK_FIELDS_INVALID")

    nodes: dict[str,dict[str,Any]]={}
    for nid,row in inputs.items():
        if not isinstance(nid,str) or not nid or not isinstance(row,Mapping): raise CandidateError("INPUT_INVALID")
        typ=row.get("type"); value=row.get("value"); dim=_dim(row.get("dimension",{}))
        if typ not in {"number","bool","string"} or not _value_ok(value,typ): raise CandidateError("INPUT_TYPE_INVALID")
        if typ!="number" and dim: raise CandidateError("NONNUMERIC_DIMENSION")
        nodes[nid]={"id":nid,"kind":"input","type":typ,"dimension":dim}

    pending: dict[str,Mapping[str,Any]]={}
    exclusions=[]
    for rule in rules:
        if not isinstance(rule,Mapping): raise CandidateError("RULE_INVALID")
        rid=rule.get("id")
        if not isinstance(rid,str) or not rid or rid in pending: raise CandidateError("RULE_ID_INVALID")
        if rule.get("origin") not in ORIGINS: raise CandidateError("RULE_ORIGIN_INVALID")
        if rule.get("op") not in OPS: raise CandidateError("RULE_OP_INVALID")
        active=_condition(rule.get("condition"),branch)
        if not active:
            exclusions.append({"rule_id":rid,"reason":"CONDITION_FALSE","condition":dict(rule.get("condition") or {"op":"always"})})
            continue
        pending[rid]=rule

    edges=[]; invariants=[]; checks=[]; applied=[]
    while pending:
        progressed=False
        for rid,rule in list(pending.items()):
            ins=rule.get("inputs"); out=rule.get("output")
            if not isinstance(ins,list) or not ins or any(not isinstance(x,str) or not x for x in ins) or not isinstance(out,str) or not out:
                raise CandidateError("RULE_IO_INVALID")
            if out in nodes: raise CandidateError("OUTPUT_DUPLICATE")
            if any(x not in nodes for x in ins):
                continue
            args=[nodes[x] for x in ins]
            typ,dim=_derive(str(rule["op"]),args)
            declared_type=rule.get("output_type"); declared_dim=_dim(rule.get("output_dimension",{}))
            if declared_type!=typ or declared_dim!=dim: raise CandidateError("DECLARED_METADATA_MISMATCH")
            node={"id":out,"kind":"derived","type":typ,"dimension":dim,"rule_id":rid,"origin":rule["origin"],"op":rule["op"]}
            nodes[out]=node
            for src in ins:
                edges.append({"source":src,"target":out,"rule_id":rid,"origin":rule["origin"],"op":rule["op"]})
            if "invariant" in rule:
                invariants.append(_invariant(rule["invariant"],node))
            checks.append({"rule_id":rid,"target":out,"dependency_count":len(ins),"check":"EDGE_CONSEQUENCE"})
            applied.append(rid); del pending[rid]; progressed=True
        if not progressed:
            raise CandidateError("UNRESOLVED_DEPENDENCY_OR_CYCLE")

    req=[]
    for x in required_outputs:
        if not isinstance(x,str) or x not in nodes: raise CandidateError("REQUIRED_OUTPUT_UNTRACED")
        req.append(x)
    return {
        "nodes":sorted(nodes.values(),key=lambda x:x["id"]),
        "edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),
        "exclusions":sorted(exclusions,key=lambda x:x["rule_id"]),
        "invariants":sorted(invariants,key=lambda x:(x["node"],x["kind"])),
        "acceptance_checks":sorted(checks,key=lambda x:x["rule_id"]),
        "required_outputs":sorted(req),
        "applied_rule_ids":sorted(applied),
    }

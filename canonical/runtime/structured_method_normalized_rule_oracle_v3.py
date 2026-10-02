"""Independent structural oracle for normalized structured-method graphs.

This evaluator does not import the Brain graph compiler. It checks the frozen
STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001 contract at its declared boundary:
requirements + normalized applicable rules + input schema are already given.

Operator *meaning* is upstream normalized-rule authority. This oracle checks graph
materialization, not arbitrary hidden semantic extraction/evaluation.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_STRUCTURED_METHOD_NORMALIZED_RULE_ORACLE_V3"
SOURCE_KINDS={"formula","constraint","schema","standard","feature_callout"}

class OracleError(ValueError): pass

def _token(v:Any,label:str)->str:
    if not isinstance(v,str) or not v.strip(): raise OracleError(label+"_INVALID")
    return v.strip()

def _meta(row:Mapping[str,Any],label:str)->dict[str,str]:
    return {"type":_token(row.get("type"),label+"_TYPE"),"dimension":_token(row.get("dimension"),label+"_DIMENSION")}

def expected(public:Mapping[str,Any])->dict[str,Any]:
    if public.get("behavior_id")!="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        raise OracleError("BEHAVIOR_ID")
    task=public.get("task")
    if not isinstance(task,Mapping): raise OracleError("TASK")
    inputs=task.get("inputs"); reqs=task.get("requirements"); rules=task.get("normalized_rules"); outputs=task.get("required_outputs")
    if not all(isinstance(x,list) for x in (inputs,reqs,rules,outputs)): raise OracleError("COLLECTIONS")

    nodes={}
    for i,row in enumerate(inputs):
        if not isinstance(row,Mapping): raise OracleError("INPUT")
        nid=_token(row.get("id"),f"INPUT_{i}")
        if nid in nodes: raise OracleError("DUPLICATE_NODE")
        nodes[nid]={"id":nid,"kind":"input",**_meta(row,"INPUT_"+nid)}

    applicable={}; exclusions=[]; seen=set()
    for row in reqs:
        if not isinstance(row,Mapping): raise OracleError("REQ")
        rid=_token(row.get("id"),"REQ_ID")
        if rid in seen: raise OracleError("DUPLICATE_REQ")
        seen.add(rid)
        kind=_token(row.get("source_kind"),"REQ_KIND")
        if kind not in SOURCE_KINDS: raise OracleError("REQ_KIND")
        status=row.get("status","applicable")
        if status=="applicable": applicable[rid]=kind
        elif status=="excluded":
            exclusions.append({"requirement_id":rid,"source_kind":kind,"reason":_token(row.get("exclusion_reason"),"EXCLUSION_REASON")})
        else: raise OracleError("REQ_STATUS")

    pending={}
    for row in rules:
        if not isinstance(row,Mapping): raise OracleError("RULE")
        rid=_token(row.get("id"),"RULE_ID")
        if rid in pending: raise OracleError("DUPLICATE_RULE")
        pending[rid]=row

    graph=[]; edges=[]; consumed={r:[] for r in applicable}; acceptance=[]
    while pending:
        progressed=False
        for rid,row in list(pending.items()):
            ins=row.get("inputs")
            if not isinstance(ins,list) or any(not isinstance(x,str) or not x for x in ins): raise OracleError("RULE_INPUTS")
            if any(x not in nodes for x in ins): continue
            out=_token(row.get("output"),"OUTPUT")
            if out in nodes: raise OracleError("DUPLICATE_OUTPUT")
            op=_token(row.get("operator"),"OPERATOR")
            contracts=row.get("input_contracts")
            if not isinstance(contracts,list) or len(contracts)!=len(ins): raise OracleError("INPUT_CONTRACTS")
            for pos,(src,contract) in enumerate(zip(ins,contracts)):
                if not isinstance(contract,Mapping): raise OracleError("INPUT_CONTRACT")
                if nodes[src]["type"]!=_token(contract.get("type"),f"TYPE_{pos}") or nodes[src]["dimension"]!=_token(contract.get("dimension"),f"DIM_{pos}"):
                    raise OracleError("TYPE_DIMENSION_MISMATCH")
            outmeta=_meta(row,"OUTPUT_"+out)
            consumes=row.get("consumes_requirements",[])
            if not isinstance(consumes,list) or any(x not in applicable for x in consumes): raise OracleError("CONSUMES")
            for req in consumes: consumed[req].append(rid)
            inv=row.get("invariants",[])
            if not isinstance(inv,list) or any(not isinstance(x,Mapping) for x in inv): raise OracleError("INVARIANTS")
            invrows=[{"kind":_token(x.get("kind"),"INV_KIND"),"statement":_token(x.get("statement"),"INV_STATEMENT")} for x in inv]
            nodes[out]={"id":out,"kind":"derived",**outmeta}
            graph.append({"rule_id":rid,"operator":op,"inputs":list(ins),"output":out,"output_type":outmeta["type"],"output_dimension":outmeta["dimension"],"consumes_requirements":sorted(consumes),"invariants":invrows})
            for src in ins: edges.append({"source":src,"target":out,"rule_id":rid})
            # These are independent structural consequences derived from source input,
            # not copied from candidate output.
            acceptance.append({"rule_id":rid,"checks":[
                "ALL_INPUT_EDGES_PRESENT",
                "DECLARED_INPUT_TYPE_DIMENSION_CONTRACTS_HOLD",
                "OUTPUT_TYPE_DIMENSION_DECLARATION_PRESERVED",
                "REQUIREMENT_LINEAGE_PRESERVED",
                "DECLARED_INVARIANTS_PRESERVED",
                "EDGE_DELETION_OR_REWIRE_MUST_BE_DETECTABLE",
            ]})
            del pending[rid]; progressed=True
        if not progressed: raise OracleError("UNRESOLVED_DEPENDENCY_OR_CYCLE")

    if any(not xs for xs in consumed.values()): raise OracleError("UNCONSUMED_REQUIREMENT")
    if any(not isinstance(x,str) or x not in nodes for x in outputs): raise OracleError("UNTRACED_OUTPUT")

    return {
      "nodes":sorted(nodes.values(),key=lambda x:x["id"]),
      "rules":sorted(graph,key=lambda x:x["rule_id"]),
      "edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),
      "requirement_lineage":[{"requirement_id":r,"source_kind":applicable[r],"consumer_rule_ids":sorted(consumed[r])} for r in sorted(applicable)],
      "justified_exclusions":sorted(exclusions,key=lambda x:x["requirement_id"]),
      "required_outputs":sorted(outputs),
      "acceptance_checks":sorted(acceptance,key=lambda x:x["rule_id"]),
    }

def score(public:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping) or candidate.get("status")!="COMPILED":
        return {"pass":False,"reason":"NOT_COMPILED"}
    try: exp=expected(public)
    except Exception as exc: return {"pass":False,"reason":"ORACLE_INVALID:"+type(exc).__name__+":"+str(exc)}
    for key,value in exp.items():
        if candidate.get(key)!=value: return {"pass":False,"reason":"MISMATCH:"+key}
    return {"pass":True,"reason":"PASS"}

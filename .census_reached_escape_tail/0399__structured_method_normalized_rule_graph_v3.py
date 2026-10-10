"""Generic normalized-rule graph compiler for STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001.

Contract boundary:
- rule extraction and semantic normalization are upstream;
- each normalized rule explicitly declares its inputs, output, input/output type+dimension
  contracts, source requirements, invariants, and operator identity;
- this compiler owns complete DAG materialization, lineage, exclusion accounting,
  type/dimension contract checking, cycle detection, and edge-level acceptance plans.

It deliberately does NOT hard-code a finite vocabulary of mathematical operators.
Unknown operator identity is acceptable only because its semantic signature is part of
the normalized rule input. This avoids falsely equating the whole contract with a small
opcode list.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_STRUCTURED_METHOD_NORMALIZED_RULE_GRAPH_V3"
SOURCE_KINDS={"formula","constraint","schema","standard","feature_callout"}

class GraphError(ValueError):
    pass

def _token(v:Any,label:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise GraphError(label+"_INVALID")
    return v.strip()

def _meta(row:Mapping[str,Any],label:str)->dict[str,str]:
    typ=_token(row.get("type"),label+"_TYPE")
    dim=_token(row.get("dimension"),label+"_DIMENSION")
    return {"type":typ,"dimension":dim}

def compile_graph(public:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(public,Mapping):
            raise GraphError("PUBLIC_NOT_OBJECT")
        if public.get("behavior_id")!="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
            raise GraphError("BEHAVIOR_ID_MISMATCH")
        task=public.get("task")
        if not isinstance(task,Mapping):
            raise GraphError("TASK_INVALID")

        raw_inputs=task.get("inputs")
        raw_reqs=task.get("requirements")
        raw_rules=task.get("normalized_rules")
        required_outputs=task.get("required_outputs")
        if not isinstance(raw_inputs,list) or not isinstance(raw_reqs,list) or not isinstance(raw_rules,list) or not isinstance(required_outputs,list):
            raise GraphError("TASK_COLLECTIONS_INVALID")

        nodes:dict[str,dict[str,Any]]={}
        for i,row in enumerate(raw_inputs):
            if not isinstance(row,Mapping):
                raise GraphError(f"INPUT_{i}_NOT_OBJECT")
            nid=_token(row.get("id"),f"INPUT_{i}_ID")
            if nid in nodes:
                raise GraphError("DUPLICATE_NODE:"+nid)
            m=_meta(row,"INPUT_"+nid)
            nodes[nid]={"id":nid,"kind":"input",**m}

        applicable:dict[str,str]={}
        exclusions:list[dict[str,Any]]=[]
        seen_req:set[str]=set()
        for i,row in enumerate(raw_reqs):
            if not isinstance(row,Mapping):
                raise GraphError(f"REQ_{i}_NOT_OBJECT")
            rid=_token(row.get("id"),f"REQ_{i}_ID")
            if rid in seen_req:
                raise GraphError("DUPLICATE_REQUIREMENT:"+rid)
            seen_req.add(rid)
            kind=_token(row.get("source_kind"),"REQ_SOURCE_KIND")
            if kind not in SOURCE_KINDS:
                raise GraphError("REQ_SOURCE_KIND_UNSUPPORTED:"+kind)
            status=row.get("status","applicable")
            if status=="applicable":
                applicable[rid]=kind
            elif status=="excluded":
                reason=_token(row.get("exclusion_reason"),"EXCLUSION_REASON")
                exclusions.append({"requirement_id":rid,"source_kind":kind,"reason":reason})
            else:
                raise GraphError("REQ_STATUS_INVALID:"+rid)

        pending:dict[str,Mapping[str,Any]]={}
        for i,row in enumerate(raw_rules):
            if not isinstance(row,Mapping):
                raise GraphError(f"RULE_{i}_NOT_OBJECT")
            rid=_token(row.get("id"),f"RULE_{i}_ID")
            if rid in pending:
                raise GraphError("DUPLICATE_RULE:"+rid)
            pending[rid]=row

        graph_rows=[]; edges=[]; acceptance=[]; consumed={rid:[] for rid in applicable}
        while pending:
            progressed=False
            for rid,row in list(pending.items()):
                ins=row.get("inputs")
                if not isinstance(ins,list) or any(not isinstance(x,str) or not x for x in ins):
                    raise GraphError("RULE_INPUTS_INVALID:"+rid)
                if any(x not in nodes for x in ins):
                    continue
                out=_token(row.get("output"),"RULE_OUTPUT")
                if out in nodes:
                    raise GraphError("DUPLICATE_OUTPUT:"+out)
                operator=_token(row.get("operator"),"RULE_OPERATOR")
                expected=row.get("input_contracts")
                if not isinstance(expected,list) or len(expected)!=len(ins):
                    raise GraphError("INPUT_CONTRACT_ARITY:"+rid)
                for pos,(src,contract) in enumerate(zip(ins,expected)):
                    if not isinstance(contract,Mapping):
                        raise GraphError("INPUT_CONTRACT_INVALID:"+rid)
                    m=_meta(contract,f"RULE_{rid}_INPUT_{pos}")
                    if nodes[src]["type"]!=m["type"] or nodes[src]["dimension"]!=m["dimension"]:
                        raise GraphError("INPUT_TYPE_DIMENSION_MISMATCH:"+rid+":"+src)
                outmeta=_meta(row,"RULE_"+rid+"_OUTPUT")
                reqs=row.get("consumes_requirements",[])
                if not isinstance(reqs,list) or any(not isinstance(x,str) or not x for x in reqs):
                    raise GraphError("RULE_REQUIREMENTS_INVALID:"+rid)
                if any(x not in applicable for x in reqs):
                    raise GraphError("RULE_CONSUMES_UNKNOWN_OR_EXCLUDED_REQUIREMENT:"+rid)
                for req in reqs:
                    consumed[req].append(rid)
                inv=row.get("invariants",[])
                if not isinstance(inv,list) or any(not isinstance(x,Mapping) for x in inv):
                    raise GraphError("RULE_INVARIANTS_INVALID:"+rid)
                inv_rows=[]
                for j,x in enumerate(inv):
                    inv_rows.append({
                        "kind":_token(x.get("kind"),f"INV_{rid}_{j}_KIND"),
                        "statement":_token(x.get("statement"),f"INV_{rid}_{j}_STATEMENT"),
                    })
                nodes[out]={"id":out,"kind":"derived",**outmeta}
                graph_rows.append({
                    "rule_id":rid,"operator":operator,"inputs":list(ins),"output":out,
                    "output_type":outmeta["type"],"output_dimension":outmeta["dimension"],
                    "consumes_requirements":sorted(reqs),"invariants":inv_rows
                })
                for src in ins:
                    edges.append({"source":src,"target":out,"rule_id":rid})
                acceptance.append({
                    "rule_id":rid,
                    "checks":[
                        "ALL_INPUT_EDGES_PRESENT",
                        "DECLARED_INPUT_TYPE_DIMENSION_CONTRACTS_HOLD",
                        "OUTPUT_TYPE_DIMENSION_DECLARATION_PRESERVED",
                        "REQUIREMENT_LINEAGE_PRESERVED",
                        "DECLARED_INVARIANTS_PRESERVED",
                        "EDGE_DELETION_OR_REWIRE_MUST_BE_DETECTABLE"
                    ]
                })
                del pending[rid]; progressed=True
            if not progressed:
                raise GraphError("UNRESOLVED_DEPENDENCY_OR_CYCLE:"+",".join(sorted(pending)))

        missing=sorted(r for r,v in consumed.items() if not v)
        if missing:
            raise GraphError("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER:"+",".join(missing))
        if any(not isinstance(x,str) or x not in nodes for x in required_outputs):
            raise GraphError("REQUIRED_OUTPUT_UNTRACED")
        lineage=[{"requirement_id":r,"source_kind":applicable[r],"consumer_rule_ids":sorted(consumed[r])} for r in sorted(applicable)]
        return {
            "schema":SCHEMA,"status":"COMPILED",
            "nodes":sorted(nodes.values(),key=lambda x:x["id"]),
            "rules":sorted(graph_rows,key=lambda x:x["rule_id"]),
            "edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),
            "requirement_lineage":lineage,
            "justified_exclusions":sorted(exclusions,key=lambda x:x["requirement_id"]),
            "required_outputs":sorted(required_outputs),
            "acceptance_checks":sorted(acceptance,key=lambda x:x["rule_id"]),
            "operator_semantics_authority":"UPSTREAM_NORMALIZED_RULE_CONTRACT__NOT_INFERRED_HERE",
            "terminal_authority":False,
            "capability_credit_delta":0
        }
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc),"terminal_authority":False,"capability_credit_delta":0}

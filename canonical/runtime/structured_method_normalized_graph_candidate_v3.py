"""Generic normalized-rule graph compiler for STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001.

This route begins after rule extraction.  It intentionally does not interpret raw
language or invent operator semantics.  Each normalized rule supplies an explicit
machine-readable signature; this compiler validates applicability disposition,
dependency closure, type/dimension compatibility, requirement lineage, invariant
bindings, required outputs and edge-level acceptance bindings for arbitrary finite
normalized operator vocabularies.
"""
from __future__ import annotations
from typing import Any, Mapping

BEHAVIOR_ID="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
SOURCE_KINDS={"formula","constraint","schema","standard","feature_callout"}
TYPES={"number","boolean","string","enum"}

class CompileError(ValueError):
    pass

def _dim(value: Any) -> dict[str,int]:
    if value is None:
        return {}
    if not isinstance(value,Mapping):
        raise CompileError("DIMENSION_NOT_MAPPING")
    out={}
    for k,v in value.items():
        if not isinstance(k,str) or not k or not isinstance(v,int) or isinstance(v,bool):
            raise CompileError("DIMENSION_INVALID")
        if v:
            out[k]=v
    return dict(sorted(out.items()))

def _meta(row: Mapping[str,Any], prefix: str) -> dict[str,Any]:
    typ=row.get("type")
    if typ not in TYPES:
        raise CompileError(prefix+"_TYPE_INVALID")
    dim=_dim(row.get("dimension",{}))
    if typ!="number" and dim:
        raise CompileError(prefix+"_NONNUMERIC_DIMENSION")
    return {"type":typ,"dimension":dim}

def _reqs(rows: Any) -> tuple[dict[str,dict[str,Any]],list[dict[str,Any]]]:
    if not isinstance(rows,list) or not rows:
        raise CompileError("REQUIREMENTS_REQUIRED")
    applicable={}
    exclusions=[]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise CompileError(f"REQUIREMENT_INVALID:{i}")
        rid=row.get("id"); source=row.get("source_kind"); disposition=row.get("disposition")
        if not isinstance(rid,str) or not rid or rid in seen:
            raise CompileError("REQUIREMENT_ID_INVALID")
        seen.add(rid)
        if source not in SOURCE_KINDS:
            raise CompileError("REQUIREMENT_SOURCE_KIND_INVALID:"+rid)
        if disposition=="APPLICABLE":
            applicable[rid]={"source_kind":source}
        elif disposition=="EXCLUDED":
            reason=row.get("exclusion_reason")
            if not isinstance(reason,str) or not reason.strip():
                raise CompileError("EXCLUSION_REASON_REQUIRED:"+rid)
            exclusions.append({"requirement_id":rid,"source_kind":source,"reason":reason.strip()})
        else:
            raise CompileError("REQUIREMENT_DISPOSITION_INVALID:"+rid)
    return applicable,sorted(exclusions,key=lambda x:x["requirement_id"])

def _signature(rule: Mapping[str,Any], dep_nodes: list[Mapping[str,Any]]) -> dict[str,Any]:
    sig=rule.get("signature")
    if not isinstance(sig,Mapping):
        raise CompileError("RULE_SIGNATURE_REQUIRED:"+str(rule.get("id")))
    ins=sig.get("inputs")
    if not isinstance(ins,list) or len(ins)!=len(dep_nodes):
        raise CompileError("RULE_SIGNATURE_ARITY_MISMATCH:"+str(rule.get("id")))
    normalized=[]
    for i,(decl,actual) in enumerate(zip(ins,dep_nodes)):
        if not isinstance(decl,Mapping):
            raise CompileError("RULE_INPUT_SIGNATURE_INVALID")
        dm=_meta(decl,"RULE_INPUT_SIGNATURE")
        if dm["type"]!=actual["type"] or dm["dimension"]!=actual["dimension"]:
            raise CompileError("RULE_INPUT_SIGNATURE_MISMATCH:"+str(rule.get("id"))+f":{i}")
        normalized.append(dm)
    out=sig.get("output")
    if not isinstance(out,Mapping):
        raise CompileError("RULE_OUTPUT_SIGNATURE_REQUIRED:"+str(rule.get("id")))
    om=_meta(out,"RULE_OUTPUT_SIGNATURE")
    return {"inputs":normalized,"output":om}

def compile_graph(public: Mapping[str,Any]) -> dict[str,Any]:
    if public.get("behavior_id")!=BEHAVIOR_ID:
        raise CompileError("BEHAVIOR_ID_MISMATCH")
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise CompileError("TASK_REQUIRED")
    inputs=task.get("inputs"); requirements=task.get("requirements")
    rules=task.get("normalized_rules"); invariants=task.get("invariants",[])
    required_outputs=task.get("required_outputs")
    if not isinstance(inputs,Mapping) or not inputs:
        raise CompileError("INPUTS_REQUIRED")
    if not isinstance(rules,list) or not rules:
        raise CompileError("NORMALIZED_RULES_REQUIRED")
    if not isinstance(invariants,list):
        raise CompileError("INVARIANTS_NOT_LIST")
    if not isinstance(required_outputs,list) or not required_outputs:
        raise CompileError("REQUIRED_OUTPUTS_REQUIRED")

    applicable,exclusions=_reqs(requirements)
    nodes={}
    for nid,row in inputs.items():
        if not isinstance(nid,str) or not nid or not isinstance(row,Mapping) or nid in nodes:
            raise CompileError("INPUT_DECLARATION_INVALID")
        m=_meta(row,"INPUT")
        nodes[nid]={"id":nid,"kind":"input",**m}

    pending={}
    for row in rules:
        if not isinstance(row,Mapping):
            raise CompileError("RULE_INVALID")
        rid=row.get("id"); out=row.get("output"); op=row.get("operator"); origin=row.get("origin")
        deps=row.get("dependencies"); consumes=row.get("consumes_requirements")
        if not isinstance(rid,str) or not rid or rid in pending:
            raise CompileError("RULE_ID_INVALID")
        if not isinstance(out,str) or not out or out in nodes:
            raise CompileError("RULE_OUTPUT_INVALID:"+rid)
        if not isinstance(op,str) or not op.strip():
            raise CompileError("RULE_OPERATOR_INVALID:"+rid)
        if origin not in SOURCE_KINDS:
            raise CompileError("RULE_ORIGIN_INVALID:"+rid)
        if not isinstance(deps,list) or not deps or not all(isinstance(x,str) and x for x in deps):
            raise CompileError("RULE_DEPENDENCIES_INVALID:"+rid)
        if len(deps)!=len(set(deps)):
            raise CompileError("RULE_DEPENDENCIES_DUPLICATE:"+rid)
        if not isinstance(consumes,list) or not consumes or not all(isinstance(x,str) and x for x in consumes):
            raise CompileError("RULE_REQUIREMENTS_INVALID:"+rid)
        if len(consumes)!=len(set(consumes)):
            raise CompileError("RULE_REQUIREMENTS_DUPLICATE:"+rid)
        for req in consumes:
            if req not in applicable:
                raise CompileError("RULE_CONSUMES_NONAPPLICABLE_REQUIREMENT:"+req)
        pending[rid]=dict(row)

    edges=[]; lineage=[]; acceptance=[]; derived_ids=set()
    consumers={rid:[] for rid in applicable}
    while pending:
        progressed=False
        for rid,row in list(pending.items()):
            deps=list(row["dependencies"])
            if any(d not in nodes for d in deps):
                continue
            out=row["output"]
            if out in nodes or out in derived_ids:
                raise CompileError("OUTPUT_DUPLICATE:"+out)
            sig=_signature(row,[nodes[d] for d in deps])
            om=sig["output"]
            node={
                "id":out,"kind":"derived","rule_id":rid,"operator":row["operator"],
                "origin":row["origin"],"type":om["type"],"dimension":om["dimension"]
            }
            nodes[out]=node; derived_ids.add(out)
            for dep in deps:
                edge={"source":dep,"target":out,"rule_id":rid}
                edges.append(edge)
                acceptance.append({
                    "edge_id":f"{rid}:{dep}->{out}",
                    "source":dep,"target":out,"rule_id":rid,
                    "check":"INDEPENDENT_EDGE_CONSEQUENCE_REQUIRED"
                })
            for req in row["consumes_requirements"]:
                consumers[req].append(rid)
                lineage.append({"requirement_id":req,"consumer_rule_id":rid,"output":out})
            del pending[rid]; progressed=True
        if not progressed:
            unresolved=sorted(pending)
            raise CompileError("UNRESOLVED_DEPENDENCY_OR_CYCLE:"+",".join(unresolved))

    missing=sorted(k for k,v in consumers.items() if not v)
    if missing:
        raise CompileError("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER:"+",".join(missing))

    inv_out=[]
    seen_inv=set()
    for i,inv in enumerate(invariants):
        if not isinstance(inv,Mapping):
            raise CompileError(f"INVARIANT_INVALID:{i}")
        iid=inv.get("id"); target=inv.get("target"); predicate=inv.get("predicate")
        if not isinstance(iid,str) or not iid or iid in seen_inv:
            raise CompileError("INVARIANT_ID_INVALID")
        if not isinstance(target,str) or target not in nodes:
            raise CompileError("INVARIANT_TARGET_INVALID:"+str(iid))
        if not isinstance(predicate,str) or not predicate.strip():
            raise CompileError("INVARIANT_PREDICATE_INVALID:"+str(iid))
        expected=inv.get("target_signature")
        if not isinstance(expected,Mapping):
            raise CompileError("INVARIANT_TARGET_SIGNATURE_REQUIRED:"+iid)
        em=_meta(expected,"INVARIANT_TARGET_SIGNATURE")
        actual=nodes[target]
        if em["type"]!=actual["type"] or em["dimension"]!=actual["dimension"]:
            raise CompileError("INVARIANT_TARGET_SIGNATURE_MISMATCH:"+iid)
        seen_inv.add(iid)
        inv_out.append({"id":iid,"target":target,"predicate":predicate.strip(),"target_type":actual["type"],"target_dimension":actual["dimension"]})

    required=[]
    for out in required_outputs:
        if not isinstance(out,str) or out not in nodes:
            raise CompileError("REQUIRED_OUTPUT_UNTRACED:"+str(out))
        required.append(out)

    return {
        "schema":"PROJECT_BRAIN_STRUCTURED_METHOD_NORMALIZED_GRAPH_V3",
        "nodes":sorted(nodes.values(),key=lambda x:x["id"]),
        "edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),
        "requirement_lineage":sorted(lineage,key=lambda x:(x["requirement_id"],x["consumer_rule_id"])),
        "exclusions":exclusions,
        "invariants":sorted(inv_out,key=lambda x:x["id"]),
        "acceptance_edge_bindings":sorted(acceptance,key=lambda x:x["edge_id"]),
        "required_outputs":sorted(required),
        "applied_rule_ids":sorted(derived_ids and [x["rule_id"] for x in nodes.values() if x.get("kind")=="derived"] or []),
    }

def solve(public: Mapping[str,Any]) -> dict[str,Any]:
    try:
        return {"status":"OK","graph":compile_graph(public)}
    except CompileError as exc:
        return {"status":"FAIL_CLOSED","reason":str(exc)}

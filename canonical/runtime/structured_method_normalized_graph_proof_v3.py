"""Independent hidden-oracle proof population for generic normalized structured-method graphs v3."""
from __future__ import annotations
import copy
import random
from typing import Any, Mapping

BEHAVIOR_ID="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
SOURCE_KINDS=("formula","constraint","schema","standard","feature_callout")
TYPES=("number","boolean","string","enum")

def _dim_for(typ:str,rng:random.Random)->dict[str,int]:
    if typ!="number":
        return {}
    choices=[{},{"L":1},{"T":-1},{"M":1},{"L":2,"T":-1}]
    return dict(rng.choice(choices))

def _sig(meta:Mapping[str,Any])->dict[str,Any]:
    return {"type":meta["type"],"dimension":dict(meta["dimension"])}

def generate_case(seed:int,rule_count:int|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED")
    rng=random.Random(seed)
    n=rule_count if rule_count is not None else rng.randint(4,18)
    if not isinstance(n,int) or n<1 or n>64:
        raise ValueError("RULE_COUNT")
    inputs={}
    node_meta={}
    for i in range(rng.randint(2,6)):
        typ=rng.choice(TYPES); nid=f"in{i}"
        meta={"type":typ,"dimension":_dim_for(typ,rng)}
        inputs[nid]=copy.deepcopy(meta); node_meta[nid]=meta

    requirements=[]; applicable_ids=[]; exclusions=[]
    for i in range(n+rng.randint(1,4)):
        rid=f"req{i}"; source=SOURCE_KINDS[i%len(SOURCE_KINDS)]
        if i<n:
            requirements.append({"id":rid,"source_kind":source,"disposition":"APPLICABLE"})
            applicable_ids.append(rid)
        else:
            reason=f"NORMALIZED_EXCLUSION_{seed}_{i}"
            requirements.append({"id":rid,"source_kind":source,"disposition":"EXCLUDED","exclusion_reason":reason})
            exclusions.append({"requirement_id":rid,"source_kind":source,"reason":reason})

    rules=[]; edges=[]; lineage=[]; acceptance=[]; derived_nodes=[]
    all_ids=list(node_meta)
    for i in range(n):
        rid=f"rule{i}"; out=f"v{i}"
        dep_count=rng.randint(1,min(3,len(all_ids)))
        deps=rng.sample(all_ids,dep_count)
        out_type=rng.choice(TYPES); out_meta={"type":out_type,"dimension":_dim_for(out_type,rng)}
        operator=f"NORMALIZED_OP_{seed}_{i}_{rng.getrandbits(32):08x}"
        consumes=[applicable_ids[i]]
        if i>0 and rng.random()<0.25:
            consumes.append(applicable_ids[rng.randrange(i)])
            consumes=list(dict.fromkeys(consumes))
        rule={
            "id":rid,"origin":SOURCE_KINDS[(i+seed)%len(SOURCE_KINDS)],
            "operator":operator,"dependencies":deps,"output":out,
            "signature":{"inputs":[_sig(node_meta[d]) for d in deps],"output":_sig(out_meta)},
            "consumes_requirements":consumes,
        }
        rules.append(rule)
        node={"id":out,"kind":"derived","rule_id":rid,"operator":operator,
              "origin":rule["origin"],"type":out_meta["type"],"dimension":out_meta["dimension"]}
        node_meta[out]=out_meta; all_ids.append(out); derived_nodes.append(node)
        for dep in deps:
            edges.append({"source":dep,"target":out,"rule_id":rid})
            acceptance.append({"edge_id":f"{rid}:{dep}->{out}","source":dep,"target":out,"rule_id":rid,
                               "check":"INDEPENDENT_EDGE_CONSEQUENCE_REQUIRED"})
        for req in consumes:
            lineage.append({"requirement_id":req,"consumer_rule_id":rid,"output":out})

    invariants=[]
    for j in range(rng.randint(1,min(5,n))):
        target=rng.choice(list(node_meta))
        iid=f"inv{j}"
        invariants.append({"id":iid,"target":target,"predicate":f"NORMALIZED_PREDICATE_{seed}_{j}",
                           "target_signature":_sig(node_meta[target])})

    required_outputs=sorted(rng.sample([f"v{i}" for i in range(n)],rng.randint(1,min(4,n))))
    input_nodes=[{"id":nid,"kind":"input","type":m["type"],"dimension":m["dimension"]} for nid,m in inputs.items()]
    expected={
        "schema":"PROJECT_BRAIN_STRUCTURED_METHOD_NORMALIZED_GRAPH_V3",
        "nodes":sorted(input_nodes+derived_nodes,key=lambda x:x["id"]),
        "edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),
        "requirement_lineage":sorted(lineage,key=lambda x:(x["requirement_id"],x["consumer_rule_id"])),
        "exclusions":sorted(exclusions,key=lambda x:x["requirement_id"]),
        "invariants":sorted([
            {"id":x["id"],"target":x["target"],"predicate":x["predicate"],
             "target_type":node_meta[x["target"]]["type"],
             "target_dimension":node_meta[x["target"]]["dimension"]} for x in invariants
        ],key=lambda x:x["id"]),
        "acceptance_edge_bindings":sorted(acceptance,key=lambda x:x["edge_id"]),
        "required_outputs":required_outputs,
        "applied_rule_ids":sorted(f"rule{i}" for i in range(n)),
    }
    public={
        "behavior_id":BEHAVIOR_ID,
        "task":{
            "inputs":inputs,"requirements":requirements,
            "normalized_rules":rules,"invariants":invariants,
            "required_outputs":required_outputs,
        }
    }
    return {"public":public,"_oracle":{"expected":expected}}

def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return copy.deepcopy(case["public"])

def score(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping) or candidate.get("status")!="OK":
        return {"pass":False,"reason":"CANDIDATE_STATUS"}
    graph=candidate.get("graph")
    if graph!=case["_oracle"]["expected"]:
        return {"pass":False,"reason":"GRAPH_MISMATCH"}
    return {"pass":True,"reason":"PASS"}

def mutation_cases(base:Mapping[str,Any])->list[tuple[str,dict[str,Any]]]:
    p=copy.deepcopy(base["public"])
    rules=p["task"]["normalized_rules"]
    out=[]
    # Signature corruption.
    q=copy.deepcopy(p); q["task"]["normalized_rules"][0]["signature"]["inputs"][0]["type"]="__WRONG__"
    out.append(("SIGNATURE_MISMATCH",q))
    # Applicable requirement without a consumer.
    q=copy.deepcopy(p); victim=q["task"]["requirements"][0]["id"]
    for r in q["task"]["normalized_rules"]:
        r["consumes_requirements"]=[x for x in r["consumes_requirements"] if x!=victim]
    out.append(("MISSING_REQUIREMENT_CONSUMER",q))
    # Consuming an excluded requirement.
    q=copy.deepcopy(p); excluded=[x["id"] for x in q["task"]["requirements"] if x["disposition"]=="EXCLUDED"][0]
    q["task"]["normalized_rules"][0]["consumes_requirements"].append(excluded)
    out.append(("CONSUME_EXCLUDED_REQUIREMENT",q))
    # Cycle.
    if len(rules)>=2:
        q=copy.deepcopy(p)
        r0=q["task"]["normalized_rules"][0]; r1=q["task"]["normalized_rules"][1]
        r0["dependencies"]=[r1["output"]]
        r0["signature"]["inputs"]=[copy.deepcopy(r1["signature"]["output"])]
        r1["dependencies"]=[r0["output"]]
        r1["signature"]["inputs"]=[copy.deepcopy(r0["signature"]["output"])]
        out.append(("DEPENDENCY_CYCLE",q))
    # Untraced required output.
    q=copy.deepcopy(p); q["task"]["required_outputs"].append("__MISSING_OUTPUT__")
    out.append(("MISSING_REQUIRED_OUTPUT",q))
    # Invariant metadata mismatch.
    q=copy.deepcopy(p); q["task"]["invariants"][0]["target_signature"]["type"]="__WRONG__"
    out.append(("INVARIANT_SIGNATURE_MISMATCH",q))
    return out

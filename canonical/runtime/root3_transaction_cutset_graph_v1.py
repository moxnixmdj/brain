from __future__ import annotations
from collections import defaultdict
from typing import Iterable

SCHEMA="PROJECT_BRAIN_ROOT3_TRANSACTION_CUTSET_GRAPH_V1"

BASE_EDGES={
    ("RUNTIME_ENTRY","PARENT_PRESTEP_BINDING"),
    ("PARENT_PRESTEP_BINDING","EXECUTE_STEP_TRANSACTION_GATE"),
    ("EXECUTE_STEP_TRANSACTION_GATE","NAMESPACE_SUPERVISOR"),
    ("NAMESPACE_SUPERVISOR","UNTRUSTED_WORKER_BLACK_BOX"),
    ("UNTRUSTED_WORKER_BLACK_BOX","RESULT_CAPTURE"),
    ("UNTRUSTED_WORKER_BLACK_BOX","PRIVATE_OVERLAY_UPPER"),
    ("UNTRUSTED_WORKER_BLACK_BOX","PROCESS_STATUS"),
    ("PRIVATE_OVERLAY_UPPER","OVERLAY_DIFF_COMPILER"),
    ("OVERLAY_DIFF_COMPILER","CANONICAL_FINAL_AUTHORIZER"),
    ("CANONICAL_FINAL_AUTHORIZER","EFFECT_CARRIER_GUARD_V2"),
    ("EFFECT_CARRIER_GUARD_V2","DURABLE_FILE_COMMIT"),
    ("RESULT_CAPTURE","COMPOSITION_STATE_CAPSULE"),
    ("PROCESS_STATUS","COMPOSITION_STATE_CAPSULE"),
    ("COMPOSITION_STATE_CAPSULE","PARENT_STATE_COMMIT"),
    ("PARENT_STATE_COMMIT","USER_VISIBLE_LOAD_BEARING_OUTPUT"),
}

SINK_REQUIREMENTS={
    "DURABLE_FILE_COMMIT":{
        "CANONICAL_FINAL_AUTHORIZER",
        "EFFECT_CARRIER_GUARD_V2",
    },
    "PARENT_STATE_COMMIT":{"COMPOSITION_STATE_CAPSULE"},
    "USER_VISIBLE_LOAD_BEARING_OUTPUT":{"COMPOSITION_STATE_CAPSULE"},
}

class CutsetError(RuntimeError):
    pass

def _paths(edges:set[tuple[str,str]], start:str, goal:str, limit:int=10000):
    adj=defaultdict(list)
    for a,b in edges:
        adj[a].append(b)
    out=[]
    def dfs(node,path,seen):
        if len(out)>=limit:
            raise CutsetError("PATH_LIMIT_EXCEEDED")
        if node==goal:
            out.append(tuple(path))
            return
        for nxt in adj.get(node,()):
            if nxt in seen:
                continue
            dfs(nxt,path+[nxt],seen|{nxt})
    dfs(start,[start],{start})
    return out

def verify_graph(extra_edges:Iterable[tuple[str,str]]=()):
    edges=set(BASE_EDGES)|set(extra_edges)
    failures=[]
    evidence={}
    for sink,required in SINK_REQUIREMENTS.items():
        paths=_paths(edges,"RUNTIME_ENTRY",sink)
        if not paths:
            failures.append({"sink":sink,"reason":"SINK_UNREACHABLE"})
            continue
        bad=[]
        for p in paths:
            missing=sorted(required-set(p))
            if missing:
                bad.append({"path":list(p),"missing":missing})
        evidence[sink]={
            "path_count":len(paths),
            "required_dominators":sorted(required),
            "all_paths_dominated":not bad,
            "bypass_paths":bad,
        }
        if bad:
            failures.append({"sink":sink,"reason":"DOMINATOR_BYPASS","count":len(bad)})
    return {
        "schema":SCHEMA,
        "status":"PASS" if not failures else "FAIL_CLOSED",
        "nodes":sorted({x for e in edges for x in e}),
        "edges":[list(e) for e in sorted(edges)],
        "sink_evidence":evidence,
        "failures":failures,
        "architectural_claim":(
            "IF_execute_step_ENTRY_DOMINANCE_AND_NAMESPACE_MEMBRANE_CUTSET_TOTALITY_HOLD, "
            "UNTRUSTED_INTERNAL_DEPENDENCY_NATIVE_CHILD_PROCESS_AND_EXTERNAL_TOOL_BEHAVIOR "
            "IS_BLACK_BOXED_BEHIND_RESULT_PROCESS_STATUS_AND_PRIVATE_OVERLAY_STATE; "
            "DURABLE_FILE_COMMIT_PATHS_THEN_CROSS_CANONICAL_FINAL_AUTHORIZER_AND_CARRIER_GUARD, "
            "WHILE_LOAD_BEARING_PARENT_STATE_PATHS_CROSS_COMPOSITION_STATE_CAPSULE."
        ),
        "hard_nonclaims":[
            "GRAPH_STRUCTURE_DOES_NOT_PROVE_PHYSICAL_MEMBRANE_TOTALITY",
            "GRAPH_STRUCTURE_DOES_NOT_PROVE_GUARD_SEMANTIC_SOUNDNESS",
            "GRAPH_STRUCTURE_DOES_NOT_PROVE_THE_TRANSACTION_GATE_IS_INSTALLED",
            "NO_C1_C2_C3_OR_ACCEPTANCE_CREDIT",
        ],
        "accounting":{"acceptance_credit_delta":0,"new_reality_units_consumed":0},
    }

from __future__ import annotations
from collections import defaultdict
from typing import Iterable

SCHEMA="PROJECT_BRAIN_ROOT3_THREE_CHANNEL_TRANSACTION_GRAPH_V1"

BASE_EDGES={
    ("RUNTIME_ENTRY","TRANSACTION_SUPERVISOR"),
    ("TRANSACTION_SUPERVISOR","UNTRUSTED_RUNTIME_BLACK_BOX"),

    ("UNTRUSTED_RUNTIME_BLACK_BOX","RESULT_CHANNEL"),
    ("UNTRUSTED_RUNTIME_BLACK_BOX","PROCESS_STATUS_CHANNEL"),
    ("UNTRUSTED_RUNTIME_BLACK_BOX","PRIVATE_OVERLAY_CHANNEL"),

    ("PRIVATE_OVERLAY_CHANNEL","DECLARED_ARTIFACT_EXTRACTOR"),
    ("DECLARED_ARTIFACT_EXTRACTOR","CANONICAL_FINAL_AUTHORIZER"),
    ("CANONICAL_FINAL_AUTHORIZER","EFFECT_CARRIER_GUARD_V2"),
    ("EFFECT_CARRIER_GUARD_V2","TYPED_PARENT_FINALIZER"),
    ("TYPED_PARENT_FINALIZER","DURABLE_DECLARED_ARTIFACT"),

    ("PRIVATE_OVERLAY_CHANNEL","EXTERNAL_INFORMATION_REQUEST_EXTRACTOR"),
    ("EXTERNAL_INFORMATION_REQUEST_EXTRACTOR","CONTINUOUS_OBS_INFORMATION_ADMISSION"),
    ("CONTINUOUS_OBS_INFORMATION_ADMISSION","TRUSTED_EXTERNAL_INFORMATION_SERVICE"),
    ("TRUSTED_EXTERNAL_INFORMATION_SERVICE","CONTENT_BOUND_INFORMATION_RESPONSE"),
    ("CONTENT_BOUND_INFORMATION_RESPONSE","PRIVATE_OVERLAY_RESPONSE_INJECTION"),
    ("PRIVATE_OVERLAY_RESPONSE_INJECTION","UNTRUSTED_RUNTIME_BLACK_BOX"),

    ("RESULT_CHANNEL","COMPOSITION_STATE_CAPSULE"),
    ("PROCESS_STATUS_CHANNEL","COMPOSITION_STATE_CAPSULE"),
    ("COMPOSITION_STATE_CAPSULE","PARENT_STATE_EVIDENCE_COMMIT"),
    ("COMPOSITION_STATE_CAPSULE","USER_VISIBLE_LOAD_BEARING_OUTPUT"),
}

REQUIRED={
    "DURABLE_DECLARED_ARTIFACT":{
        "DECLARED_ARTIFACT_EXTRACTOR",
        "CANONICAL_FINAL_AUTHORIZER",
        "EFFECT_CARRIER_GUARD_V2",
        "TYPED_PARENT_FINALIZER",
    },
    "TRUSTED_EXTERNAL_INFORMATION_SERVICE":{
        "EXTERNAL_INFORMATION_REQUEST_EXTRACTOR",
        "CONTINUOUS_OBS_INFORMATION_ADMISSION",
    },
    "PARENT_STATE_EVIDENCE_COMMIT":{"COMPOSITION_STATE_CAPSULE"},
    "USER_VISIBLE_LOAD_BEARING_OUTPUT":{"COMPOSITION_STATE_CAPSULE"},
}

class GraphError(RuntimeError):
    pass

def _paths(edges:set[tuple[str,str]],start:str,goal:str,limit:int=5000):
    adj=defaultdict(list)
    for a,b in edges:
        adj[a].append(b)
    out=[]
    def dfs(node,path,seen):
        if len(out)>=limit:
            raise GraphError("PATH_LIMIT_EXCEEDED")
        if node==goal:
            out.append(tuple(path)); return
        for nxt in adj.get(node,()):
            if nxt in seen:
                continue
            dfs(nxt,path+[nxt],seen|{nxt})
    dfs(start,[start],{start})
    return out

def verify(extra_edges:Iterable[tuple[str,str]]=()):
    edges=set(BASE_EDGES)|set(extra_edges)
    failures=[]; evidence={}
    for sink,required in REQUIRED.items():
        paths=_paths(edges,"RUNTIME_ENTRY",sink)
        if not paths:
            failures.append({"sink":sink,"reason":"UNREACHABLE"}); continue
        bad=[]
        for path in paths:
            missing=sorted(required-set(path))
            if missing:
                bad.append({"path":list(path),"missing":missing})
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
        "worker_external_channel_count":3,
        "worker_external_channels":[
            "RESULT_CHANNEL",
            "PROCESS_STATUS_CHANNEL",
            "PRIVATE_OVERLAY_CHANNEL",
        ],
        "general_worker_durable_filesystem_commit":"ABSENT_BY_DESIGN",
        "direct_worker_network":"ABSENT_BY_PHYSICAL_MEMBRANE_PREMISE",
        "sink_evidence":evidence,
        "failures":failures,
        "hard_nonclaims":[
            "GRAPH_PASS_DOES_NOT_PROVE_PHYSICAL_NAMESPACE_MEMBRANE",
            "GRAPH_PASS_DOES_NOT_PROVE_REQUEST_OR_AUTHORIZATION_SEMANTIC_SOUNDNESS",
            "GRAPH_PASS_DOES_NOT_PROVE_THE_ARCHITECTURE_IS_INSTALLED",
            "NO_C1_C2_C3_OR_ACCEPTANCE_CREDIT",
        ],
        "accounting":{"acceptance_credit_delta":0,"new_reality_units_consumed":0},
    }

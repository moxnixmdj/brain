"""Additive zero-learned Unknown-Domain direct candidate V2.

V1 is immutable and receives zero credit after a deductive support-ambiguity
finding. V2 keeps the frozen visible interface, requests a second allowed probe
when output consistency cannot identify support, then resolves any remaining
output-saturating ambiguity by minimum visible cross-domain scale distortion.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence
from canonical.runtime import unknown_domain_direct_candidate_v1 as v1

TRANSFER=v1.TRANSFER
ABSTAIN=v1.ABSTAIN
CandidateError=v1.UnknownDomainDirectCandidateError

def _unused_probe(case:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    used={str(t.get("requested_probe_id") or "") for t in transcript if isinstance(t,Mapping)}
    rows=[]
    for p in case.get("domain_b",{}).get("allowed_probes",[]):
        if not isinstance(p,Mapping):
            continue
        pid=str(p.get("probe_id") or "")
        if pid and pid not in used:
            cost=p.get("cost")
            if isinstance(cost,bool) or not isinstance(cost,(int,float)):
                cost=math.inf
            rows.append((float(cost),pid))
    if not rows:
        raise CandidateError("NO_UNUSED_PROBE")
    rows.sort()
    return {"type":"REQUEST_PROBE","probe_id":rows[0][1]}

def _source_ranges(case:Mapping[str,Any], receipt:Mapping[str,Any], roles:list[str]):
    binding=receipt.get("source_role_binding")
    tasks=case.get("domain_a",{}).get("tasks")
    if not isinstance(binding,Mapping) or not isinstance(tasks,list):
        raise CandidateError("SOURCE_RANGE_INPUT_INVALID")
    out={}
    for role in roles:
        fid=str(binding.get(role) or "")
        vals=[]
        for row in tasks:
            if isinstance(row,Mapping) and isinstance(row.get("inputs"),Mapping) and fid in row["inputs"]:
                vals.append(float(row["inputs"][fid]))
        if len(vals)<2:
            raise CandidateError("SOURCE_RANGE_INSUFFICIENT")
        out[role]=(min(vals),max(vals))
    return out

def _outside_distance(x:float, lo:float, hi:float):
    span=max(hi-lo,1e-9)
    if x<lo:return (lo-x)/span
    if x>hi:return (x-hi)/span
    return 0.0

def _scale_resolve(case,transcript,receipt,program,mappings):
    roles=[str(x) for x in program.get("roles",[])]
    ranges=_source_ranges(case,receipt,roles)
    probes=[t.get("probe_result") for t in transcript if isinstance(t,Mapping) and isinstance(t.get("probe_result"),Mapping)]
    if not probes:
        raise CandidateError("PROBE_REQUIRED")
    best={}
    for m in mappings:
        support=tuple(sorted(set(m.values())))
        score=0.0
        for role in roles:
            lo,hi=ranges[role]
            for row in probes:
                score += _outside_distance(float(row["inputs"][m[role]]),lo,hi)**2
        prev=best.get(support)
        if prev is None or score<prev[0]:
            best[support]=(score,m)
    ranked=sorted((score,support,m) for support,(score,m) in best.items())
    if not ranked:
        raise CandidateError("NO_SCALE_CANDIDATE")
    if len(ranked)>1 and math.isclose(ranked[0][0],ranked[1][0],rel_tol=0.0,abs_tol=1e-12):
        raise CandidateError("STRUCTURAL_SCALE_TIE")
    return ranked[0][2]

def _conclude(case,transcript,receipt,program,mapping):
    query=case.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    values={role:float(query[fid]) for role,fid in mapping.items()}
    consequence=v1._program_eval(program,values)
    support=set(mapping.values())
    rejected=v1._all_visible_feature_ids(case,transcript)-support
    rid=str(receipt["receipt_id"])
    return {
        "type":"CONCLUDE",
        "terminal_consequence":consequence,
        "domain_a_source_receipt_ids":[rid],
        "transferred_primitive_fingerprint":str(receipt["primitive_fingerprint"]),
        "support_feature_ids":sorted(support),
        "negative_transfer_rejected_feature_ids":sorted(rejected),
        "mapping_basis":v1.MAPPING_BASIS,
        "evidence_provenance":v1._provenance(rid,support,rejected),
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
    }

def _transfer(case:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    receipt=v1._receipt(case)
    program=receipt.get("normalized_primitive_program")
    if not isinstance(program,Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")
    if not transcript:
        return _unused_probe(case,transcript)
    observations=v1._public_transfer_observations(case,transcript)
    mappings=v1._candidate_mappings(program,observations)
    supports={v1._support_signature(m) for m in mappings}
    query=case.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    consequences={round(x[0],12) for x in v1._query_predictions(program,mappings,query)}
    if len(supports)==1 and len(consequences)==1:
        mapping=sorted(mappings,key=lambda m:tuple(sorted(m.items())))[0]
        return _conclude(case,transcript,receipt,program,mapping)
    if len(transcript)<2:
        return _unused_probe(case,transcript)
    mapping=_scale_resolve(case,transcript,receipt,program,mappings)
    return _conclude(case,transcript,receipt,program,mapping)

def step(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    leaf=str(case_visible.get("leaf_id") or "")
    if leaf==TRANSFER:return _transfer(case_visible,transcript)
    if leaf==ABSTAIN:return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")

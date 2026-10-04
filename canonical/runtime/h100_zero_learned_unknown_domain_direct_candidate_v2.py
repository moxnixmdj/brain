"""Zero-learned Unknown-Domain direct candidate V2.

Repairs V1's support ambiguity for output-saturating primitives. V2 first uses
V1 exact output-consistency. If support is still ambiguous it requests the
second allowed probe. If ambiguity remains, it selects the output-consistent
support with minimum scale distortion relative to visible Domain-A role values.
"""
from __future__ import annotations
import itertools, math
from typing import Any, Mapping, Sequence
from canonical.runtime import h100_zero_learned_unknown_domain_direct_candidate_v1 as v1

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2"
TRANSFER=v1.TRANSFER
ABSTAIN=v1.ABSTAIN
CandidateError=v1.CandidateError

def _unused_probe(case:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]])->dict[str,Any]:
    used={str(t.get("requested_probe_id") or "") for t in transcript if isinstance(t,Mapping)}
    rows=[p for p in case.get("domain_b",{}).get("allowed_probes",[])
          if isinstance(p,Mapping) and str(p.get("probe_id") or "") not in used]
    if not rows:
        raise CandidateError("NO_UNUSED_PROBE")
    p=min(rows,key=lambda x:(float(x.get("cost",math.inf)),str(x.get("probe_id") or "")))
    return {"type":"REQUEST_PROBE","probe_id":str(p["probe_id"])}

def _fits(case,transcript,program):
    roles=[str(x) for x in program["roles"]]
    feats=v1._all_domain_b_features(case,transcript)
    obs=list(case.get("domain_b",{}).get("tasks",[]))
    obs += [t["probe_result"] for t in transcript
            if isinstance(t,Mapping) and isinstance(t.get("probe_result"),Mapping)]
    out=[]
    for chosen in itertools.permutations(feats,len(roles)):
        m=dict(zip(roles,chosen))
        ok=True
        for row in obs:
            try:
                vals={r:float(row["inputs"][m[r]]) for r in roles}
                pred=v1._eval_program(program,vals)
            except Exception:
                ok=False;break
            if not v1._same_number(pred,row.get("terminal_consequence")):
                ok=False;break
        if ok:out.append(m)
    if not out:raise CandidateError("NO_CONSISTENT_ROLE_MAPPING")
    return out

def _source_ranges(case,receipt,roles):
    bind=receipt.get("source_role_binding",{})
    tasks=case.get("domain_a",{}).get("tasks",[])
    out={}
    for role in roles:
        fid=str(bind.get(role) or "")
        vals=[float(r["inputs"][fid]) for r in tasks if isinstance(r,Mapping) and fid in r.get("inputs",{})]
        if len(vals)<2:raise CandidateError("SOURCE_RANGE_INSUFFICIENT")
        out[role]=(min(vals),max(vals))
    return out

def _outside_distance(x,lo,hi):
    span=max(hi-lo,1e-9)
    if x<lo:return (lo-x)/span
    if x>hi:return (x-hi)/span
    return 0.0

def _scale_resolve(case,transcript,receipt,program):
    roles=[str(x) for x in program["roles"]]
    ranges=_source_ranges(case,receipt,roles)
    probes=[t["probe_result"] for t in transcript if isinstance(t,Mapping) and isinstance(t.get("probe_result"),Mapping)]
    if not probes:raise CandidateError("PROBE_REQUIRED")
    best={}
    for m in _fits(case,transcript,program):
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
    if len(ranked)>1 and math.isclose(ranked[0][0],ranked[1][0],rel_tol=0,abs_tol=1e-12):
        raise CandidateError("STRUCTURAL_SCALE_TIE")
    return ranked[0][2]

def _conclude(case,transcript,receipt,program,mapping):
    query=case.get("domain_b",{}).get("query_inputs",{})
    values={r:float(query[f]) for r,f in mapping.items()}
    consequence=v1._eval_program(program,values)
    support=sorted(set(mapping.values()))
    rejected=sorted(set(v1._all_domain_b_features(case,transcript))-set(support))
    rid=str(receipt["receipt_id"]); fp=str(receipt["primitive_fingerprint"])
    prov=[{"evidence_id":rid,"source":"DOMAIN_A_RECEIPT","receipt":fp}]
    prov += [{"evidence_id":f,"source":"DOMAIN_B_VISIBLE_OR_PROBE","receipt":"OBSERVED_FEATURE"}
             for f in sorted(set(support)|set(rejected))]
    return {"type":"CONCLUDE","terminal_consequence":consequence,
            "domain_a_source_receipt_ids":[rid],
            "transferred_primitive_fingerprint":fp,
            "support_feature_ids":support,
            "negative_transfer_rejected_feature_ids":rejected,
            "mapping_basis":"STRUCTURAL_EQUIVALENCE",
            "evidence_provenance":prov}

def _transfer(case,transcript):
    receipt=v1._receipt(case)
    program=receipt.get("normalized_primitive_program")
    if not isinstance(program,Mapping):raise CandidateError("RECEIPT_PROGRAM_INVALID")
    if not transcript:return _unused_probe(case,transcript)
    try:
        mapping=v1._fit_role_mapping(case,transcript,program)
        return _conclude(case,transcript,receipt,program,mapping)
    except CandidateError as exc:
        if not str(exc).startswith("ROLE_MAPPING_SUPPORT_NOT_IDENTIFIED"):
            raise
    if len(transcript)<2:
        return _unused_probe(case,transcript)
    mapping=_scale_resolve(case,transcript,receipt,program)
    return _conclude(case,transcript,receipt,program,mapping)

def step(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]])->dict[str,Any]:
    leaf=case_visible.get("leaf_id")
    if leaf==TRANSFER:return _transfer(case_visible,transcript)
    if leaf==ABSTAIN:return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_UNSUPPORTED")

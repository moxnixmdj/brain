"""Zero-learned candidate for the frozen Unknown-Domain direct evaluator V1/V2.

This candidate implements only the frozen visible interface:
    step(case_visible, transcript) -> action

For transfer cases it reuses the independently verified normalized primitive
program carried by a Domain-A earned receipt, enumerates structural mappings to
opaque Domain-B features, filters them by public observations and requested probe
results, and concludes only when the query consequence and support feature set
are identified.  Otherwise it requests an allowed probe, bounded by the frozen
harness.

For calibrated unknown cases it concludes when all live hypotheses imply the
same terminal consequence, requests the minimum-cost visible safe binary
discriminator when one exists, and otherwise abstains with a witness.

The module imports no hidden generator, scorer, harness, model, or network
provider.  Persistent learned bytes are exactly zero.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
MAPPING_BASIS = "STRUCTURAL_EQUIVALENCE"

class UnknownDomainDirectCandidateError(ValueError):
    pass

def _finite(x: Any, field: str) -> float:
    if isinstance(x, bool):
        raise UnknownDomainDirectCandidateError(field.upper()+"_INVALID")
    try:
        y=float(x)
    except (TypeError,ValueError) as exc:
        raise UnknownDomainDirectCandidateError(field.upper()+"_INVALID") from exc
    if not math.isfinite(y):
        raise UnknownDomainDirectCandidateError(field.upper()+"_NONFINITE")
    return y

def _program_eval(program: Mapping[str,Any], role_values: Mapping[str,float]) -> float:
    if not isinstance(program,Mapping):
        raise UnknownDomainDirectCandidateError("PROGRAM_INVALID")
    if program.get("dsl")!="UDIR_V1":
        raise UnknownDomainDirectCandidateError("PROGRAM_DSL_INVALID")
    op=str(program.get("op") or "")
    roles=program.get("roles")
    params=program.get("params")
    if not isinstance(roles,list) or not roles or not isinstance(params,Mapping):
        raise UnknownDomainDirectCandidateError("PROGRAM_SHAPE_INVALID")
    x=_finite(role_values.get("r0",0.0),"r0")
    if op=="AFFINE_POS":
        return _finite(params["bias"],"bias")+_finite(params["gain"],"gain")*x
    if op=="SIGN":
        return -1.0 if x<0 else 1.0
    if op=="COMPLEMENT":
        return _finite(params["total"],"total")-x
    if op=="SAT_MONO":
        return _finite(params["bias"],"bias")+_finite(params["gain"],"gain")*(x/(1.0+abs(x)))
    if op=="ADD2":
        return _finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")
    if op=="STEP":
        return _finite(params["high"],"high") if x>=_finite(params["threshold"],"threshold") else _finite(params["low"],"low")
    raise UnknownDomainDirectCandidateError("PROGRAM_OP_UNKNOWN")

def _close(a: float,b: float) -> bool:
    scale=max(1.0,abs(a),abs(b))
    return abs(a-b)<=1e-9*scale

def _receipt(case_visible: Mapping[str,Any]) -> Mapping[str,Any]:
    domain_a=case_visible.get("domain_a")
    if not isinstance(domain_a,Mapping):
        raise UnknownDomainDirectCandidateError("DOMAIN_A_INVALID")
    receipts=domain_a.get("earned_receipts")
    if not isinstance(receipts,list) or len(receipts)!=1 or not isinstance(receipts[0],Mapping):
        raise UnknownDomainDirectCandidateError("EXACTLY_ONE_EARNED_RECEIPT_REQUIRED")
    rec=receipts[0]
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise UnknownDomainDirectCandidateError("EARNED_RECEIPT_NOT_VERIFIED")
    for k in ("receipt_id","normalized_primitive_program","primitive_fingerprint"):
        if not rec.get(k):
            raise UnknownDomainDirectCandidateError("EARNED_RECEIPT_FIELD_MISSING:"+k)
    return rec

def _public_transfer_observations(case_visible: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]):
    domain_b=case_visible.get("domain_b")
    if not isinstance(domain_b,Mapping):
        raise UnknownDomainDirectCandidateError("DOMAIN_B_INVALID")
    tasks=domain_b.get("tasks")
    if not isinstance(tasks,list) or not tasks:
        raise UnknownDomainDirectCandidateError("DOMAIN_B_TASKS_INVALID")
    rows=[]
    for row in tasks:
        if not isinstance(row,Mapping) or not isinstance(row.get("inputs"),Mapping):
            raise UnknownDomainDirectCandidateError("DOMAIN_B_TASK_INVALID")
        rows.append((dict(row["inputs"]),_finite(row.get("terminal_consequence"),"terminal_consequence"),"DOMAIN_B_PUBLIC_TASK"))
    for tr in transcript:
        if not isinstance(tr,Mapping):
            raise UnknownDomainDirectCandidateError("TRANSCRIPT_INVALID")
        probe=tr.get("probe_result")
        if not isinstance(probe,Mapping) or not isinstance(probe.get("inputs"),Mapping):
            raise UnknownDomainDirectCandidateError("PROBE_RESULT_INVALID")
        rows.append((dict(probe["inputs"]),_finite(probe.get("terminal_consequence"),"probe_terminal_consequence"),"DOMAIN_B_REQUESTED_PROBE"))
    return rows

def _candidate_mappings(program: Mapping[str,Any], observations):
    roles=[str(x) for x in program.get("roles",[])]
    if roles not in (["r0"],["r0","r1"]):
        raise UnknownDomainDirectCandidateError("PROGRAM_ROLES_UNSUPPORTED")
    keys=None
    for inputs,_,_ in observations:
        current=set(map(str,inputs.keys()))
        keys=current if keys is None else keys&current
    if not keys or len(keys)<len(roles):
        raise UnknownDomainDirectCandidateError("DOMAIN_B_FEATURE_SET_TOO_SMALL")
    out=[]
    for chosen in itertools.permutations(sorted(keys),len(roles)):
        mapping=dict(zip(roles,chosen))
        ok=True
        for inputs,target,_ in observations:
            try:
                vals={role:_finite(inputs[fid],fid) for role,fid in mapping.items()}
                pred=_program_eval(program,vals)
            except (KeyError,UnknownDomainDirectCandidateError):
                ok=False; break
            if not _close(pred,target):
                ok=False; break
        if ok:
            out.append(mapping)
    if not out:
        raise UnknownDomainDirectCandidateError("NO_STRUCTURAL_MAPPING_SURVIVES_PUBLIC_EVIDENCE")
    return out

def _support_signature(mapping: Mapping[str,str]) -> tuple[str,...]:
    return tuple(sorted(set(mapping.values())))

def _query_predictions(program, mappings, query_inputs):
    rows=[]
    for mapping in mappings:
        vals={role:_finite(query_inputs[fid],fid) for role,fid in mapping.items()}
        rows.append((_program_eval(program,vals),_support_signature(mapping),mapping))
    return rows

def _all_visible_feature_ids(case_visible: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]) -> set[str]:
    domain_b=case_visible["domain_b"]
    ids=set()
    for row in domain_b["tasks"]:
        ids.update(map(str,row["inputs"].keys()))
    query=domain_b.get("query_inputs")
    if isinstance(query,Mapping):
        ids.update(map(str,query.keys()))
    for tr in transcript:
        probe=tr.get("probe_result",{})
        if isinstance(probe,Mapping) and isinstance(probe.get("inputs"),Mapping):
            ids.update(map(str,probe["inputs"].keys()))
    return ids

def _provenance(receipt_id: str, support: set[str], rejected: set[str]):
    rows=[{"evidence_id":receipt_id,"source":"DOMAIN_A_EARNED_RECEIPT","receipt":receipt_id}]
    for fid in sorted(support):
        rows.append({"evidence_id":fid,"source":"DOMAIN_B_PUBLIC_OR_REQUESTED_OBSERVATION","receipt":receipt_id})
    for fid in sorted(rejected):
        rows.append({"evidence_id":fid,"source":"DOMAIN_B_NEGATIVE_TRANSFER_CHECK","receipt":receipt_id})
    return rows

def _transfer_step(case_visible: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]):
    rec=_receipt(case_visible)
    program=rec["normalized_primitive_program"]
    observations=_public_transfer_observations(case_visible,transcript)
    mappings=_candidate_mappings(program,observations)
    query=case_visible.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping):
        raise UnknownDomainDirectCandidateError("DOMAIN_B_QUERY_INVALID")
    preds=_query_predictions(program,mappings,query)
    consequences={round(x[0],12) for x in preds}
    supports={x[1] for x in preds}

    if len(consequences)==1 and len(supports)==1:
        consequence=preds[0][0]
        support=set(next(iter(supports)))
        all_ids=_all_visible_feature_ids(case_visible,transcript)
        rejected=all_ids-support
        rid=str(rec["receipt_id"])
        return {
            "type":"CONCLUDE",
            "terminal_consequence":consequence,
            "domain_a_source_receipt_ids":[rid],
            "transferred_primitive_fingerprint":str(rec["primitive_fingerprint"]),
            "support_feature_ids":sorted(support),
            "negative_transfer_rejected_feature_ids":sorted(rejected),
            "mapping_basis":MAPPING_BASIS,
            "evidence_provenance":_provenance(rid,support,rejected),
            "persistent_learned_bytes":0,
            "external_frontier_model_calls":0,
            "external_learned_capability_calls":0,
        }

    requested={str(x.get("requested_probe_id") or "") for x in transcript}
    probes=case_visible.get("domain_b",{}).get("allowed_probes")
    if not isinstance(probes,list):
        raise UnknownDomainDirectCandidateError("ALLOWED_PROBES_INVALID")
    remaining=[]
    for row in probes:
        if not isinstance(row,Mapping):
            continue
        pid=str(row.get("probe_id") or "")
        if pid and pid not in requested:
            cost=row.get("cost")
            if isinstance(cost,bool) or not isinstance(cost,(int,float)):
                cost=10**9
            remaining.append((float(cost),pid))
    if remaining:
        remaining.sort(key=lambda x:(x[0],x[1]))
        return {"type":"REQUEST_PROBE","probe_id":remaining[0][1]}

    return {
        "type":"ABSTAIN",
        "nonidentifiability_witness":"MULTIPLE_STRUCTURAL_MAPPINGS_REMAIN_AFTER_ALL_ALLOWED_TRANSFER_PROBES",
    }

def _abstention_step(case_visible: Mapping[str,Any]):
    hypotheses=case_visible.get("hypotheses")
    if not isinstance(hypotheses,list) or not hypotheses:
        raise UnknownDomainDirectCandidateError("HYPOTHESES_INVALID")
    live=[]
    for h in hypotheses:
        if not isinstance(h,Mapping):
            raise UnknownDomainDirectCandidateError("HYPOTHESIS_NOT_OBJECT")
        if h.get("plausible") is not True:
            continue
        hid=str(h.get("hypothesis_id") or "")
        consequence=str(h.get("terminal_consequence") or "")
        if not hid or not consequence:
            raise UnknownDomainDirectCandidateError("LIVE_HYPOTHESIS_INVALID")
        live.append((hid,consequence))
    if not live:
        return {"type":"ABSTAIN","nonidentifiability_witness":"NO_LIVE_SUPPORTED_HYPOTHESIS"}

    consequences={x[1] for x in live}
    if len(consequences)==1:
        return {"type":"CONCLUDE","terminal_consequence":next(iter(consequences))}

    probes=case_visible.get("allowed_probes")
    if not isinstance(probes,list):
        raise UnknownDomainDirectCandidateError("ALLOWED_PROBES_INVALID")
    discriminators=[]
    for row in probes:
        if not isinstance(row,Mapping):
            continue
        pid=str(row.get("probe_id") or "")
        schema=row.get("argument_schema")
        kind=str(schema.get("type") or "") if isinstance(schema,Mapping) else ""
        cost=row.get("cost")
        if pid and kind=="SAFE_BINARY_DISCRIMINATOR" and not isinstance(cost,bool) and isinstance(cost,(int,float)):
            discriminators.append((float(cost),pid))
    if discriminators:
        discriminators.sort(key=lambda x:(x[0],x[1]))
        return {"type":"REQUEST_DISCRIMINATOR","discriminator":discriminators[0][1]}

    witness="DECISION_DISTINCT_LIVE_HYPOTHESES_WITH_NO_VISIBLE_SAFE_DISCRIMINATOR:"+",".join(sorted(hid for hid,_ in live))
    return {"type":"ABSTAIN","nonidentifiability_witness":witness}

def step(case_visible: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]):
    if not isinstance(case_visible,Mapping):
        raise UnknownDomainDirectCandidateError("CASE_VISIBLE_INVALID")
    if not isinstance(transcript,Sequence) or isinstance(transcript,(str,bytes)):
        raise UnknownDomainDirectCandidateError("TRANSCRIPT_INVALID")
    leaf=str(case_visible.get("leaf_id") or "")
    if leaf==TRANSFER:
        return _transfer_step(case_visible,transcript)
    if leaf==ABSTAIN:
        return _abstention_step(case_visible)
    raise UnknownDomainDirectCandidateError("LEAF_ID_UNKNOWN")

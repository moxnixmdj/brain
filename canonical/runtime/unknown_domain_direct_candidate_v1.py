"""Zero-learned candidate for the frozen Unknown-Domain direct evaluator.

The candidate is a generic constraint solver over the candidate-visible packet:
- reuse the normalized primitive program from a verified Domain-A receipt,
- enumerate Domain-B feature-to-role mappings consistent with visible evidence,
- request only predeclared probes while mappings remain decision-relevant,
- conclude only when the surviving support set and query consequence are unique,
- reject all non-support features as negative-transfer distractors,
- distinguish identifiable, underspecified, and nonidentifiable decision states
  from candidate-visible hypotheses and declared safe discriminator probes.

No learned state, model call, hidden evaluator field, or production-case secret is
used. Qualification and production execution are separate governance steps.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V1"
TRANSFER="CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN="CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
TOL=1e-8

RESOURCE_ACCOUNTING={
    "persistent_learned_bytes":0,
    "external_frontier_model_calls":0,
    "external_learned_capability_calls":0,
}


class UnknownDomainCandidateError(ValueError):
    pass


def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()


def _digest(value:Any)->str:
    return "sha256:"+hashlib.sha256(_canon(value)).hexdigest()


def _finite(value:Any, field:str)->float:
    if isinstance(value,bool):
        raise UnknownDomainCandidateError(field+"_INVALID")
    try:
        out=float(value)
    except (TypeError,ValueError) as exc:
        raise UnknownDomainCandidateError(field+"_INVALID") from exc
    if not math.isfinite(out):
        raise UnknownDomainCandidateError(field+"_NONFINITE")
    return out


def _program_eval(program:Mapping[str,Any], role_values:Mapping[str,float])->float:
    if not isinstance(program,Mapping) or program.get("dsl")!="UDIR_V1":
        raise UnknownDomainCandidateError("PRIMITIVE_PROGRAM_INVALID")
    op=str(program.get("op") or "")
    params=program.get("params")
    if not isinstance(params,Mapping):
        raise UnknownDomainCandidateError("PRIMITIVE_PARAMS_INVALID")
    roles=program.get("roles")
    if not isinstance(roles,Sequence) or isinstance(roles,(str,bytes)) or not roles:
        raise UnknownDomainCandidateError("PRIMITIVE_ROLES_INVALID")
    for role in roles:
        if str(role) not in role_values:
            raise UnknownDomainCandidateError("PRIMITIVE_ROLE_VALUE_MISSING:"+str(role))
    x=_finite(role_values.get("r0",0.0),"r0")
    if op=="AFFINE_POS":
        y=_finite(params.get("bias"),"bias")+_finite(params.get("gain"),"gain")*x
    elif op=="SIGN":
        y=-1.0 if x<0.0 else 1.0
    elif op=="COMPLEMENT":
        y=_finite(params.get("total"),"total")-x
    elif op=="SAT_MONO":
        y=_finite(params.get("bias"),"bias")+_finite(params.get("gain"),"gain")*(x/(1.0+abs(x)))
    elif op=="ADD2":
        y=_finite(params.get("bias"),"bias")+_finite(role_values.get("r0"),"r0")+_finite(role_values.get("r1"),"r1")
    elif op=="STEP":
        threshold=_finite(params.get("threshold"),"threshold")
        y=_finite(params.get("high"),"high") if x>=threshold else _finite(params.get("low"),"low")
    else:
        raise UnknownDomainCandidateError("PRIMITIVE_OP_UNSUPPORTED")
    if not math.isfinite(y):
        raise UnknownDomainCandidateError("PRIMITIVE_OUTPUT_NONFINITE")
    return y


def _receipt(case_visible:Mapping[str,Any])->Mapping[str,Any]:
    domain_a=case_visible.get("domain_a")
    if not isinstance(domain_a,Mapping):
        raise UnknownDomainCandidateError("DOMAIN_A_INVALID")
    rows=domain_a.get("earned_receipts")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise UnknownDomainCandidateError("DOMAIN_A_RECEIPT_REQUIRED")
    admissible=[]
    for row in rows:
        if not isinstance(row,Mapping):
            continue
        if row.get("independent_verified") is not True or row.get("exact_byte_bound") is not True:
            continue
        if row.get("conclusion")!="success":
            continue
        if not str(row.get("receipt_id") or "").strip():
            continue
        if not str(row.get("primitive_fingerprint") or "").strip():
            continue
        if not isinstance(row.get("normalized_primitive_program"),Mapping):
            continue
        admissible.append(row)
    if not admissible:
        raise UnknownDomainCandidateError("NO_ADMISSIBLE_DOMAIN_A_RECEIPT")
    return sorted(admissible,key=lambda x:str(x["receipt_id"]))[0]


def _transcript_rows(transcript:Sequence[Mapping[str,Any]])->list[Mapping[str,Any]]:
    if not isinstance(transcript,Sequence) or isinstance(transcript,(str,bytes)):
        raise UnknownDomainCandidateError("TRANSCRIPT_INVALID")
    out=[]
    seen=set()
    for i,row in enumerate(transcript):
        if not isinstance(row,Mapping):
            raise UnknownDomainCandidateError("TRANSCRIPT_ROW_INVALID")
        pid=str(row.get("requested_probe_id") or "").strip()
        if not pid or pid in seen:
            raise UnknownDomainCandidateError("TRANSCRIPT_PROBE_ID_INVALID")
        seen.add(pid)
        result=row.get("probe_result")
        if not isinstance(result,Mapping):
            raise UnknownDomainCandidateError("TRANSCRIPT_PROBE_RESULT_INVALID")
        if not isinstance(result.get("inputs"),Mapping) or "terminal_consequence" not in result:
            raise UnknownDomainCandidateError("TRANSCRIPT_PROBE_RESULT_SCHEMA_INVALID")
        out.append(result)
    return out


def _observations(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]])->list[Mapping[str,Any]]:
    domain_b=case_visible.get("domain_b")
    if not isinstance(domain_b,Mapping):
        raise UnknownDomainCandidateError("DOMAIN_B_INVALID")
    rows=domain_b.get("tasks")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise UnknownDomainCandidateError("DOMAIN_B_TASKS_REQUIRED")
    out=[]
    feature_set=None
    for row in list(rows)+_transcript_rows(transcript):
        if not isinstance(row,Mapping) or not isinstance(row.get("inputs"),Mapping) or "terminal_consequence" not in row:
            raise UnknownDomainCandidateError("DOMAIN_B_OBSERVATION_INVALID")
        keys=set(map(str,row["inputs"].keys()))
        if not keys:
            raise UnknownDomainCandidateError("DOMAIN_B_FEATURES_EMPTY")
        if feature_set is None:
            feature_set=keys
        elif keys!=feature_set:
            raise UnknownDomainCandidateError("DOMAIN_B_FEATURE_SET_DRIFT")
        out.append(row)
    return out


def _close(a:float,b:float)->bool:
    return abs(a-b)<=TOL*max(1.0,abs(a),abs(b))


def _surviving_mappings(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    receipt=_receipt(case_visible)
    program=receipt["normalized_primitive_program"]
    roles=[str(x) for x in program["roles"]]
    rows=_observations(case_visible,transcript)
    features=sorted(map(str,rows[0]["inputs"].keys()))
    if len(roles)>len(features) or len(roles)>3:
        raise UnknownDomainCandidateError("ROLE_COUNT_UNSUPPORTED")
    survivors=[]
    for chosen in itertools.permutations(features,len(roles)):
        mapping=dict(zip(roles,chosen))
        ok=True
        for row in rows:
            try:
                values={role:_finite(row["inputs"][feature],feature) for role,feature in mapping.items()}
                pred=_program_eval(program,values)
                actual=_finite(row["terminal_consequence"],"terminal_consequence")
            except (KeyError,UnknownDomainCandidateError):
                ok=False
                break
            if not _close(pred,actual):
                ok=False
                break
        if ok:
            survivors.append(mapping)
    return receipt,program,rows,survivors


def _requested_probe_ids(transcript:Sequence[Mapping[str,Any]])->set[str]:
    return {str(x.get("requested_probe_id") or "") for x in transcript if isinstance(x,Mapping)}


def _next_probe(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    domain_b=case_visible["domain_b"]
    rows=domain_b.get("allowed_probes",[])
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise UnknownDomainCandidateError("ALLOWED_PROBES_INVALID")
    requested=_requested_probe_ids(transcript)
    available=[]
    for row in rows:
        if not isinstance(row,Mapping):
            continue
        pid=str(row.get("probe_id") or "").strip()
        if not pid or pid in requested:
            continue
        cost=_finite(row.get("cost",1.0),"probe_cost")
        available.append((cost,pid))
    if not available:
        return None
    _,pid=min(available,key=lambda x:(x[0],x[1]))
    return {"type":"REQUEST_PROBE","probe_id":pid}


def _feature_provenance(case_visible:Mapping[str,Any], rows:Sequence[Mapping[str,Any]], evidence_id:str)->dict[str,str]:
    return {
        "evidence_id":evidence_id,
        "source":"DOMAIN_B_VISIBLE_OR_REQUESTED_EVIDENCE",
        "receipt":_digest({
            "case_id":case_visible.get("case_id"),
            "feature_id":evidence_id,
            "observations":rows,
            "query_inputs":case_visible.get("domain_b",{}).get("query_inputs",{}),
        }),
    }


def _transfer_step(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]])->dict[str,Any]:
    receipt,program,rows,survivors=_surviving_mappings(case_visible,transcript)
    if not survivors:
        return {
            "type":"ABSTAIN",
            "nonidentifiability_witness":"NO_DOMAIN_B_ROLE_MAPPING_IS_CONSISTENT_WITH_THE_VERIFIED_SOURCE_PRIMITIVE_AND_VISIBLE_EVIDENCE",
        }

    query=case_visible.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping) or not query:
        raise UnknownDomainCandidateError("DOMAIN_B_QUERY_INPUTS_REQUIRED")

    support_sets={frozenset(m.values()) for m in survivors}
    predictions=[]
    for mapping in survivors:
        values={role:_finite(query[feature],feature) for role,feature in mapping.items()}
        predictions.append(_program_eval(program,values))
    prediction_unique=all(_close(predictions[0],x) for x in predictions[1:])

    if len(support_sets)!=1 or not prediction_unique:
        probe=_next_probe(case_visible,transcript)
        if probe is not None:
            return probe
        return {
            "type":"ABSTAIN",
            "nonidentifiability_witness":"MULTIPLE_DECISION_RELEVANT_DOMAIN_B_MAPPINGS_REMAIN_AFTER_ALL_ALLOWED_PROBES",
        }

    support=set(next(iter(support_sets)))
    all_features=set(map(str,query.keys()))
    if not support.issubset(all_features):
        raise UnknownDomainCandidateError("SUPPORT_NOT_IN_QUERY")
    rejected=all_features-support
    receipt_id=str(receipt["receipt_id"])
    fingerprint=str(receipt["primitive_fingerprint"])
    source_digest=str(receipt.get("source_evidence_digest") or _digest(receipt))
    provenance=[{
        "evidence_id":receipt_id,
        "source":"DOMAIN_A_EARNED_RECEIPT",
        "receipt":source_digest,
    }]
    provenance.extend(_feature_provenance(case_visible,rows,eid) for eid in sorted(support|rejected))

    return {
        "type":"CONCLUDE",
        "terminal_consequence":predictions[0],
        "domain_a_source_receipt_ids":[receipt_id],
        "transferred_primitive_fingerprint":fingerprint,
        "support_feature_ids":sorted(support),
        "negative_transfer_rejected_feature_ids":sorted(rejected),
        "mapping_basis":"FORMAL_REDUCTION",
        "evidence_provenance":provenance,
    }


def _abstention_step(case_visible:Mapping[str,Any])->dict[str,Any]:
    hypotheses=case_visible.get("hypotheses")
    if not isinstance(hypotheses,Sequence) or isinstance(hypotheses,(str,bytes)) or not hypotheses:
        return {"type":"ABSTAIN","nonidentifiability_witness":"NO_CANDIDATE_VISIBLE_LIVE_HYPOTHESES"}
    live=[h for h in hypotheses if isinstance(h,Mapping) and h.get("plausible") is not False]
    if not live:
        return {"type":"ABSTAIN","nonidentifiability_witness":"NO_POSITIVE_MASS_LIVE_HYPOTHESES"}

    consequences={}
    for h in live:
        if "terminal_consequence" not in h:
            return {"type":"ABSTAIN","nonidentifiability_witness":"LIVE_HYPOTHESIS_LACKS_TERMINAL_CONSEQUENCE"}
        key=_canon(h["terminal_consequence"]).decode()
        consequences[key]=h["terminal_consequence"]
    if len(consequences)==1:
        return {"type":"CONCLUDE","terminal_consequence":next(iter(consequences.values()))}

    probes=case_visible.get("allowed_probes",[])
    discriminators=[]
    if isinstance(probes,Sequence) and not isinstance(probes,(str,bytes)):
        for p in probes:
            if not isinstance(p,Mapping):
                continue
            schema=p.get("argument_schema",{})
            if not isinstance(schema,Mapping) or schema.get("type")!="SAFE_BINARY_DISCRIMINATOR":
                continue
            pid=str(p.get("probe_id") or "").strip()
            if not pid:
                continue
            cost=_finite(p.get("cost",1.0),"discriminator_cost")
            discriminators.append((cost,pid))
    if discriminators:
        _,pid=min(discriminators,key=lambda x:(x[0],x[1]))
        return {"type":"REQUEST_DISCRIMINATOR","discriminator":pid}

    witness="DECISION_DISTINCT_SURVIVORS_WITH_NO_DECLARED_SAFE_POSITIVE_GAIN_DISCRIMINATOR:"+",".join(
        sorted(str(h.get("hypothesis_id") or "") for h in live)
    )
    return {"type":"ABSTAIN","nonidentifiability_witness":witness}


def step(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(case_visible,Mapping):
        raise UnknownDomainCandidateError("CASE_VISIBLE_INVALID")
    leaf=case_visible.get("leaf_id")
    if leaf==TRANSFER:
        action=_transfer_step(case_visible,transcript)
    elif leaf==ABSTAIN:
        action=_abstention_step(case_visible)
    else:
        raise UnknownDomainCandidateError("LEAF_ID_UNKNOWN")
    return {
        **action,
        "_candidate_schema":SCHEMA,
        "_persistent_learned_bytes":0,
        "_external_frontier_model_calls":0,
        "_external_learned_capability_calls":0,
    }

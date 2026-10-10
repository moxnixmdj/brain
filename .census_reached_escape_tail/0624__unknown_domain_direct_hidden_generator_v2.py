"""Unknown-Domain direct hidden generator V2.

V2 preserves the independently verified V1 authority and packet schemas while
making all task-level numeric parameters and observations depend on the unseen
post-freeze beacon plus evaluator-only secret. This prevents candidate
qualification from overfitting the public TEST_ONLY fixture's numeric values.

No production case is generated on import or verification. Production generation
still requires the exact V1 predicate-local one-use authority gate.
"""
from __future__ import annotations

import hmac
import hashlib
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V2"


def _unit(secret:bytes, beacon:str, *parts:Any)->float:
    msg="|".join([beacon]+[str(x) for x in parts]).encode()
    raw=hmac.new(secret,msg,hashlib.sha256).digest()[:8]
    return int.from_bytes(raw,"big") / float((1<<64)-1)


def _range(secret:bytes, beacon:str, lo:float, hi:float, *parts:Any)->float:
    return lo + (hi-lo)*_unit(secret,beacon,*parts)


def _program_for(secret:bytes, beacon:str, index:int):
    family=v1.PRIMITIVE_FAMILIES[index % len(v1.PRIMITIVE_FAMILIES)]
    if family=="ORDER_PRESERVING_TRANSFORM":
        program={"dsl":"UDIR_V1","op":"AFFINE_POS","roles":["r0"],"params":{
            "bias":_range(secret,beacon,-2.0,2.0,"param",index,"bias"),
            "gain":_range(secret,beacon,0.6,2.6,"param",index,"gain"),
        }}
    elif family=="PARITY_OR_SIGN_INVARIANT":
        program={"dsl":"UDIR_V1","op":"SIGN","roles":["r0"],"params":{}}
    elif family=="CONSERVATION_RELATION":
        program={"dsl":"UDIR_V1","op":"COMPLEMENT","roles":["r0"],"params":{
            "total":_range(secret,beacon,2.0,8.0,"param",index,"total"),
        }}
    elif family=="MONOTONE_CAUSAL_EDGE":
        program={"dsl":"UDIR_V1","op":"SAT_MONO","roles":["r0"],"params":{
            "bias":_range(secret,beacon,-1.5,1.5,"param",index,"bias"),
            "gain":_range(secret,beacon,0.7,3.0,"param",index,"gain"),
        }}
    elif family=="COMPOSITIONAL_REWRITE":
        program={"dsl":"UDIR_V1","op":"ADD2","roles":["r0","r1"],"params":{
            "bias":_range(secret,beacon,-2.0,2.0,"param",index,"bias"),
        }}
    else:
        threshold=_range(secret,beacon,-1.25,1.25,"param",index,"threshold")
        low=_range(secret,beacon,-2.5,-0.5,"param",index,"low")
        high=_range(secret,beacon,0.5,2.5,"param",index,"high")
        program={"dsl":"UDIR_V1","op":"STEP","roles":["r0"],"params":{
            "threshold":threshold,"low":low,"high":high,
        }}
    return family,program,list(program["roles"])


def _role_rows(secret:bytes, beacon:str, index:int, program:Mapping[str,Any], *, domain:str):
    op=str(program["op"])
    rows=[]
    if op=="STEP":
        t=float(program["params"]["threshold"])
        for j in range(6):
            mag=_range(secret,beacon,0.35,2.2,"row",index,domain,j,"mag")
            sign=-1.0 if j%2==0 else 1.0
            rows.append({"r0":t+sign*mag})
        return rows

    for j in range(6):
        mag0=_range(secret,beacon,0.25,3.5,"row",index,domain,j,"r0")
        sign0=-1.0 if (j+index)%2==0 else 1.0
        row={"r0":sign0*mag0}
        if "r1" in program["roles"]:
            mag1=_range(secret,beacon,0.25,3.5,"row",index,domain,j,"r1")
            sign1=-1.0 if (j+index+1)%3==0 else 1.0
            row["r1"]=sign1*mag1
        rows.append(row)
    return rows


def _transfer_case(secret:bytes, beacon:str, index:int, *, namespace:str):
    family,program,roles=_program_for(secret,beacon,index)
    fingerprint=v1._sha256(program)
    source_rows=_role_rows(secret,beacon,index,program,domain="A")
    target_rows=_role_rows(secret,beacon,index,program,domain="B")
    a_map,a_distractors=v1._surface_ids(secret,beacon,index,namespace+"_A",roles)
    b_map,b_distractors=v1._surface_ids(secret,beacon,index,namespace+"_B",roles)
    if (set(a_map.values())|set(a_distractors)) & (set(b_map.values())|set(b_distractors)):
        raise v1.UnknownDomainGeneratorError("DOMAIN_VOCABULARY_OVERLAP")

    source_observations=[]
    for j,row in enumerate(source_rows[:3]):
        source_observations.append({
            "inputs":v1._surface_row(row,a_map,a_distractors,mimic_visible=False,probe_variant=j),
            "terminal_consequence":v1._eval(program,row),
        })

    target_observations=[]
    for j,row in enumerate(target_rows[:3]):
        target_observations.append({
            "inputs":v1._surface_row(row,b_map,b_distractors,mimic_visible=True,probe_variant=j),
            "terminal_consequence":v1._eval(program,row),
        })

    receipt_id=f"R-{v1._token(secret,beacon,'receipt',index,namespace)}"
    receipt={
        "receipt_id":receipt_id,
        "normalized_primitive_program":program,
        "primitive_fingerprint":fingerprint,
        "source_role_binding":dict(a_map),
        "source_evidence_digest":v1._sha256(source_observations),
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
    }

    probes=[]
    probe_hidden={}
    for j,row in enumerate(target_rows[3:5]):
        pid=f"P-{v1._token(secret,beacon,'probe',index,j,namespace)}"
        probes.append({
            "probe_id":pid,
            "argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW","row_slot":j},
            "cost":j+1,
        })
        probe_hidden[pid]={
            "inputs":v1._surface_row(row,b_map,b_distractors,mimic_visible=False,probe_variant=j),
            "terminal_consequence":v1._eval(program,row),
        }

    query_roles=target_rows[5]
    query_inputs=v1._surface_row(query_roles,b_map,b_distractors,mimic_visible=False,probe_variant=9)
    case_id=f"{namespace}-T-{v1._token(secret,beacon,'case',v1.TRANSFER,index,namespace,width=20)}"
    visible={
        "case_id":case_id,
        "leaf_id":v1.TRANSFER,
        "domain_a":{"tasks":source_observations,"earned_receipts":[receipt]},
        "domain_b":{
            "tasks":target_observations,
            "query_inputs":query_inputs,
            "allowed_probes":probes,
            "tool_metadata":{
                "input_shape":"OPAQUE_FEATURE_VALUE_MAP",
                "output_shape":"SCALAR_TERMINAL_CONSEQUENCE",
            },
        },
        "decision_requirement":"PREDICT_TERMINAL_CONSEQUENCE_AND_PROVIDE_TRANSFER_PROOF_TRACE",
    }
    relevant=[b_map[r] for r in roles]
    hidden={
        "case_id":case_id,
        "leaf_id":v1.TRANSFER,
        "primitive_family":family,
        "latent_primitive_program":program,
        "latent_primitive_fingerprint":fingerprint,
        "domain_mapping":dict(b_map),
        "domain_a_earned_receipt_ids":[receipt_id],
        "domain_a_receipt_primitive_bindings":{receipt_id:fingerprint},
        "transfer_relevant_feature_ids":relevant,
        "distractor_feature_ids":list(b_distractors),
        "gold_terminal_consequence":v1._eval(program,query_roles),
        "full_rediscovery_probe_floor":3,
        "surface_label_permutation_verified":True,
        "domain_vocabularies_disjoint":True,
        "allowed_probe_outcome_table":probe_hidden,
    }
    return visible,hidden


def _generate(*, beacon:str, evaluator_secret:Any, namespace:str):
    if not isinstance(beacon,str) or len(beacon.strip())<16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret=v1._secret_bytes(evaluator_secret)
    visible=[]
    hidden=[]
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        a,b=_transfer_case(secret,beacon,i,namespace=namespace)
        visible.append(a); hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        a,b=v1._abstention_case(secret,beacon,i,namespace=namespace)
        visible.append(a); hidden.append(b)
    ids=[x["case_id"] for x in visible]
    if len(ids)!=27 or len(ids)!=len(set(ids)):
        raise v1.UnknownDomainGeneratorError("CASE_ID_SET_INVALID")
    return {
        "schema":SCHEMA,
        "case_count":27,
        "visible_cases":visible,
        "hidden_records":hidden,
        "visible_packet_digest":v1._sha256(visible),
        "hidden_packet_digest":v1._sha256(hidden),
    }


def generate_production_population(*, beacon:str, evaluator_secret:Any, authority:Mapping[str,Any]):
    v1._production_authorized(authority)
    out=_generate(beacon=beacon,evaluator_secret=evaluator_secret,namespace="UDIR")
    out["authority_claim_id"]=str(authority["one_use_claim_id"])
    out["production"]=True
    return out


def generate_qualification_fixture_population(*, beacon:str):
    if not isinstance(beacon,str) or len(beacon.strip())<16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out=_generate(
        beacon="QUALIFICATION-ONLY|"+beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY",
    )
    out["production"]=False
    out["hard_nonclaim"]="QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out

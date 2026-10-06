"""Full Registry V1-V8 provenance census for independent H100 research.

This is a source/provenance audit, not a capability execution benchmark.
It classifies each of the 21 Registry V8 entries under a frozen causal taxonomy
and computes compact selection-code capacity only where a frozen finite search
universe is explicitly content-bound.

Selection-code capacity is NOT claimed as Shannon mutual information.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_H100_FULL_REGISTRY_PROVENANCE_CENSUS_V1"

V1=ROOT/"canonical/runtime/h100_verified_capability_registry_v1.py"
V2=ROOT/"canonical/runtime/h100_verified_capability_registry_v2.py"
V3=ROOT/"canonical/runtime/h100_verified_capability_registry_v3.py"
V4=ROOT/"canonical/runtime/h100_verified_capability_registry_v4.py"
V5=ROOT/"canonical/runtime/h100_verified_capability_registry_v5.py"
V6=ROOT/"canonical/runtime/h100_verified_capability_registry_v6.py"
V7=ROOT/"canonical/runtime/h100_verified_capability_registry_v7.py"
V8=ROOT/"canonical/runtime/h100_verified_capability_registry_v8.py"

TRANSFER_PRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
TRANSFER_VER=ROOT/"canonical/verification/H100_ZERO_LEARNED_TRANSFER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
CUBIC_PRE=ROOT/"canonical/governance/H100_MINIMAL_PATCH_SEARCH_PRECOMMIT_V1.json"
CUBIC_VER=ROOT/"canonical/verification/H100_MINIMAL_PATCH_SEARCH_SEPARATE_RUNTIME_VERIFICATION_20261005_V1.json"
V3_PRE=ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json"
V3_VER=ROOT/"canonical/verification/H100_GENERIC_PATCH_SEARCH_TRANSFER_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
V4_PRE=ROOT/"canonical/governance/H100_FINITE_GRAMMAR_ESCAPE_PRECOMMIT_V1.json"
V4_VER=ROOT/"canonical/verification/H100_FINITE_GRAMMAR_ESCAPE_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
V5_PRE=ROOT/"canonical/governance/H100_JIT_PRIMITIVE_ACQUISITION_PRECOMMIT_V1.json"
V5_VER=ROOT/"canonical/verification/H100_JIT_PRIMITIVE_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
V6_PRE=ROOT/"canonical/governance/H100_SAFE_STDLIB_OPERATOR_ACQUISITION_PRECOMMIT_V1.json"
V6_VER=ROOT/"canonical/verification/H100_SAFE_STDLIB_OPERATOR_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
V7_PRE=ROOT/"canonical/governance/H100_DECLARATIVE_OPERATOR_PACK_ACQUISITION_PRECOMMIT_V1.json"
V7_VER=ROOT/"canonical/verification/H100_DECLARATIVE_OPERATOR_PACK_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
V8_PRE=ROOT/"canonical/governance/H100_COMPLETE_UNARY_CHAIN_SEARCH_PRECOMMIT_V1.json"
V8_VER=ROOT/"canonical/verification/H100_COMPLETE_UNARY_CHAIN_SEARCH_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

STRICT="STRICT_OUTCOME_SELECTED"
DEV_FIXED="DEVELOPMENT_CONDITIONED_PREOUTCOME_FIXED"
EXTERNAL_FIXED="EXTERNAL_CAPABILITY_DEFINITION_PREOUTCOME_FIXED"
UNRESOLVED="PROVENANCE_UNRESOLVED"


class FullRegistryProvenanceCensusError(ValueError):
    pass


def _j(path:Path)->dict[str,Any]:
    obj=json.loads(path.read_text())
    if not isinstance(obj,dict):
        raise FullRegistryProvenanceCensusError("JSON_OBJECT_REQUIRED:"+str(path))
    return obj


def _src(path:Path)->str:
    return path.read_text()


def _ceil_log2(n:int)->int:
    if not isinstance(n,int) or isinstance(n,bool) or n<1:
        raise FullRegistryProvenanceCensusError("POSITIVE_INTEGER_REQUIRED")
    return 0 if n==1 else (n-1).bit_length()


def _require_all(text:str, needles:list[str], label:str)->None:
    missing=[x for x in needles if x not in text]
    if missing:
        raise FullRegistryProvenanceCensusError(label+"_MISSING:"+",".join(missing))


def v1_rows()->list[dict[str,Any]]:
    src=_src(V1)
    transfer_pre=_j(TRANSFER_PRE)
    transfer_ver=_j(TRANSFER_VER)
    if "FROZEN_BEFORE_OUTCOMES" not in str(transfer_pre.get("status","")):
        raise FullRegistryProvenanceCensusError("V1_TRANSFER_NOT_PREEXPOSED")
    if transfer_ver.get("independently_verified",{}).get("paired_families")!="3_OF_3_PASS":
        raise FullRegistryProvenanceCensusError("V1_TRANSFER_NOT_VERIFIED")

    dev=[
        "CAP_LINEAR_TREND_SINUSOID_V1",
        "CAP_EXP_ABS_V1",
        "CAP_THRESHOLD_STEP_V1",
    ]
    unresolved=[
        "CAP_OEWN_REAL_LEXICAL_V1",
        "CAP_LEXICAL_SOURCE_FALLBACK_V1",
        "CAP_COMPOSITIONAL_LANGUAGE_V1",
        "CAP_TOOL_TRACE_NORMALIZER_V1",
    ]
    _require_all(src,dev+unresolved,"V1_SOURCE")
    return (
        [{
            "capability_id":cid,
            "registry_generation":1,
            "category":DEV_FIXED,
            "basis":"THREE_FAMILY_ROUTE_IS_FROZEN_AROUND_PREDECLARED_SEED_TRANSFER_FAMILIES_BEFORE_OUTCOMES__NO_OUTCOME_SELECTED_PERSISTED_STRUCTURE_IS_CLAIMED_HERE",
            "selection_capacity_bits":None,
        } for cid in dev]
        +
        [{
            "capability_id":cid,
            "registry_generation":1,
            "category":UNRESOLVED,
            "basis":"CURRENT_AUDIT_DOES_NOT_BIND_IMPLEMENTATION_CREATION_TO_A_WORLD_INDEPENDENT_PREDEVELOPMENT_ORIGIN",
            "selection_capacity_bits":None,
        } for cid in unresolved]
    )


def cubic_rows()->tuple[list[dict[str,Any]],dict[str,Any]]:
    pre=_j(CUBIC_PRE); ver=_j(CUBIC_VER); src=_src(V2)
    grammar=list(pre["patch_grammar"])
    selected=str(ver["observed"]["selected_patch_id"])
    if len(grammar)!=3 or selected!="AFFINE_PLUS_X3":
        raise FullRegistryProvenanceCensusError("CUBIC_SELECTION_BINDING_FAILED")
    _require_all(src,["CAP_AFFINE_CUBIC_V1",'"fixed_power":3',"H100_MINIMAL_PATCH_SEARCH_SEPARATE_RUNTIME_VERIFICATION_20261005_V1.json"],"V2_SOURCE")
    bits=_ceil_log2(len(grammar))
    return ([{
        "capability_id":"CAP_AFFINE_CUBIC_V1",
        "registry_generation":2,
        "category":STRICT,
        "basis":"SELECTED_FROM_FROZEN_THREE_PATCH_GRAMMAR_BY_DEVELOPMENT_FIT_AND_TRANSFER_THEN_PERSISTED",
        "selection_capacity_bits":bits,
    }],{
        "id":"CUBIC_V2","candidate_count":len(grammar),"fixed_length_bits":bits
    })


def v3_rows()->tuple[list[dict[str,Any]],dict[str,Any]]:
    pre=_j(V3_PRE); ver=_j(V3_VER); src=_src(V3)
    grammar=list(pre["patch_grammar"])
    compiled=list(ver.get("compile_candidates",[]))
    expected=[
        "CAP_AFFINE_POWER5_V1","CAP_AFFINE_HINGE_V1",
        "CAP_AFFINE_GAUSSIAN_V1","CAP_AFFINE_TANH_V1",
    ]
    if sorted(compiled)!=sorted(expected) or len(grammar)!=6:
        raise FullRegistryProvenanceCensusError("V3_COMPILE_SET_BINDING_FAILED")
    _require_all(src,expected+["FIXED_POWER_5"],"V3_SOURCE")
    support_count=math.comb(len(grammar),len(expected))
    support_bits=_ceil_log2(support_count)
    power_row=next((x for x in grammar if x.get("family_id")=="POWER"),None)
    if not isinstance(power_row,dict):
        raise FullRegistryProvenanceCensusError("V3_POWER_GRAMMAR_MISSING")
    pcount=len(power_row["powers"])
    power_bits=_ceil_log2(pcount)
    aggregate=support_bits+power_bits
    rows=[{
        "capability_id":cid,
        "registry_generation":3,
        "category":STRICT,
        "basis":"FOUR_FAMILIES_SELECTED_BY_FROZEN_MULTI_FAMILY_SEARCH_AND_TRANSFER_THEN_PERSISTED",
        "selection_capacity_bits":None,
    } for cid in expected]
    return rows,{
        "id":"V3_SUPPORT",
        "frozen_family_count":len(grammar),
        "selected_family_count":len(expected),
        "support_set_count":support_count,
        "support_set_bits":support_bits,
        "power_exponent_count":pcount,
        "power_exponent_bits":power_bits,
        "aggregate_fixed_length_bits":aggregate,
        "note":"AGGREGATE_CODE_RECONSTRUCTS_THE_PERSISTED_V3_SUPPORT_SET_PLUS_POWER5_IDENTITY_RELATIVE_TO_FROZEN_GRAMMAR",
    }


def v4_rows()->tuple[list[dict[str,Any]],dict[str,Any]]:
    pre=_j(V4_PRE); ver=_j(V4_VER); src=_src(V4)
    if not bool(pre["transfer_task"]["frozen_before_seed_search_outcome"]):
        raise FullRegistryProvenanceCensusError("V4_TRANSFER_NOT_FROZEN")
    obs=ver["observed"]
    n=int(obs["seed_candidate_count"])
    if n!=2822:
        raise FullRegistryProvenanceCensusError("V4_CANDIDATE_COUNT_CHANGED")
    _require_all(src,["CAP_AFFINE_RATIONAL_SAT_SQUARE_V1","\"op\":\"sat\"","\"op\":\"square\""],"V4_SOURCE")
    bits=_ceil_log2(n)
    return ([{
        "capability_id":"CAP_AFFINE_RATIONAL_SAT_SQUARE_V1",
        "registry_generation":4,
        "category":STRICT,
        "basis":"BROADER_EXPRESSION_SEARCH_SELECTED_FEATURE_STRUCTURE_FROM_FROZEN_FINITE_CANDIDATE_SET_THEN_TRANSFERRED_AND_PERSISTED",
        "selection_capacity_bits":bits,
    }],{
        "id":"RATIONAL_V4","candidate_count":n,"fixed_length_bits":bits
    })


def external_rows()->list[dict[str,Any]]:
    p5=_j(V5_PRE); v5=_j(V5_VER); s5=_src(V5)
    if p5["primitive_descriptor"]["module"]!="math" or p5["primitive_descriptor"]["attribute"]!="erf":
        raise FullRegistryProvenanceCensusError("V5_DESCRIPTOR_CHANGED")
    _require_all(s5,["CAP_AFFINE_ERF_V1","math.erf"],"V5_SOURCE")

    p6=_j(V6_PRE); v6=_j(V6_VER); s6=_src(V6)
    attrs=[str(x["attribute"]) for x in p6["operators"]]
    if attrs!=["atan","tanh"]:
        raise FullRegistryProvenanceCensusError("V6_OPERATORS_CHANGED")
    _require_all(s6,["CAP_AFFINE_ATAN_V1","CAP_AFFINE_TANH_V1"],"V6_SOURCE")

    p7=_j(V7_PRE); v7=_j(V7_VER); s7=_src(V7)
    packs=list(p7["packs"])
    if len(packs)!=2 or any(not str(x.get("git_blob_sha","")) for x in packs):
        raise FullRegistryProvenanceCensusError("V7_PACK_BINDING_CHANGED")
    _require_all(s7,["CAP_AFFINE_ASYM_CLAMP_V1","CAP_AFFINE_TRIANGLE_V1","pack_git_blob_sha"],"V7_SOURCE")

    return [
        {
            "capability_id":"CAP_AFFINE_ERF_V1","registry_generation":5,
            "category":EXTERNAL_FIXED,
            "basis":"MATH_ERF_DESCRIPTOR_FROZEN_BEFORE_TASK_OUTCOMES__EXTERNAL_STDLIB_DEFINITION",
            "selection_capacity_bits":None,
        },
        {
            "capability_id":"CAP_AFFINE_ATAN_V1","registry_generation":6,
            "category":EXTERNAL_FIXED,
            "basis":"MATH_ATAN_DESCRIPTOR_FROZEN_BEFORE_TASK_OUTCOMES__EXTERNAL_STDLIB_DEFINITION",
            "selection_capacity_bits":None,
        },
        {
            "capability_id":"CAP_AFFINE_TANH_V1","registry_generation":6,
            "category":EXTERNAL_FIXED,
            "basis":"MATH_TANH_DESCRIPTOR_FROZEN_BEFORE_TASK_OUTCOMES__EXTERNAL_STDLIB_DEFINITION",
            "selection_capacity_bits":None,
        },
        {
            "capability_id":"CAP_AFFINE_ASYM_CLAMP_V1","registry_generation":7,
            "category":EXTERNAL_FIXED,
            "basis":"CONTENT_ADDRESSED_DECLARATIVE_PACK_FROZEN_BEFORE_TASK_OUTCOMES",
            "selection_capacity_bits":None,
        },
        {
            "capability_id":"CAP_AFFINE_TRIANGLE_V1","registry_generation":7,
            "category":EXTERNAL_FIXED,
            "basis":"CONTENT_ADDRESSED_DECLARATIVE_PACK_FROZEN_BEFORE_TASK_OUTCOMES",
            "selection_capacity_bits":None,
        },
    ]


def v8_rows()->tuple[list[dict[str,Any]],dict[str,Any]]:
    pre=_j(V8_PRE); ver=_j(V8_VER); src=_src(V8)
    n=int(pre["expected_enumeration_count"]["cumulative_through_depth4"])
    task_count=len(pre["fresh_tasks"])
    if n!=1554 or task_count!=3 or not bool(ver["observed"]["all_depth4_exact_count_one"]):
        raise FullRegistryProvenanceCensusError("V8_SELECTION_BINDING_FAILED")
    ids=[
        "CAP_AFFINE_CHAIN_SQUARE_LOG_SQRT_SAT_V1",
        "CAP_AFFINE_CHAIN_SAT_SQUARE_LOG_SQRT_V1",
        "CAP_AFFINE_CHAIN_LOG_SAT_SQRT_LOG_V1",
    ]
    _require_all(src,ids+["H100_COMPLETE_UNARY_CHAIN_SEARCH_SECOND_CARRIER_VERIFICATION_20261005_V1.json"],"V8_SOURCE")
    bits=_ceil_log2(n)
    return ([{
        "capability_id":cid,
        "registry_generation":8,
        "category":STRICT,
        "basis":"ONE_UNIQUE_DEPTH4_CHAIN_SELECTED_FROM_1554_FROZEN_CANDIDATES_FOR_FIXED_TASK_THEN_PERSISTED",
        "selection_capacity_bits":bits,
    } for cid in ids],{
        "id":"DEPTH4_V8",
        "candidate_count_per_task":n,
        "task_count":task_count,
        "fixed_length_bits_per_task":bits,
        "aggregate_fixed_length_bits":bits*task_count,
    })


def run()->dict[str,Any]:
    rows=v1_rows()
    c,ccode=cubic_rows(); rows.extend(c)
    x,v3code=v3_rows(); rows.extend(x)
    x,v4code=v4_rows(); rows.extend(x)
    rows.extend(external_rows())
    x,v8code=v8_rows(); rows.extend(x)

    ids=[x["capability_id"] for x in rows]
    if len(ids)!=21:
        raise FullRegistryProvenanceCensusError("REGISTRY_RECORD_CENSUS_NOT_21")
    by_id={}
    for row in rows:
        by_id.setdefault(row["capability_id"],[]).append(row)
    collisions={
        cid:[
            {"registry_generation":r["registry_generation"],"category":r["category"]}
            for r in rs
        ]
        for cid,rs in by_id.items() if len(rs)>1
    }
    if set(collisions)!={"CAP_AFFINE_TANH_V1"}:
        raise FullRegistryProvenanceCensusError("UNEXPECTED_STABLE_ID_COLLISION_SET")
    tanh=collisions["CAP_AFFINE_TANH_V1"]
    if sorted(x["registry_generation"] for x in tanh)!=[3,6]:
        raise FullRegistryProvenanceCensusError("TANH_COLLISION_GENERATIONS_CHANGED")

    counts={k:sum(1 for x in rows if x["category"]==k) for k in (STRICT,DEV_FIXED,EXTERNAL_FIXED,UNRESOLVED)}
    strict_bits=ccode["fixed_length_bits"]+v3code["aggregate_fixed_length_bits"]+v4code["fixed_length_bits"]+v8code["aggregate_fixed_length_bits"]
    strict_bytes=(strict_bits+7)//8

    return {
        "schema":SCHEMA,
        "status":"PASS__FULL_21_RECORD_DUAL_LEDGER_PROVENANCE_CENSUS__20_STABLE_IDS__ONE_TANH_ID_COLLISION__STRICT_OUTCOME_SELECTED_CODE_CAPACITY_54_BITS__ZERO_TERMINAL_CREDIT",
        "entry_count":len(rows),
        "unique_stable_capability_id_count":len(by_id),
        "stable_id_collisions":collisions,
        "census_identity_rule":"REGISTRY_GENERATION_PLUS_CAPABILITY_ID",
        "rows":rows,
        "category_counts":counts,
        "strict_selection_codes":[ccode,v3code,v4code,v8code],
        "strict_outcome_selected_compact_code":{
            "aggregate_fixed_length_bits":strict_bits,
            "ceil_bytes":strict_bytes,
            "interpretation":"COMPACT_INDEX_CODE_RELATIVE_TO_FROZEN_SEARCH_UNIVERSES__UPPER_BOUND_FOR_THE_AUDITED_STRICT_SELECTION_IDENTITIES__NOT_EXACT_MUTUAL_INFORMATION",
        },
        "ledger_summary":{
            "syntactic_v0_zero_learned_claim_for_registry":True,
            "provenance_v1_zero_learned_claim_for_registry":False,
            "strict_outcome_selected_entry_count":counts[STRICT],
            "development_conditioned_preoutcome_fixed_entry_count":counts[DEV_FIXED],
            "external_capability_definition_preoutcome_fixed_entry_count":counts[EXTERNAL_FIXED],
            "provenance_unresolved_entry_count":counts[UNRESOLVED],
            "stable_capability_id_collision_count":len(collisions),
            "exact_total_provenance_v1_learned_bits":None,
        },
        "hard_nonclaims":[
            "54_BITS_IS_NOT_A_MUTUAL_INFORMATION_LOWER_BOUND",
            "54_BITS_DOES_NOT_INCLUDE_DEVELOPMENT_CONDITIONED_PREOUTCOME_FIXED_OR_EXTERNAL_ACQUISITION_MEMBERSHIP_DECISIONS",
            "UNRESOLVED_ENTRIES_ARE_NOT_ASSUMED_ZERO",
            "EXTERNAL_CAPABILITY_DEFINITIONS_ARE_NOT_RELABELED_LEARNED_MERELY_BY_PERSISTENCE",
            "STABLE_CAPABILITY_ID_IS_NOT_USED_AS_A_UNIQUE_PROVENANCE_KEY_WHEN_GENERATIONS_COLLIDE",
            "NO_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))

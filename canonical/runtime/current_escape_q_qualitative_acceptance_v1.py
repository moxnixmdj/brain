"""Current Escape Q qualitative-acceptance theorem projection.

Binds the two current qualitative acceptance rows to the already-proved
acceptance-relation uncertainty theorem and qualitative prompt non-entailment
boundary. This module proves only the shared Q closure law and sound next
routes. It grants no row acceptance, capability, ownership, or terminal credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CURRENT_ESCAPE_Q_QUALITATIVE_ACCEPTANCE_V1"
ROOT=Path(__file__).resolve().parents[2]

CURRENT_OQ_PATH=ROOT/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"
FROZEN_CLASSIFICATION_PATH=ROOT/"canonical/governance/FROZEN_18_ACCEPTANCE_REGIME_EXHAUSTIVE_CLASSIFICATION_20261007_V1.json"
RELATION_THEOREM_PATH=ROOT/"canonical/governance/ACCEPTANCE_RELATION_UNCERTAINTY_NORMAL_FORM_20261007_V1.json"
NONENTAILMENT_CUT_PATH=ROOT/"canonical/governance/QUALITATIVE_PAIRWISE_PROMPT_NONENTAILMENT_CUT_20261007_V1.json"
ROBUST_POLICY_RUNTIME_PATH=ROOT/"canonical/runtime/robust_common_policy_db_admission_v1.py"
NONENTAILMENT_RUNTIME_PATH=ROOT/"canonical/runtime/qualitative_pairwise_prompt_nonentailment_v1.py"

EXPECTED_IMMUTABLE_BLOBS={
    "frozen_classification":"dc9f0c5147349fa806d2a0296a8139c637d85b83",
    "relation_theorem":"42498bbe40327cd47be5e4251e7f524a8c0c8d5b",
    "nonentailment_cut":"bd1018b320418aeaa8aa6a06cd8df85521bad2b8",
    "robust_policy_runtime":"3424c7844d227ab56fbb7ea99c5b202154dbf40c",
    "nonentailment_runtime":"2d309030afa3dc189579a8d989dfb52614063adf",
}


def _git_blob_sha_bytes(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "shared_q_acceptance_law_bound":False,
        "all_current_q_rows_closed":False,
        "current_q_row_acceptance_closed_count":0,
        "prompt_metadata_alone_sufficient":False,
        "row_credit_delta":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "terminal_credit_delta":0,
    }
    out.update(detail)
    return out


def evaluate(
    oq:Mapping[str,Any],
    frozen:Mapping[str,Any],
    theorem:Mapping[str,Any],
    cut:Mapping[str,Any],
)->dict[str,Any]:
    reduction=oq.get("reduction")
    if not isinstance(reduction,Mapping):
        return _fail("CURRENT_OQ_REDUCTION_MISSING")

    q_raw=reduction.get("Q_rows")
    if not isinstance(q_raw,list) or not all(isinstance(x,str) and x.strip() for x in q_raw):
        return _fail("CURRENT_Q_ROWS_INVALID")
    q_rows=[x.strip() for x in q_raw]
    if len(q_rows)!=len(set(q_rows)):
        return _fail("CURRENT_Q_ROWS_DUPLICATE")

    if reduction.get("Q_QUALITATIVE_RELATIVE_ORDER")!=len(q_rows):
        return _fail("CURRENT_Q_COUNT_MISMATCH")
    o_count=reduction.get("O_OBJECTIVE_ACCEPTANCE")
    total=reduction.get("current_frontier_row_count")
    if not isinstance(o_count,int) or not isinstance(total,int) or o_count+len(q_rows)!=total:
        return _fail("CURRENT_O_Q_TOTAL_MISMATCH")
    if reduction.get("mixed")!=0 or reduction.get("unclassified")!=0:
        return _fail("CURRENT_O_Q_NOT_EXHAUSTIVE")

    frozen_rows=frozen.get("exhaustive_rows")
    if not isinstance(frozen_rows,list):
        return _fail("FROZEN_ACCEPTANCE_ROWS_INVALID")
    frozen_q=set()
    for row in frozen_rows:
        if not isinstance(row,Mapping):
            return _fail("FROZEN_ACCEPTANCE_ROW_INVALID")
        oid=row.get("obligation")
        regime=row.get("regime")
        if regime=="Q_QUALITATIVE_RELATIVE_ORDER":
            if not isinstance(oid,str) or not oid.strip():
                return _fail("FROZEN_Q_OBLIGATION_INVALID")
            frozen_q.add(oid.strip())

    missing=sorted(set(q_rows)-frozen_q)
    if missing:
        return _fail(
            "CURRENT_Q_ROW_OUTSIDE_FROZEN_Q_UNIVERSE",
            current_q_count=len(q_rows),
            current_q_rows=q_rows,
            missing_from_frozen_q_universe=missing,
        )

    theorem_text=theorem.get("theorem")
    special=theorem.get("special_cases")
    if not isinstance(theorem_text,str) or not theorem_text.strip():
        return _fail("ACCEPTANCE_RELATION_THEOREM_INVALID")
    if not isinstance(special,Mapping) or not isinstance(special.get("Q_QUALITATIVE_RELATIVE_ORDER"),str):
        return _fail("Q_SPECIAL_CASE_MISSING")

    mic=cut.get("minimum_information_cut")
    if not isinstance(mic,Mapping):
        return _fail("Q_NONENTAILMENT_MINIMUM_INFORMATION_CUT_MISSING")
    sufficient=mic.get("sufficient_disjunction")
    if not isinstance(sufficient,list) or len(sufficient)<3 or not all(isinstance(x,str) and x for x in sufficient):
        return _fail("Q_NONENTAILMENT_SUFFICIENT_DISJUNCTION_INVALID")

    required_tokens=(
        "AUTHENTIC_TARGET_JUDGE_OUTCOME_OR_EXTENSIONALLY_EQUIVALENT_TARGET_RELATION_INFORMATION",
        "CONTENT_ADDRESSED_JUDGE_SEMANTICS_STRONG_ENOUGH_TO_DERIVE_THE_RELEVANT_PAIRWISE_OUTCOME",
        "EVALUATOR_ROBUST_SCOPE_COMPLETE_BRAIN_DOMINANCE_OR_UNIVERSAL_TOP_SUPPORT",
    )
    if any(not any(token in item for item in sufficient) for token in required_tokens):
        return _fail("Q_NONENTAILMENT_SOUND_CLOSURE_DISJUNCTION_DRIFT")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__CURRENT_Q2_BOUND_TO_ACCEPTANCE_RELATION_UNCERTAINTY_LAW__PROMPT_NONENTAILMENT_PRESERVED__ZERO_ROW_CREDIT",
        "current_q_count":len(q_rows),
        "current_q_rows":q_rows,
        "missing_from_frozen_q_universe":[],
        "shared_q_acceptance_law_bound":True,
        "acceptance_relation_theorem":theorem_text,
        "q_special_case":special["Q_QUALITATIVE_RELATIVE_ORDER"],
        "prompt_metadata_alone_sufficient":False,
        "sound_closure_routes":[
            "ROBUST_COMMON_POLICY",
            "BOUND_JUDGE_SEMANTICS_SUFFICIENT_TO_DERIVE_RELEVANT_OUTCOME",
            "MINIMUM_AUTHENTIC_RELATION_INFORMATION",
            "EVALUATOR_ROBUST_SCOPE_COMPLETE_DOMINANCE_OR_UNIVERSAL_TOP_SUPPORT",
        ],
        "open_q_rows":q_rows,
        "all_current_q_rows_closed":False,
        "current_q_row_acceptance_closed_count":0,
        "row_proof_authority":False,
        "caller_asserted_q_closure_authority":False,
        "next_required_edge":"FOR_EACH_CURRENT_Q_CLASS__FIRST_SEARCH_FOR_ONE_BRAIN_OWNED_POLICY_PROVED_ADEQUATE_OVER_A_SOUND_SCOPE_COMPLETE_ACCEPTANCE_RELATION_OVERAPPROXIMATION__IF_NONE_EXISTS_ACQUIRE_ONLY_THE_MINIMUM_AUTHENTIC_RELATION_OR_JUDGE_SEMANTICS_INFORMATION_THAT_CHANGES_POLICY_ADEQUACY",
        "row_credit_delta":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "terminal_credit_delta":0,
    }


def evaluate_current()->dict[str,Any]:
    try:
        immutable_docs=[
            (FROZEN_CLASSIFICATION_PATH,EXPECTED_IMMUTABLE_BLOBS["frozen_classification"]),
            (RELATION_THEOREM_PATH,EXPECTED_IMMUTABLE_BLOBS["relation_theorem"]),
            (NONENTAILMENT_CUT_PATH,EXPECTED_IMMUTABLE_BLOBS["nonentailment_cut"]),
        ]
        immutable_runtime=[
            (ROBUST_POLICY_RUNTIME_PATH,EXPECTED_IMMUTABLE_BLOBS["robust_policy_runtime"]),
            (NONENTAILMENT_RUNTIME_PATH,EXPECTED_IMMUTABLE_BLOBS["nonentailment_runtime"]),
        ]
        docs=[]
        for path,expected in immutable_docs:
            raw=path.read_bytes()
            actual=_git_blob_sha_bytes(raw)
            if actual!=expected:
                return _fail(
                    "IMMUTABLE_Q_SOURCE_BLOB_DRIFT",
                    path=str(path.relative_to(ROOT)),
                    expected_git_blob_sha=expected,
                    actual_git_blob_sha=actual,
                )
            docs.append(json.loads(raw.decode("utf-8")))
        for path,expected in immutable_runtime:
            raw=path.read_bytes()
            actual=_git_blob_sha_bytes(raw)
            if actual!=expected:
                return _fail(
                    "IMMUTABLE_Q_RUNTIME_BLOB_DRIFT",
                    path=str(path.relative_to(ROOT)),
                    expected_git_blob_sha=expected,
                    actual_git_blob_sha=actual,
                )
        oq=_load(CURRENT_OQ_PATH)
    except Exception as exc:
        return _fail("CURRENT_Q_PROJECTION_SOURCE_LOAD_FAILED",detail=str(exc))
    frozen,theorem,cut=docs
    return evaluate(oq,frozen,theorem,cut)

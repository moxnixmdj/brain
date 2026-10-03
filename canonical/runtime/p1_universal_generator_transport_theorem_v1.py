"""Zero-reality universal P1 failure-semantics transport theorem.

Proves the exact frozen contract-native P1 generator collapses to a finite set of
structural equivalence classes and that every such class is correctly transported
through the public-only binder, V7 candidate, V6 intervention scorer, and native
rescue scorer. The quarantined run 37108111537 is deliberately not read.
"""
from __future__ import annotations
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_UNIVERSAL_GENERATOR_TRANSPORT_THEOREM_V1"
EXPECTED={
 "canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
 "canonical/runtime/p1_shared_failure_semantics_batch_v1.py":"695cfe3f283723a52bafb6299236a2d0378dc79e",
 "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py":"b6ba06fc6a35fa132eb19389ee256e74a63a4849",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":"28940387bd6c11671035ad9201e37bba13fd9bc9",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":"0f41a36e6ad16722ce05b180e036fb921a2ef886",
}
QUARANTINED_RUN_ID=37108111537

def _blob(path: str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class _SymbolicRng:
    def __init__(self,cause:int,reverse_shuffle:bool=False):
        self.cause=cause
        self.reverse_shuffle=reverse_shuffle
        self.calls:list[tuple[Any,...]]=[]
    def randint(self,a:int,b:int)->int:
        self.calls.append(("randint",a,b))
        assert a<=self.cause<=b,(a,self.cause,b)
        return self.cause
    def shuffle(self,seq:list[Any])->None:
        self.calls.append(("shuffle",len(seq)))
        if self.reverse_shuffle:
            seq.reverse()

def _one(surface:str,index:int,difficulty:int,cause:int,reverse_shuffle:bool)->dict[str,Any]:
    holder:dict[str,_SymbolicRng]={}
    old=source._rng
    def fake_rng(seed:int):
        r=_SymbolicRng(cause,reverse_shuffle)
        holder["rng"]=r
        return r
    source._rng=fake_rng
    try:
        verdict=batch.evaluate_one(
            beacon="P1_UNIVERSAL_ZERO_REALITY_SYMBOLIC_CLASS_V1",
            surface_id=surface,
            case_index=index,
        )
        # Independently obtain the exact source case to verify generator structure
        # and the complete source of stochasticity for this equivalence class.
        full=source.generate_case(batch.CONTRACT,123456789,difficulty)
    finally:
        source._rng=old

    rng=holder["rng"]
    n=max(5,min(14,6+difficulty))
    expected_calls=[("randint",1,n-3),("shuffle",n-1-cause)]
    assert rng.calls==expected_calls,(rng.calls,expected_calls)

    traj=full["task"]["trajectory"]
    assert len(traj)==n
    assert full["_oracle"]=={"cause_step":cause,"repair_id":f"repair_{cause}"}
    for i,row in enumerate(traj):
        assert row["step"]==i and row["action"]==f"A{i}"
        if i<cause:
            assert (row["state"],row["invariant_pass"],row["terminal_symptom"])==("OK",True,False)
        elif i==cause:
            assert (row["state"],row["invariant_pass"],row["terminal_symptom"])==("FAULT_INJECTED",False,False)
        else:
            assert (row["state"],row["invariant_pass"],row["terminal_symptom"])==("DOWNSTREAM_DEGRADED",False,True)

    assert verdict["pass"] is True,verdict
    assert verdict["candidate_status"]=="IDENTIFIED",verdict
    assert verdict["semantics_counts"]=={
        "DIRECT_CONTRACT":1,
        "DERIVED_UPSTREAM":n-cause-1,
    },verdict
    assert verdict["v7_intervention_scorer_pass"] is True
    assert verdict["source_native_rescue_scorer_pass"] is True
    assert verdict["source_native_rescue_pass"] is True
    return {
        "surface":surface,"case_index":index,"difficulty":difficulty,
        "n":n,"cause":cause,"reverse_shuffle":reverse_shuffle,
        "pass":True,
    }

def evaluate()->dict[str,Any]:
    drift={p:{"expected":h,"actual":_blob(p)} for p,h in EXPECTED.items() if _blob(p)!=h}
    if drift:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT",
          "pass":False,"drift":drift,"new_reality_units_consumed":0,
          "capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }

    # Static load-bearing facts: the binder never consumes repair-candidate order,
    # and source randomness in _trajectory_case is restricted to cause choice plus
    # repair-list shuffle. Exact blobs above make these source-text claims immutable.
    binder_text=inspect.getsource(batch.bind_public_source_case)
    gen_text=inspect.getsource(source._trajectory_case)
    assert "repair_candidates" not in binder_text
    assert "r.randint(1,n-3)" in gen_text.replace(" ","")
    assert "r.shuffle(repairs)" in gen_text.replace(" ","")

    rows=[]
    structural=set()
    # Exhaust every case index that the frozen batch can select, every possible
    # cause position for that index's difficulty, all 3 frozen surfaces, and two
    # extreme repair orderings. Repair order is proven non-load-bearing above.
    for surface in batch.SURFACES:
        for index in range(batch.CASES_PER_SURFACE):
            difficulty=batch.DIFFICULTIES[index%len(batch.DIFFICULTIES)]
            n=max(5,min(14,6+difficulty))
            for cause in range(1,n-2):
                for reverse in (False,True):
                    row=_one(surface,index,difficulty,cause,reverse)
                    rows.append(row)
                    structural.add((difficulty,n,cause))

    expected_structural={(d,6+d,c) for d in range(1,6) for c in range(1,(6+d)-2)}
    assert structural==expected_structural,(len(structural),len(expected_structural))
    # 4+5+6+7+8 = 30 semantic trajectory classes.
    assert len(structural)==30
    assert all(x["pass"] for x in rows)

    return {
      "schema":SCHEMA,
      "status":"PASS__UNIVERSAL_OVER_ALL_FROZEN_GENERATOR_STRUCTURAL_EQUIVALENCE_CLASSES__ZERO_REALITY",
      "pass":True,
      "behavior_id":batch.CONTRACT,
      "proof_domain":"ALL_CASES_GENERATABLE_BY_EXACT_FROZEN_CONTRACT_NATIVE_P1_SOURCE_GENERATOR_FOR_DIFFICULTY_1_TO_5__ALL_64_FROZEN_CASE_INDICES__ALL_3_FROZEN_DIRECT_SURFACES",
      "source_blob_bindings":EXPECTED,
      "structural_equivalence_classes":len(structural),
      "surface_count":len(batch.SURFACES),
      "case_indices_per_surface":batch.CASES_PER_SURFACE,
      "shuffle_extremes_per_class":2,
      "deterministic_proof_executions":len(rows),
      "generator_randomness_classification":"SEMANTIC_TRAJECTORY_DEPENDS_ONLY_ON_CAUSE_POSITION__REPAIR_ORDER_SHUFFLE_IS_BINDER_IRRELEVANT",
      "semantic_theorem":[
        "EXACTLY_ONE_FAILED_PUBLIC_STATE_IS_FAULT_INJECTED_AND_BINDS_DIRECT_CONTRACT",
        "EVERY_LATER_FAILED_PUBLIC_STATE_IS_DOWNSTREAM_DEGRADED_AND_BINDS_DERIVED_UPSTREAM",
        "V7_THEREFORE_HAS_EXACTLY_ONE_DIRECT_FAILURE_ON_THE_TERMINAL_CAUSAL_SLICE",
        "V7_IDENTIFIES_A_CAUSE_AND_PROPOSES_RESTORE_A_CAUSE_INVARIANT",
        "NATIVE_SOURCE_ORACLE_CAUSE_AND_REPAIR_ARE_THE_SAME_CAUSE_INDEX",
        "V6_INTERVENTION_AND_NATIVE_RESCUE_SCORERS_PASS_FOR_EVERY_GENERATOR_CLASS",
      ],
      "quarantined_execution_used_as_proof":False,
      "quarantined_execution_run_id":QUARANTINED_RUN_ID,
      "terminal_results_replayed":0,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "next":"INDEPENDENTLY_VERIFY_EXACT_BYTES_AND_THEOREM__THEN_TEST_SCOPE_RELATION_TO_ALL_THREE_P1_FAILURE_SEMANTICS_TRANSPORT_REQUIREMENTS__NO_CREDIT_FROM_QUARANTINED_RUN",
      "hard_nonclaims":[
        "NO_USE_OF_RUN_37108111537_AS_ACCEPTANCE_EVIDENCE",
        "NO_CLAIM_OUTSIDE_EXACT_FROZEN_CONTRACT_NATIVE_GENERATOR",
        "NO_P1_QUARANTINE_LIFT_WITHOUT_INDEPENDENT_SCOPE_REDUCTION",
      ],
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__=="__main__":
    raise SystemExit(main())

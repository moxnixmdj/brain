"""P1 one-batch fresh failure-semantics harness V1.

This module freezes the zero-cost program-side harness for the exact one-reality-unit
P1 cut. It deliberately does NOT choose the terminal beacon. Terminal execution is
valid only after this package is frozen/independently verified and an uncontrollable
post-freeze public beacon receipt is supplied.

The fresh population is 3 surfaces x 8 failure kinds x 4 causal patterns = 96 cells.
The beacon changes structural details inside each predeclared cell. Failure semantics
are derived from instrumentation provenance before the candidate sees the case.
The exact V7 candidate and exact inherited V6 intervention-rescue scorer are reused.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.trajectory_failure_typed_ir_candidate_v7 import solve
from canonical.runtime.trajectory_failure_typed_ir_proof_v6 import score_case

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_SHARED_FRESH_FAILURE_SEMANTICS_BATCH_V1"

SURFACES=(
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
KINDS=(
    "AUTHORITY","SCOPE","SCHEMA","PROVENANCE",
    "INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY",
)
PATTERNS=("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")
ORIGIN_DIRECT="LOCAL_CONTRACT_INSTRUMENTATION"
ORIGIN_DERIVED="UPSTREAM_PROPAGATION_INSTRUMENTATION"
SEMANTICS_BY_ORIGIN={
    ORIGIN_DIRECT:"DIRECT_CONTRACT",
    ORIGIN_DERIVED:"DERIVED_UPSTREAM",
}

PINNED_BLOBS={
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":
        "28940387bd6c11671035ad9201e37bba13fd9bc9",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":
        "0f41a36e6ad16722ce05b180e036fb921a2ef886",
    "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json":
        "75cd1ad0ec0739ebd894cf6075af5837b93d83f8",
    "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":
        "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    "canonical/governance/P1_MINIMUM_REALITY_CUT_INPUT_V1.json":
        "cbcb2faff8404623846e77e19fcc5b0ad00e81d9",
    "canonical/verification/P1_V7_CURRENT_MAIN_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":
        "4e8cf594503a216302a1d61c2009945131d86041",
    "canonical/verification/P1_V7_PROVENANCE_AND_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "01ca625add4db7035224f0d4cb9efb406d17362d",
}

def _blob_sha(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _cell_seed(beacon:str,surface:str,kind:str,pattern:str)->int:
    if not isinstance(beacon,str) or len(beacon)<16:
        raise ValueError("BEACON_TOO_SHORT")
    payload="|".join((SCHEMA,beacon,surface,kind,pattern)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")

def _check(kind:str, aid:str, passed:bool, origin:str|None=None)->dict[str,Any]:
    row={
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":bool(passed),
        "evidence":[] if passed else [
            f"instrument:{aid}:{kind}",
            f"receipt:{aid}:{kind}",
        ],
    }
    if not passed:
        if origin not in SEMANTICS_BY_ORIGIN:
            raise ValueError("FAILED_CHECK_ORIGIN_INVALID")
        row["_instrumentation_failure_origin"]=origin
    return row

def _normalize_check(row:Mapping[str,Any])->dict[str,Any]:
    out={k:copy.deepcopy(v) for k,v in row.items() if k!="_instrumentation_failure_origin"}
    if out.get("pass") is False:
        origin=row.get("_instrumentation_failure_origin")
        semantics=SEMANTICS_BY_ORIGIN.get(str(origin))
        if semantics is None:
            raise ValueError("UNBOUND_FAILURE_SEMANTICS")
        out["failure_semantics"]=semantics
    else:
        out["failure_semantics"]="DIRECT_CONTRACT"
    return out

def _raw_row(
    aid:str,
    *,
    reads:list[str],
    writes:list[str],
    depends_on:list[str],
    failed_kind:str|None=None,
    failure_origin:str|None=None,
    composition:str="SEQUENTIAL",
)->dict[str,Any]:
    checks=[_check("INVARIANT",aid,True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind,aid,False,failure_origin))
    return {
        "action_id":aid,
        "reads":reads,
        "writes":writes,
        "depends_on":depends_on,
        "dependency_composition":composition,
        "checks":checks,
    }

def _normalize_case(raw:Mapping[str,Any])->dict[str,Any]:
    task=raw["task"]
    rows=[]
    for source in task["trajectory"]:
        row={k:copy.deepcopy(v) for k,v in source.items() if k!="checks"}
        row["checks"]=[_normalize_check(x) for x in source["checks"]]
        rows.append(row)
    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "surface_id":raw["surface_id"],
        "cell_id":raw["cell_id"],
        "seed":raw["seed"],
        "task":{
            "domain":task["domain"],
            "trajectory":rows,
            "terminal_failed_resources":copy.deepcopy(task["terminal_failed_resources"]),
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
        "_oracle":copy.deepcopy(raw["_oracle"]),
    }

def _generate_raw(beacon:str,surface:str,kind:str,pattern:str)->dict[str,Any]:
    if surface not in SURFACES or kind not in KINDS or pattern not in PATTERNS:
        raise ValueError("CELL_OUTSIDE_FROZEN_MATRIX")
    seed=_cell_seed(beacon,surface,kind,pattern)
    r=random.Random(seed)
    domain="CODE" if surface.startswith("T0/") else "TOOL_API"
    prefix=hashlib.sha256(f"{surface}|{seed}".encode()).hexdigest()[:10]
    rows:list[dict[str,Any]]=[]
    counter=0

    def add(*,reads,writes,deps,failed=None,origin=None,composition="SEQUENTIAL")->str:
        nonlocal counter
        aid=f"A{counter}"
        counter+=1
        rows.append(_raw_row(
            aid,reads=list(reads),writes=list(writes),depends_on=list(deps),
            failed_kind=failed,failure_origin=origin,composition=composition,
        ))
        return aid

    seed_res=f"{prefix}:seed"
    root0=add(reads=[],writes=[seed_res],deps=[])

    # Beacon-dependent neutral prefix. It changes causal distance without changing
    # which local checks are direct contract facts.
    prev=root0
    prev_res=seed_res
    for i in range(r.randint(0,3)):
        out=f"{prefix}:pre:{i}"
        prev=add(reads=[prev_res],writes=[out],deps=[prev])
        prev_res=out

    oracle:dict[str,Any]

    if pattern in {"SINGLE","DELAYED"}:
        root_res=f"{prefix}:root"
        root=add(
            reads=[prev_res],writes=[root_res],deps=[prev],
            failed=kind,origin=ORIGIN_DIRECT,
        )
        derived_count=r.randint(1,2) if pattern=="SINGLE" else r.randint(3,7)
        cur=root
        cur_res=root_res
        for i in range(derived_count):
            out=f"{prefix}:derived:{i}"
            cur=add(
                reads=[cur_res],writes=[out],deps=[cur],
                failed="INVARIANT",origin=ORIGIN_DERIVED,
            )
            cur_res=out
        terminal=f"{prefix}:terminal"
        add(reads=[cur_res],writes=[terminal],deps=[cur])
        oracle={
            "status":"IDENTIFIED",
            "roots":[root],
            "critical":root,
            "mechanisms":{root:[kind]},
        }

    else:
        kind2=KINDS[(KINDS.index(kind)+1+r.randint(0,len(KINDS)-2))%len(KINDS)]
        if kind2==kind:
            kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
        left_res=f"{prefix}:left"
        right_res=f"{prefix}:right"
        left=add(
            reads=[prev_res],writes=[left_res],deps=[prev],
            failed=kind,origin=ORIGIN_DIRECT,
        )
        right=add(
            reads=[prev_res],writes=[right_res],deps=[prev],
            failed=kind2,origin=ORIGIN_DIRECT,
        )

        # Independently vary branch delay to prevent a fixed positional shortcut.
        left_end,left_end_res=left,left_res
        for i in range(r.randint(0,3)):
            out=f"{prefix}:left-delay:{i}"
            left_end=add(reads=[left_end_res],writes=[out],deps=[left_end])
            left_end_res=out
        right_end,right_end_res=right,right_res
        for i in range(r.randint(0,3)):
            out=f"{prefix}:right-delay:{i}"
            right_end=add(reads=[right_end_res],writes=[out],deps=[right_end])
            right_end_res=out

        merge_res=f"{prefix}:merge"
        merge=add(
            reads=[left_end_res,right_end_res],writes=[merge_res],
            deps=[left_end,right_end],
            composition="CONJUNCTIVE" if pattern=="INTERACTION" else "ALTERNATIVE",
        )
        symptom_res=f"{prefix}:symptom"
        symptom=add(
            reads=[merge_res],writes=[symptom_res],deps=[merge],
            failed="INVARIANT",origin=ORIGIN_DERIVED,
        )
        tail=symptom
        tail_res=symptom_res
        for i in range(r.randint(0,3)):
            out=f"{prefix}:tail:{i}"
            tail=add(reads=[tail_res],writes=[out],deps=[tail])
            tail_res=out
        terminal=f"{prefix}:terminal"
        add(reads=[tail_res],writes=[terminal],deps=[tail])

        if pattern=="INTERACTION":
            oracle={
                "status":"INTERACTION",
                "roots":[left,right],
                "critical":left,
                "mechanisms":{left:[kind],right:[kind2]},
            }
        else:
            oracle={
                "status":"AMBIGUOUS",
                "roots":[left,right],
                "critical":None,
                "mechanisms":{left:[kind],right:[kind2]},
            }

    # Beacon-dependent irrelevant side branch. It is not on the terminal slice.
    if r.random()<0.75:
        side_res=f"{prefix}:side"
        add(reads=[seed_res],writes=[side_res],deps=[root0])

    return {
        "surface_id":surface,
        "cell_id":f"{surface}|{kind}|{pattern}",
        "seed":seed,
        "task":{
            "domain":domain,
            "trajectory":rows,
            "terminal_failed_resources":[terminal],
        },
        "_oracle":oracle,
    }

def generate_case(beacon:str,surface:str,kind:str,pattern:str)->dict[str,Any]:
    return _normalize_case(_generate_raw(beacon,surface,kind,pattern))

def public_case(case:Mapping[str,Any])->dict[str,Any]:
    return {k:copy.deepcopy(v) for k,v in case.items() if k!="_oracle"}

def run_batch(beacon:str)->dict[str,Any]:
    rows=[]
    for surface in SURFACES:
        for kind in KINDS:
            for pattern in PATTERNS:
                case=generate_case(beacon,surface,kind,pattern)
                candidate=solve(public_case(case))
                verdict=score_case(case,candidate)
                rows.append({
                    "surface_id":surface,
                    "kind":kind,
                    "pattern":pattern,
                    "seed":case["seed"],
                    "candidate_status":candidate.get("status"),
                    "pass":verdict.get("pass") is True,
                    "reason":verdict.get("reason"),
                })
    return {
        "schema":SCHEMA,
        "status":"PASS__FROZEN_BATCH_EXECUTION" if all(x["pass"] for x in rows) else "FAIL_CLOSED__BATCH_CASE_FAILURE",
        "beacon":beacon,
        "case_count":len(rows),
        "surface_count":len({x["surface_id"] for x in rows}),
        "matrix_complete":len(rows)==len(SURFACES)*len(KINDS)*len(PATTERNS),
        "all_cases_pass":all(x["pass"] for x in rows),
        "rows":rows,
        "terminal_credit_authorized":False,
        "reason_terminal_credit_not_authorized":"THIS_FUNCTION_DOES_NOT_PROVE_BEACON_WAS_POST_FREEZE_OR_UNCONTROLLABLE",
        "new_reality_units_claimed":0,
        "incremental_spend_usd":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def prefreeze_check()->dict[str,Any]:
    drift=[p for p,want in PINNED_BLOBS.items() if _blob_sha(p)!=want]
    route=json.loads((ROOT/"canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json").read_text())
    protocol=route.get("execution_protocol") if isinstance(route,dict) else {}
    cut=json.loads((ROOT/"canonical/governance/P1_MINIMUM_REALITY_CUT_INPUT_V1.json").read_text())
    shared=next((x for x in cut.get("observations",[]) if x.get("id")=="P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH"),None)
    obligations={
        "PINNED_SOURCE_BYTES_UNCHANGED":not drift,
        "CANDIDATE_FROZEN_BEFORE_CASE_SELECTION":protocol.get("candidate_package_frozen_before_case_selection") is True,
        "POST_FREEZE_UNCONTROLLABLE_SELECTOR_PREDECLARED":protocol.get("case_selector")=="POST_FREEZE_UNCONTROLLABLE_PUBLIC_BEACON_HASH_TO_INTEGER_SEEDS",
        "NO_REPLAY_FOR_TUNING":protocol.get("same_case_replay_for_tuning") is False,
        "ONE_SHARED_BATCH_IS_VERIFIED_MINIMUM":isinstance(shared,dict) and shared.get("cost")==1 and set(shared.get("covers") or [])=={
            "P1_FAILURE_SEMANTICS_TRANSPORT_FRONTIERCODE",
            "P1_FAILURE_SEMANTICS_TRANSPORT_CURSORBENCH",
            "P1_FAILURE_SEMANTICS_TRANSPORT_RECOVERY_SCOPE_COMPOSITION",
        },
        "EXACT_THREE_SURFACES_FROZEN":len(SURFACES)==3,
        "EXACT_96_CELL_MATRIX_FROZEN":len(SURFACES)*len(KINDS)*len(PATTERNS)==96,
        "FAILURE_SEMANTICS_MAPPING_FROZEN":SEMANTICS_BY_ORIGIN=={
            ORIGIN_DIRECT:"DIRECT_CONTRACT",
            ORIGIN_DERIVED:"DERIVED_UPSTREAM",
        },
    }
    ok=all(obligations.values())
    return {
        "schema":"PROJECT_BRAIN_P1_SHARED_FRESH_BATCH_PREFREEZE_V1",
        "status":"PASS__PROGRAM_SIDE_BATCH_PACKAGE_FROZEN__EXTERNAL_POST_FREEZE_BEACON_OPEN__ZERO_CREDIT" if ok else "FAIL_CLOSED__PREFREEZE_OBLIGATION_FAILED",
        "pass":ok,
        "source_blob_drift":drift,
        "obligations":obligations,
        "surfaces":list(SURFACES),
        "failure_kinds":list(KINDS),
        "causal_patterns":list(PATTERNS),
        "case_count_after_beacon":96,
        "minimum_missing_fact":"INDEPENDENTLY_VERIFIED_PREFREEZE_PACKAGE__THEN_FIRST_ADMISSIBLE_POST_FREEZE_UNCONTROLLABLE_PUBLIC_BEACON_RECEIPT",
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(prefreeze_check(),indent=2,sort_keys=True))

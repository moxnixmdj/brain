"""Compile the exact current acceptance delta from verified Tool Discovery closure.

This is a pure zero-reality promotion compiler. It changes exactly one atomic
predicate in a copy of current evidence bindings, then recomputes counts and the
family delta. It does not mutate current authority by itself.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_CURRENT_ACCEPTANCE_PROMOTION_V1"
TARGET="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"

EXPECTED={
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
   "0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
   "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":
   "f47a69253e7eb75e139b445b736d3d18b33be622",
 "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
   "913d171b3c855000d322e183b142b3200eeaf0a9",
}


def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def load(rel:str)->dict[str,Any]:
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))


def compile_promotion(
    *,
    evidence:Mapping[str,Any],
    registry:Mapping[str,Any],
    authority:Mapping[str,Any],
    reduction_receipt:Mapping[str,Any],
)->dict[str,Any]:
    errors=[]

    rr=reduction_receipt.get("independent_runner")
    rv=reduction_receipt.get("verified")
    if not isinstance(rr,Mapping) or rr.get("conclusion")!="success":
        errors.append("REDUCTION_INDEPENDENT_RUNNER_NOT_SUCCESS")
    if not isinstance(rv,Mapping):
        rv={}
        errors.append("REDUCTION_VERIFIED_BLOCK_MISSING")
    if rv.get("candidate_target_state")!="PROVED":
        errors.append("REDUCTION_TARGET_NOT_PROVED")
    if rv.get("tool_discovery_family_candidate_state")!="PASS_3_OF_3":
        errors.append("REDUCTION_FAMILY_NOT_3_OF_3")
    if rv.get("uses_empirical_generalization") is not False:
        errors.append("EMPIRICAL_GENERALIZATION_REINTRODUCED")
    if rv.get("source_180_of_180_load_bearing") is not False:
        errors.append("FINITE_SAMPLE_REINTRODUCED_AS_SCOPE_PROOF")

    truth=authority.get("truth")
    if not isinstance(truth,Mapping) or truth.get("opus55_acceptance")!="4/19_PASS__15/19_OPEN":
        errors.append("CURRENT_ACCEPTANCE_WORLD_NOT_4_OF_19")

    predicates=registry.get("predicates")
    if not isinstance(predicates,list) or len(predicates)!=38:
        errors.append("REGISTRY_NOT_38")
        predicates=[]
    registry_ids=[x.get("id") for x in predicates if isinstance(x,Mapping)]
    if TARGET not in registry_ids:
        errors.append("TARGET_NOT_IN_REGISTRY")

    claims=evidence.get("claims")
    if not isinstance(claims,list):
        errors.append("EVIDENCE_CLAIMS_NOT_LIST")
        claims=[]
    by_id={
      x.get("predicate_id"):x for x in claims
      if isinstance(x,Mapping) and isinstance(x.get("predicate_id"),str)
    }
    current=by_id.get(TARGET)
    if not isinstance(current,Mapping):
        errors.append("CURRENT_TARGET_MISSING")
    else:
        if current.get("state")!="EXTERNAL_BLOCKED":
            errors.append("CURRENT_TARGET_NOT_EXTERNAL_BLOCKED")
        if current.get("blocker")!="ABSOLUTE_SCOPE_COMPLETENESS_MISSING":
            errors.append("CURRENT_TARGET_BLOCKER_CHANGED")
    for pid in ("TOOL_LEARNING_SECOND_TASK_TRANSFER","TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION"):
        if (by_id.get(pid) or {}).get("state")!="PROVED":
            errors.append("TOOL_ATOM_NOT_PROVED:"+pid)

    if errors:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,
          "execution_authority":False,"promotion_authority":False,
          "fresh_reality_authority":False,
        }

    new=copy.deepcopy(dict(evidence))
    replacement={
      "predicate_id":TARGET,
      "state":"PROVED",
      "proof_kind":"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS",
      "source_path":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
      "source_sha":"f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
      "independent_or_objective":True,
      "scope_complete":True,
      "objective_ceiling":True,
      "brain_value":1,
      "objective_ceiling_value":1,
      "family":FAMILY,
      "basis":"INDEPENDENT_UNIVERSAL_FORMAL_SCOPE_PROOF_COVERS_EVERY_VALID_INSTANCE_OF_THE_EXACT_FROZEN_HIDDEN_TOOL_PROTOCOL__FINITE_180_OF_180_SAMPLE_RETAINED_AS_NON_LOAD_BEARING_CORROBORATION_ONLY",
      "promotion_receipt":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    }
    new_claims=[]
    replaced=0
    for row in claims:
        if isinstance(row,Mapping) and row.get("predicate_id")==TARGET:
            new_claims.append(replacement)
            replaced+=1
        else:
            new_claims.append(copy.deepcopy(row))
    if replaced!=1:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["TARGET_REPLACEMENT_COUNT_NOT_1"],
                "execution_authority":False,"promotion_authority":False,
                "fresh_reality_authority":False}
    new["claims"]=new_claims

    states={x.get("predicate_id"):x.get("state") for x in new_claims if isinstance(x,Mapping)}
    proved=sum(1 for pid in registry_ids if states.get(pid)=="PROVED")
    unresolved=sum(1 for pid in registry_ids if states.get(pid) not in {"PROVED","REFUTED"})
    blockers=sum(1 for pid in registry_ids if states.get(pid)=="EXTERNAL_BLOCKED")

    family_ids=[x["id"] for x in predicates if x.get("family")==FAMILY]
    family_states={pid:states.get(pid) for pid in family_ids}
    family_pass=bool(family_ids) and all(v=="PROVED" for v in family_states.values())

    if (proved,unresolved)!=(12,26):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":[f"COUNT_MISMATCH:{proved}:{unresolved}"],
                "execution_authority":False,"promotion_authority":False,
                "fresh_reality_authority":False}
    if not family_pass:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["TOOL_DISCOVERY_FAMILY_NOT_ALL_PROVED"],
                "execution_authority":False,"promotion_authority":False,
                "fresh_reality_authority":False}

    new["status"]="AUTHORITY_RECONCILED__12_PROVED__3_BOUND_BLOCKERS__23_OTHER_UNRESOLVED__26_TOTAL_UNRESOLVED__TOOL_DISCOVERY_UNIVERSAL_SCOPE_CLOSED"
    new["saturation"]={
      "status":"RECOMPUTED_AFTER_INDEPENDENT_TOOL_DISCOVERY_UNIVERSAL_FORMAL_SCOPE_CLOSURE",
      "source_snapshot_sha":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
      "receipt":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
      "proved_predicate_count":12,
      "bound_blocker_count":blockers,
      "unresolved_predicate_count":26,
      "new_reality_units_consumed":0,
      "rule":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR_DISCHARGED_BY_INDEPENDENT_UNIVERSAL_FORMAL_SCOPE_PROOF__FINITE_180_OF_180_SAMPLE_NON_LOAD_BEARING",
    }

    return {
      "schema":SCHEMA,
      "status":"PASS__EXACT_ONE_PREDICATE_PROMOTION__12_OF_38__TOOL_DISCOVERY_3_OF_3__5_OF_19_ACCEPTANCE_CANDIDATE",
      "pass":True,
      "errors":[],
      "candidate_evidence":new,
      "proved_predicates":proved,
      "unresolved_predicates":unresolved,
      "bound_blockers":blockers,
      "tool_discovery_family_predicates":family_states,
      "tool_discovery_family_pass":True,
      "prior_acceptance":"4/19_PASS__15/19_OPEN",
      "candidate_acceptance":"5/19_PASS__14/19_OPEN",
      "verified_owned_family_count_unchanged":2,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }


def verify()->dict[str,Any]:
    for rel,want in EXPECTED.items():
        got=blob_sha(ROOT/rel)
        if got!=want:
            raise AssertionError((rel,got,want))
    return compile_promotion(
      evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
      registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
      authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
      reduction_receipt=load("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
    )


def main()->int:
    out=verify()
    print(json.dumps({k:v for k,v in out.items() if k!="candidate_evidence"},indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__=="__main__":
    raise SystemExit(main())

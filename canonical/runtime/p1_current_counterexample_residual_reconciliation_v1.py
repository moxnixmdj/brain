"""Current-residual reconciler for P1 composite-proof quarantine.

This reducer does not lift P1 quarantine. It only removes stale counterexamples
whose assigned mutation role changed after the independently verified
counterexample receipt, while preserving any counterexample that still attacks
the current exact role partition and exact scorer blob.

No terminal replay. No acceptance or family credit.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
RECON=ROOT/"canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"
QUAR=ROOT/"canonical/governance/P1_COMPOSITE_PROOF_COUNTEREXAMPLE_QUARANTINE_V1.json"
RECEIPT=ROOT/"canonical/verification/P1_COMPOSITE_PROOF_COUNTEREXAMPLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V4=ROOT/"canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"

SCHEMA="PROJECT_BRAIN_P1_CURRENT_COUNTEREXAMPLE_RESIDUAL_RECONCILIATION_V1"

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text())
    if not isinstance(x,dict): raise ValueError(str(p))
    return x

def evaluate(recon:Mapping[str,Any], quarantine:Mapping[str,Any], receipt:Mapping[str,Any], current_v4_blob:str)->dict[str,Any]:
    errors=[]
    roles=recon.get("mutation_roles") if isinstance(recon.get("mutation_roles"),Mapping) else {}
    v4=set(roles.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT") or [])
    term=set(roles.get("T0_T2_TERMINAL_INTERVENTION_RESCUE") or [])
    if "DROP_PROVENANCE_OR_DEPENDENCY_EDGE" not in v4:
        errors.append("DROP_PROVENANCE_NOT_CURRENTLY_ASSIGNED_TO_V4")
    if "UNFALSIFIABLE_DIAGNOSIS" not in v4:
        errors.append("UNFALSIFIABLE_DIAGNOSIS_NOT_CURRENTLY_ASSIGNED_TO_V4")
    if "UNFALSIFIABLE_DIAGNOSIS" in term:
        errors.append("UNFALSIFIABLE_DIAGNOSIS_STILL_ASSIGNED_TO_TERMINAL")

    exact=quarantine.get("exact_source_blobs") if isinstance(quarantine.get("exact_source_blobs"),Mapping) else {}
    if exact.get("canonical/runtime/trajectory_failure_typed_ir_proof_v4.py")!=current_v4_blob:
        errors.append("V4_SCORER_BLOB_DRIFT_FROM_COUNTEREXAMPLE_BASIS")

    verified=receipt.get("verified") if isinstance(receipt.get("verified"),list) else []
    if "V4_HIDDEN_ORACLE_SCORER_STILL_PASSES_AFTER_DROP_PROVENANCE_MUTATION" not in verified:
        errors.append("DROP_PROVENANCE_COUNTEREXAMPLE_NOT_INDEPENDENTLY_VERIFIED")
    if "TERMINAL_SCORER_STILL_PASSES_AFTER_EXPLICIT_UNFALSIFIABLE_DIAGNOSIS_INJECTION" not in verified:
        errors.append("TERMINAL_DIAGNOSIS_COUNTEREXAMPLE_NOT_INDEPENDENTLY_VERIFIED")

    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
                "current_applicable_counterexample_count":None,"whole_p1_contract_restored":False,
                "quarantine_lift_eligible":False,"new_reality_units_consumed":0,
                "capability_credit_delta":0,"family_credit_delta":0}

    residual=[{
      "mutation":"DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
      "assigned_role":"V4_TYPED_CROSS_DOMAIN_PREFLIGHT",
      "state":"CURRENT_APPLICABLE_INDEPENDENT_COUNTEREXAMPLE",
      "reason":"CURRENT_ROLE_STILL_ASSIGNS_THIS_MUTATION_TO_THE_EXACT_UNCHANGED_V4_SCORER_AND_PUBLIC_RUNNER_PROVED_THE_MUTATION_SURVIVES"
    }]
    stale=[{
      "mutation":"UNFALSIFIABLE_DIAGNOSIS",
      "old_attacked_role":"T0_T2_TERMINAL_INTERVENTION_RESCUE",
      "current_role":"V4_TYPED_CROSS_DOMAIN_PREFLIGHT",
      "state":"STALE_AGAINST_CURRENT_PARTITION",
      "reason":"THE_INDEPENDENT_TERMINAL_EXTRA_DIAGNOSIS_COUNTEREXAMPLE_ATTACKS_A_ROLE_ASSIGNMENT_NO_LONGER_PRESENT_IN_THE_CURRENT_RECONCILIATION__IT_DOES_NOT_PROVE_THE_CURRENT_V4_ASSIGNMENT"
    }]
    return {
      "schema":SCHEMA,
      "status":"PASS__CURRENT_P1_COUNTEREXAMPLE_SET_REDUCED_TO_ONE_APPLICABLE_RESIDUAL__QUARANTINE_REMAINS",
      "pass":True,
      "errors":[],
      "current_applicable_counterexample_count":1,
      "stale_counterexample_count":1,
      "current_applicable_counterexamples":residual,
      "stale_counterexamples":stale,
      "exact_remaining_p1_blocker":"V4_DROP_PROVENANCE_OR_DEPENDENCY_EDGE_MUTATION_NOT_KILLED",
      "whole_p1_contract_restored":False,
      "quarantine_lift_eligible":False,
      "terminal_results_replayed":0,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"STALE_COUNTEREXAMPLES_MAY_BE_REMOVED_ONLY_WHEN_THEIR_EXACT_ATTACKED_ROLE_IS_ABSENT_FROM_THE_CURRENT_CONTENT_ADDRESSED_PARTITION__SURVIVING_COUNTEREXAMPLES_KEEP_P1_QUARANTINED"
    }

def main()->int:
    out=evaluate(load(RECON),load(QUAR),load(RECEIPT),blob(V4))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())

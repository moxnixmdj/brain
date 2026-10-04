#!/usr/bin/env python3
"""Empirical calibration for conditional retrieval recovery mechanisms.

The V12-V18 stages operate only after earlier routes miss. They therefore must
not be mixed into ordinary provider-route recall. This module records each
independently verified fallback mechanism with its observed residual trials,
recoveries, transport reliability, and scope.

These are finite regression measurements, not open-world probabilities.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_RETRIEVAL_RECOVERY_MECHANISM_CALIBRATION_V1"

RECEIPTS={
 "MULTI_QUERY_DECOMPOSITION_V12":{
  "path":"canonical/verification/RETRIEVAL_V12_MULTI_QUERY_RECOVERY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "blob":"2bf84eccb2119b5ae66dac65e4efe3747ad73121",
  "trials_field":"replayed_v11_miss_count","successes_field":"recovered_v11_miss_count",
  "successful_field":"successful_replay_count","scope":"V11_MISSES",
 },
 "RESIDUAL_ROOT_FIX_V13":{
  "path":"canonical/verification/RETRIEVAL_V13_RESIDUAL_ROOT_FIX_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "blob":"8a436f7ba1593cb3d660f63450ec144b9fc69c27",
  "trials_field":"residual_case_count","successes_field":"recovered_count",
  "successful_field":"successful_case_count","scope":"V12_RESIDUALS",
 },
 "MAVEN_DEEP_MANIFEST_V14":{
  "path":"canonical/verification/RETRIEVAL_V14_MAVEN_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "blob":"3d92eca537007e38e497304d1886a4bdfcde7b88",
  "trials_field":"case_count","successes_field":"recovered_count",
  "successful_field":"successful_case_count","scope":"V13_MAVEN_RESIDUALS",
 },
 "BEHAVIOR_CONTEXT_GRAPH_SNOWBALL_V16":{
  "path":"canonical/verification/RETRIEVAL_V16_GRAPH_SNOWBALL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "blob":"13c402ded359447f32c89b4433e3c63fbe01074e",
  "constant_trials":1,"constant_successes":1,"constant_successful":1,
  "scope":"MAVEN_COLLECTIONS_RESIDUAL",
 },
 "VERSION_HISTORY_IDENTITY_V18":{
  "path":"canonical/verification/RETRIEVAL_V18_VERSIONED_IDENTITY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "blob":"d991a068c50ccac3afa0f5d648ba047c222b3782",
  "constant_trials":1,"constant_successes":1,"constant_successful":1,
  "scope":"MAVEN_JSON_BIND_VERSIONED_IDENTITY_RESIDUAL",
 },
}

def _beta(successes:int,trials:int)->dict[str,float]:
    trials=max(0,int(trials));successes=max(0,min(trials,int(successes)))
    a=successes+0.5;b=(trials-successes)+0.5
    return {"alpha":a,"beta":b,"mean":a/(a+b)}

def _sha1_blob(raw:bytes)->str:
    import hashlib
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def calibrate_repository(root:Path)->dict[str,Any]:
    rows={}
    for mechanism,spec in RECEIPTS.items():
        p=root/spec["path"]
        raw=p.read_bytes()
        got=_sha1_blob(raw)
        if got!=spec["blob"]:
            raise ValueError(f"RECEIPT_BLOB_MISMATCH:{mechanism}:{got}")
        obj=json.loads(raw.decode("utf-8"))
        if obj.get("independent_runner",{}).get("conclusion")!="success":
            raise ValueError("RECEIPT_NOT_INDEPENDENT_PASS:"+mechanism)
        truth=obj.get("measured_live_truth") or {}
        trials=int(spec.get("constant_trials",truth.get(spec.get("trials_field",""),0)) or 0)
        recovered=int(spec.get("constant_successes",truth.get(spec.get("successes_field",""),0)) or 0)
        successful=int(spec.get("constant_successful",truth.get(spec.get("successful_field",""),0)) or 0)
        if not (0<=recovered<=successful<=trials):
            raise ValueError("INVALID_MEASURED_COUNTS:"+mechanism)
        rows[mechanism]={
            "mechanism_id":mechanism,
            "scope":spec["scope"],
            "residual_trial_count":trials,
            "transport_success_count":successful,
            "recovered_count":recovered,
            "conditional_recovery_rate_on_all_trials":recovered/trials if trials else None,
            "conditional_recovery_rate_on_successful_transport":recovered/successful if successful else None,
            "conditional_recovery_posterior":_beta(recovered,trials) if trials else None,
            "transport_reliability_posterior":_beta(successful,trials) if trials else None,
            "verification_path":spec["path"],
            "verification_git_blob_sha":spec["blob"],
            "open_world_completeness_claim":False,
        }
    return {
        "schema":SCHEMA,
        "status":"CALIBRATED_CONDITIONAL_RECOVERY_MECHANISMS_FROM_INDEPENDENT_LIVE_RESIDUALS",
        "mechanisms":rows,
        "mechanism_count":len(rows),
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "RECOVERY_MECHANISM_RATES_ARE_CONDITIONAL_ON_THEIR_MEASURED_RESIDUAL_SCOPES",
            "DO_NOT_TREAT_STAGE_RECOVERY_RATE_AS_UNCONDITIONAL_OPEN_WORLD_RECALL",
            "DO_NOT_MERGE_FALLBACK_MECHANISM_STATS_INTO_FIRST_PASS_PROVIDER_QUERY_STATS",
            "UNKNOWN_MECHANISM_DOMAIN_TRANSFER_REQUIRES_COLD_START_OR_NEW_EVIDENCE",
            "FINITE_30_OF_30_UNION_IS_REGRESSION_TRUTH_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(calibrate_repository(root),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

"""Fail-closed verifier for synthesis required-claim-coverage ceiling lift V2."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
CAND=ROOT/"canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json"
OLD=ROOT/"canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V1.json"
OLD_FAIL=ROOT/"canonical/verification/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_INDEPENDENT_FAILURE_20261002_V1.json"
SEM=ROOT/"canonical/verification/SYNTHESIS_OVERLAY_V3_REBIND_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
CERT=ROOT/"canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json"
LOSSLESS=ROOT/"canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
ACT=ROOT/"canonical/verification/SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

TARGET="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
METRIC="required_claim_coverage_noninferiority"
BEHAVIOR="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
EXPECTED_FAILURES={
    "SOURCE_SCOPE_NOT_PROVED_EXACT_OR_SUPERSET_OF_TARGET_SCOPE",
    "SOURCE_TARGET_SCOPE_RELATION_NOT_INDEPENDENTLY_VERIFIED",
}

def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(str(p))
    return x

def sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fail(*errors:str)->dict[str,Any]:
    return {
        "schema":"PROJECT_BRAIN_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2_VERDICT",
        "status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
        "new_reality_units_consumed":0,"incremental_spend_usd":0,
        "acceptance_credit_delta":0,"family_credit_delta":0,
        "capability_credit_delta":0,"ownership_credit_delta":0,
        "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
    }

def evaluate(
    cand:Mapping[str,Any], old:Mapping[str,Any], old_fail:Mapping[str,Any],
    sem:Mapping[str,Any], cert:Mapping[str,Any], lossless:Mapping[str,Any],
    act:Mapping[str,Any], shas:Mapping[str,str],
)->dict[str,Any]:
    e=[]
    auth=cand.get("authority") or {}
    expected={
      "historical_candidate":("canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V1.json",shas["old"]),
      "historical_independent_failure":("canonical/verification/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_INDEPENDENT_FAILURE_20261002_V1.json",shas["old_fail"]),
      "current_semantics_transport":("canonical/verification/SYNTHESIS_OVERLAY_V3_REBIND_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",shas["sem"]),
      "scope_certificate":("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json",shas["cert"]),
      "lossless_scope_verification":("canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",shas["lossless"]),
      "scope_activation_verification":("canonical/verification/SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",shas["act"]),
    }
    for key,(path,digest) in expected.items():
        row=auth.get(key)
        if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=digest:
            e.append("AUTHORITY_MISMATCH:"+key)

    # The earlier independent verifier checked every original input byte and
    # stopped only at the two absent scope premises. Reuse that falsification
    # rather than replaying thousands of terminal cases.
    old_sha=sha(OLD)
    if (old_fail.get("exact_brain_blobs") or {}).get(
        "canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V1.json"
    )!=old_sha:
        e.append("HISTORICAL_CANDIDATE_NOT_BOUND_BY_FAILURE_RECEIPT")
    if old_fail.get("public_runner",{}).get("conclusion")!="failure":
        e.append("HISTORICAL_FAIL_CLOSED_RECEIPT_INVALID")
    if set(old_fail.get("failure") or [])!=EXPECTED_FAILURES:
        e.append("HISTORICAL_FAILURE_SET_NOT_SCOPE_ONLY")
    if "EXACT_10_OF_10_BRAIN_BLOBS_MATCHED" not in set(old_fail.get("verified_before_failure") or []):
        e.append("HISTORICAL_EXACT_BLOB_CHECK_MISSING")

    p0=old.get("proof") or {}
    if p0.get("behavior_id")!=BEHAVIOR: e.append("HISTORICAL_BEHAVIOR_DRIFT")
    if p0.get("frozen_oracle_literal")!="100_PERCENT_REQUIRED_CLAIM_COVERAGE":
        e.append("HISTORICAL_COVERAGE_ORACLE_DRIFT")
    if p0.get("brain_required_claim_coverage_lower_bound")!=1:
        e.append("HISTORICAL_BRAIN_LOWER_BOUND_DRIFT")
    if p0.get("admissible_metric_upper_bound")!=1:
        e.append("HISTORICAL_METRIC_UPPER_BOUND_DRIFT")
    if p0.get("brain_minus_comparator_lower_bound")!=0:
        e.append("HISTORICAL_DERIVED_BOUND_DRIFT")
    if p0.get("target_direction")!="higher" or p0.get("target_threshold")!=0:
        e.append("HISTORICAL_TARGET_REQUIREMENT_DRIFT")

    sv=sem.get("verified") or {}
    if sem.get("independent_runner",{}).get("verification_runs") is None:
        e.append("CURRENT_SEMANTICS_INDEPENDENCE_MISSING")
    if sv.get("target_predicate_id")!=TARGET or sv.get("v1_to_v3_target_semantics_identical") is not True:
        e.append("CURRENT_TARGET_SEMANTICS_NOT_IDENTICAL")
    if METRIC not in set(sv.get("missing_metric_bounds") or []):
        e.append("CURRENT_REQUIRED_COVERAGE_BOUND_NOT_OPEN_IN_TRANSPORT_RECEIPT")

    if cert.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR":
        e.append("SCOPE_CERT_TARGET_ID_DRIFT")
    if cert.get("witness_scope_id")!="scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL":
        e.append("SCOPE_CERT_WITNESS_ID_DRIFT")
    if cert.get("verified") is not True or cert.get("independent") is not True:
        e.append("SCOPE_CERT_NOT_VERIFIED_INDEPENDENT")
    if cert.get("scope_relation")!="PROVEN_STRONGER":
        e.append("SCOPE_CERT_NOT_PROVEN_STRONGER")
    if cert.get("coverage_complete") is not True or cert.get("coverage_proof_verified") is not True:
        e.append("SCOPE_CERT_COVERAGE_INCOMPLETE")
    if cert.get("coverage_relation")!="EXACT_UNION":
        e.append("SCOPE_CERT_COVERAGE_RELATION_DRIFT")

    lv=lossless.get("verified") or {}
    if lossless.get("independent_runner",{}).get("conclusion")!="success":
        e.append("LOSSLESS_SCOPE_INDEPENDENT_VERIFICATION_FAILED")
    if lv.get("target_predicate_id")!=TARGET or lv.get("scope_relation")!="PROVEN_STRONGER":
        e.append("LOSSLESS_SCOPE_RELATION_INVALID")
    if lv.get("exact_dimension_set") is not True or lv.get("exact_contract_fragment_witnesses") is not True:
        e.append("LOSSLESS_SCOPE_EXACTNESS_MISSING")

    av=act.get("verified") or {}
    if act.get("independent_runner",{}).get("conclusion")!="success":
        e.append("SCOPE_ACTIVATION_INDEPENDENT_VERIFICATION_FAILED")
    if av.get("predicate_id")!=TARGET or av.get("after_root_class")!="ROOT2_ONLY":
        e.append("SCOPE_ACTIVATION_TARGET_DRIFT")

    pc=cand.get("proof_composition") or {}
    if pc.get("behavior_id")!=BEHAVIOR:
        e.append("CANDIDATE_BEHAVIOR_DRIFT")
    if pc.get("source_scope_id")!=cert.get("witness_scope_id") or pc.get("target_scope_id")!=cert.get("target_scope_id"):
        e.append("CANDIDATE_SCOPE_IDS_NOT_CERT_BOUND")
    if pc.get("verified_source_to_target_relation")!="SUPERSET":
        e.append("CANDIDATE_RELATION_NOT_SUPERSET")
    if pc.get("relation_independent") is not True:
        e.append("CANDIDATE_RELATION_NOT_INDEPENDENT")
    if pc.get("brain_required_claim_coverage_lower_bound")!=1.0 or pc.get("admissible_metric_upper_bound")!=1.0:
        e.append("CANDIDATE_CEILING_NUMBERS_DRIFT")
    if pc.get("brain_minus_comparator_lower_bound")!=0.0:
        e.append("CANDIDATE_DERIVED_BOUND_DRIFT")
    if pc.get("target_direction")!="higher" or pc.get("target_threshold")!=0.0:
        e.append("CANDIDATE_TARGET_REQUIREMENT_DRIFT")

    expected_bound={METRIC:{"lower":0.0,"derivation":"ABSOLUTE_CEILING_DOMINANCE_AFTER_INDEPENDENT_SUPERSET_SCOPE_REPAIR"}}
    if cand.get("derived_metric_bounds")!=expected_bound:
        e.append("DERIVED_METRIC_BOUND_SHAPE_MISMATCH")
    if set(cand.get("explicitly_not_proved") or [])!={"metric:matched_quality","matched_quality_noninferiority"}:
        e.append("MATCHED_QUALITY_OVERCLAIM")
    residual=cand.get("expected_residual_after_verification") or {}
    if set(residual.get("missing_atoms") or [])!={"metric:matched_quality"}:
        e.append("RESIDUAL_ATOM_DRIFT")
    if set(residual.get("missing_metric_bounds") or [])!={"matched_quality_noninferiority"}:
        e.append("RESIDUAL_BOUND_DRIFT")

    if e: return fail(*e)
    return {
      "schema":"PROJECT_BRAIN_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2_VERDICT",
      "status":"PASS__REQUIRED_CLAIM_COVERAGE_NONINFERIORITY_DISCHARGED_BY_100_PERCENT_CEILING_PLUS_INDEPENDENT_SUPERSET_SCOPE__ZERO_ACCEPTANCE_CREDIT",
      "pass":True,"target_predicate_id":TARGET,"metric":METRIC,
      "brain_lower_bound":1.0,"comparator_upper_bound":1.0,"brain_minus_comparator_lower_bound":0.0,
      "remaining_unproved":["metric:matched_quality","matched_quality_noninferiority"],
      "new_reality_units_consumed":0,"terminal_cases_consumed":0,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
    }

def docs():
    paths={"cand":CAND,"old":OLD,"old_fail":OLD_FAIL,"sem":SEM,"cert":CERT,"lossless":LOSSLESS,"act":ACT}
    loaded={k:load(p) for k,p in paths.items()}
    shas={k:sha(p) for k,p in paths.items() if k!="cand"}
    return loaded["cand"],loaded["old"],loaded["old_fail"],loaded["sem"],loaded["cert"],loaded["lossless"],loaded["act"],shas

def main()->int:
    out=evaluate(*docs())
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())

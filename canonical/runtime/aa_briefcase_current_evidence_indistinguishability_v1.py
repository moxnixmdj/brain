"""AA-Briefcase current-evidence parity indistinguishability certificate.

The certifier proves a narrow epistemic result. Current canonical bytes bind the
matched current-owner reference and the receipt semantics, but contain neither
an actual matched Brain score nor a bound scope-complete professional-quality
certificate. Therefore a just-below-target result and a target-meeting result
remain observationally indistinguishable from the current retained evidence.

A future verified score or genuinely new scope-complete premise reopens this cut.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_AA_BRIEFCASE_CURRENT_EVIDENCE_INDISTINGUISHABILITY_V1"
TARGET_PATH="canonical/evidence/AA_BRIEFCASE_OPUS55_CURRENT_OWNER_TARGET_20261007_V1.json"
ROUTE_PATH="canonical/governance/AA_BRIEFCASE_CURRENT_EPOCH_PARITY_ROUTE_20261007_V1.json"
SCAN_PATH="canonical/governance/AA_BRIEFCASE_CURRENT_EVIDENCE_EXHAUSTION_20261008_V1.json"
BOUNDARY_PATH="canonical/governance/AA_BRIEFCASE_EXTERNAL_ACCESS_BOUNDARY_20261005_V1.json"
BRIDGE_VERIFY_PATH="canonical/verification/AA_BRIEFCASE_CURRENT_EPOCH_RESULT_BRIDGE_V2_VERIFICATION_20261007_V1.json"

def _load(root:Path, rel:str)->Mapping[str,Any]:
    p=(root/rel).resolve(strict=True); p.relative_to(root)
    value=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value,Mapping): raise ValueError("JSON_OBJECT_REQUIRED:"+rel)
    return value

def certify(*,repo_root:str|Path)->dict[str,Any]:
    try:
        root=Path(repo_root).resolve(strict=True)
        target=_load(root,TARGET_PATH)
        route=_load(root,ROUTE_PATH)
        scan=_load(root,SCAN_PATH)
        boundary=_load(root,BOUNDARY_PATH)
        bridge=_load(root,BRIDGE_VERIFY_PATH)

        t=target.get("target")
        ct=route.get("current_target")
        receipts=scan.get("actual_score_receipts")
        stronger=scan.get("stronger_full_scope_certificate_scan")
        public=boundary.get("public_source")
        if not all(isinstance(x,Mapping) for x in (t,ct,receipts,stronger,public)):
            raise ValueError("BOUND_SHAPE_INVALID")

        reference=t.get("current_owner_elo")
        if isinstance(reference,bool) or not isinstance(reference,(int,float)) or not math.isfinite(float(reference)):
            raise ValueError("REFERENCE_INVALID")
        reference=float(reference)
        if reference!=1807.0 or float(ct.get("opus55_reference_elo"))!=reference:
            raise ValueError("CURRENT_REFERENCE_DRIFT")
        if t.get("benchmark")!="AA-Briefcase v1.1" or ct.get("benchmark")!="AA-Briefcase v1.1":
            raise ValueError("BENCHMARK_DRIFT")
        if route.get("status")!="ACTIVE_CANDIDATE_ROUTE__CURRENT_EPOCH_REFERENCE_1807__BRAIN_SCORE_MISSING__ZERO_CREDIT":
            raise ValueError("ROUTE_NO_LONGER_SCORE_MISSING")
        if receipts.get("count")!=0:
            raise ValueError("ACTUAL_SCORE_RECEIPT_NOW_EXISTS")
        if stronger.get("bound_certificate_count")!=0:
            raise ValueError("BOUND_STRONGER_CERTIFICATE_NOW_EXISTS")
        if scan.get("conclusion",{}).get("current_internal_existing_evidence_search_exhausted") is not True:
            raise ValueError("EXISTING_EVIDENCE_SEARCH_NOT_EXHAUSTED")
        if "NO_BRAIN_SCORE" not in str(bridge.get("status") or ""):
            raise ValueError("BRIDGE_VERIFICATION_SCORE_BOUNDARY_CHANGED")

        facts=set(public.get("facts") or [])
        required={
            "OFFICIAL_EVALUATION_IS_PRIVATE_DATASET",
            "FOUR_SCORE_BEARING_PROJECT_SCENARIOS_ARE_PRIVATE",
            "PUBLIC_FIFTH_SCENARIO_IS_DEMONSTRATIVE_ONLY",
            "PUBLIC_FIFTH_SCENARIO_DOES_NOT_CONTRIBUTE_TO_OFFICIAL_AA_BRIEFCASE_ELO",
            "OFFICIAL_AA_BRIEFCASE_SCORE_IS_NOT_PUBLICLY_SELF_SERVICE_AVAILABLE",
        }
        if not required.issubset(facts):
            raise ValueError("PRIVATE_SCORE_BOUNDARY_NOT_BOUND")

        fail_score=reference-0.1
        pass_score=reference
        fail_world={
            "hypothetical_matched_verified_brain_score":fail_score,
            "opus55_reference_score":reference,
            "parity_pass":False,
        }
        pass_world={
            "hypothetical_matched_verified_brain_score":pass_score,
            "opus55_reference_score":reference,
            "parity_pass":True,
        }
        return {
            "schema":SCHEMA,
            "status":"PASS__CURRENT_BOUND_AA_BRIEFCASE_EVIDENCE_IS_PARITY_INDETERMINATE",
            "pass":True,
            "benchmark":"AA-Briefcase v1.1",
            "current_owner_reference_elo":reference,
            "actual_verified_comparable_brain_score_receipt_count":0,
            "bound_scope_complete_certificate_count":0,
            "fail_world":fail_world,
            "pass_world":pass_world,
            "current_bound_evidence_decides_parity":False,
            "information_theoretic_indistinguishability_proved":True,
            "current_internal_parity_derivation_exhausted":True,
            "required_new_information_class":"MATCHED_CURRENT_EPOCH_INDEPENDENT_OR_OWNER_VERIFIED_AA_BRIEFCASE_BRAIN_SCORE_OR_NEW_SCOPE_COMPLETE_PROFESSIONAL_QUALITY_PREMISE",
            "shared_leverage":["PROWORK_AA_BRIEFCASE_GE_1822","ARTIFACT_AA_BRIEFCASE_GE_1822","PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"],
            "future_verified_score_or_new_premise_reopens":True,
            "execution_authority":False,
            "promotion_authority":False,
            "terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "information_theoretic_indistinguishability_proved":False,
            "current_internal_parity_derivation_exhausted":False,
            "execution_authority":False,"promotion_authority":False,"terminal_authority":False,
        }

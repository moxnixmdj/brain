"""R9 execution-leaf property-truth verifier V1.

Discharges only the exact manifest execution acceptance for the frozen R9 leaf
by replaying the bound conservative-censoring and temporal-defeater guard over
positive, near-miss, adversarial, stale-dependency, and identity-substitution
cases. It does not prove detection completeness, R9 semantics/root closure, or
professional-quality/terminal authority.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r9_execution_guard_v1 as guard
from canonical.runtime.tb_science_conservative_censoring_reducer_v1 import adjudicate

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID=guard.LEAF_ID
ROOT_ID=guard.ROOT_ID
CLAIM_ID=guard.CLAIM_ID
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "censoring_verify":("canonical/verification/PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_VERIFY_20261010_V1.json","7081a52621a1bb8f1ad07d1da23b40c8e57e16c2"),
 "guard_runtime":("canonical/runtime/professional_quality_r9_execution_guard_v1.py","bdc7c9f0a05ffd06ae23186af4bba411af097867"),
 "censoring_runtime":("canonical/runtime/tb_science_conservative_censoring_reducer_v1.py","3b48ea534d606cf47a8321b56427353066393577"),
}

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
    return value

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
      "leaf_property_truth_authority":False,"detection_completeness_proved":False,
      "r9_semantic_leaf_closed":False,"r9_root_closed":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _leaf_acceptance(manifest:Mapping[str,Any])->str|None:
    for row in manifest.get("roots") or []:
        if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID: continue
        leaf=row.get("execution_leaf")
        if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
            value=leaf.get("acceptance")
            return value if isinstance(value,str) else None
    return None

SLOTS=[f"task-{i:02d}::trial-{j}" for i in range(70) for j in range(3)]
def _rows(n:int,state:str)->list[dict[str,str]]:
    return [{"slot_id":SLOTS[i],"state":state} for i in range(n)]

def _guard(profile:Mapping[str,Any],catalog:Mapping[str,Any],*,verdict:Mapping[str,Any]|None=None,
           detected:tuple[str,...]=(),near:Mapping[str,bool]|None=None,unmapped:bool=False,
           fresh:bool=True,claim_id:str=CLAIM_ID)->dict[str,Any]:
    return guard.evaluate(
      claim_id=claim_id,
      censoring_verdict=verdict or adjudicate(SLOTS,_rows(124,"SUCCESS")),
      execution_profile=profile,
      defeater_catalog=catalog,
      detected_defeater_ids=detected,
      near_miss_signals=near or {},
      unmapped_material_false_certification_defeater=unmapped,
      dependency_fresh=fresh,
    )

def evaluate_documents(
 manifest:Mapping[str,Any],profile:Mapping[str,Any],catalog:Mapping[str,Any],
 scope_batch_verify:Mapping[str,Any],censoring_verify:Mapping[str,Any],
)->dict[str,Any]:
    if _leaf_acceptance(manifest)!=ACCEPTANCE:
        return _fail("R9_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_leaf_acceptance(manifest))

    replay=scope_batch_verify.get("independent_replay")
    pins=scope_batch_verify.get("pinned_dependencies")
    if (
      not str(scope_batch_verify.get("status") or "").startswith("PASS__")
      or not isinstance(replay,Mapping)
      or replay.get("leaf_count")!=24
      or replay.get("domain_equivalence_pass_count")!=24
      or replay.get("scope_complete_count")!=24
      or replay.get("unique_claim_id_count")!=24
      or replay.get("property_truth_count")!=0
      or not isinstance(pins,Mapping)
      or pins.get("leaf_manifest")!=PINS["manifest"][1]
    ):
        return _fail("R9_WHOLE_LEAF_SCOPE_BATCH_NOT_COMPLETE")

    creplay=censoring_verify.get("replay")
    exact=censoring_verify.get("exact_blobs")
    if (
      not str(censoring_verify.get("status") or "").startswith("PASS__")
      or not isinstance(creplay,Mapping)
      or creplay.get("unit_tests_passed")!=5
      or creplay.get("exhaustive_final_success_counts_checked")!=211
      or not isinstance(exact,Mapping)
      or exact.get("runtime")!=PINS["censoring_runtime"][1]
    ):
        return _fail("R9_CENSORING_VERIFICATION_INCOMPLETE")

    positive=_guard(profile,catalog)
    positive_ok=(
      positive.get("pass") is True
      and positive.get("status")=="PASS__R9_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION"
      and positive.get("ordinary_certificate_path_allowed") is True
      and positive.get("whole_leaf_property_truth_proved") is False
      and positive.get("quality_authority") is False
    )

    known={}
    for did in sorted(guard.KNOWN_R9_DEFEATERS):
        out=_guard(profile,catalog,detected=(did,))
        known[did]=(
          out.get("pass") is False
          and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R9_DEFEATER_ACTIVE"
          and out.get("ordinary_certificate_path_allowed") is False
        )

    near={}
    for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
        out=_guard(profile,catalog,near={signal:True})
        near[signal]=(
          out.get("pass") is False
          and out.get("status")=="ESCALATE__R9_NEAR_MISS_TRIGGER"
          and trigger in set(out.get("active_escalation_triggers") or [])
        )

    unknown=_guard(profile,catalog,detected=("C999_FRESH_TEMPORAL_ATTACK",))
    unmapped=_guard(profile,catalog,unmapped=True)
    final_fail=_guard(profile,catalog,verdict=adjudicate(SLOTS,_rows(123,"SUCCESS"),final=True))
    failure_lock=_guard(profile,catalog,verdict=adjudicate(SLOTS,_rows(87,"FAILURE")))
    stale=_guard(profile,catalog,fresh=False)

    invalid=deepcopy(adjudicate(SLOTS,_rows(124,"SUCCESS")))
    invalid["unobserved_slots_count_as_zero_on_finalization"]=False
    invalid_out=_guard(profile,catalog,verdict=invalid)
    claim_out=_guard(profile,catalog,claim_id="0"*64)

    checks={
      "POSITIVE_PASS_LOCK_BOUND_TO_R9_CONTRACT":positive_ok,
      "ALL_13_KNOWN_R9_DEFEATERS_BLOCK":all(known.values()) and len(known)==13,
      "ALL_R9_NEAR_MISS_CLASSES_ESCALATE":all(near.values()) and len(near)==len(guard.NEAR_MISS_TO_TRIGGER),
      "UNKNOWN_DETECTED_DEFEATER_ESCALATES":unknown.get("status")=="ESCALATE__UNMAPPED_DETECTED_DEFEATER",
      "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_ESCALATES":unmapped.get("status")=="ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
      "FINAL_123_SUCCESS_BOUNDARY_FAILS":final_fail.get("status")=="ABSTAIN_OR_ESCALATE__R9_CENSORING_NOT_PASS_LOCK",
      "IRREVERSIBLE_87_FAILURE_BOUNDARY_FAILS":failure_lock.get("status")=="ABSTAIN_OR_ESCALATE__R9_CENSORING_NOT_PASS_LOCK",
      "STALE_DEPENDENCY_BLOCKS":stale.get("status")=="ABSTAIN_OR_ESCALATE__R9_STALE_DEPENDENCY",
      "CENSORING_INVARIANT_DRIFT_FAILS_CLOSED":invalid_out.get("reason")=="CENSORING_INVARIANT_DRIFT",
      "CLAIM_SUBSTITUTION_FAILS_CLOSED":claim_out.get("reason")=="CLAIM_ID_MISMATCH",
    }
    if not all(checks.values()):
        return _fail("R9_EXECUTION_PROPERTY_CHALLENGE_FAILED",
                     checks=checks,known_defeater_results=known,near_miss_results=near)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__R9_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_BOUND_RUNTIME_BEHAVIOR__ONE_LEAF_PROPERTY_TRUTH_ONLY",
      "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
      "manifest_acceptance":ACCEPTANCE,"checks":checks,
      "observed_case_counts":{
        "positive":1,"known_adversarial":13,"near_miss":len(near),
        "unknown_detected":1,"unmapped_material":1,"final_123_boundary":1,
        "irreversible_failure_lock":1,"stale_dependency":1,
        "censoring_invariant_drift":1,"claim_substitution":1,
        "total":22+len(near),
      },
      "leaf_property_truth_authority":True,
      "property_truth_basis":"MANIFEST_CASE_BASED_EXECUTION_ACCEPTANCE_ON_EXACT_BOUND_R9_RUNTIME_BEHAVIOR",
      "detection_completeness_proved":False,
      "r9_semantic_leaf_closed":False,"r9_root_closed":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    docs={}
    for key,(rel,expected) in PINS.items():
        p=root/rel
        if not p.is_file() or p.is_symlink():
            return _fail(key.upper()+"_MISSING")
        observed=_blob(p)
        if observed!=expected:
            return _fail(key.upper()+"_BLOB_STALE",observed_blob=observed)
        if key in {"manifest","profile","catalog","scope_batch_verify","censoring_verify"}:
            try: docs[key]=_load(p)
            except Exception: return _fail(key.upper()+"_JSON_INVALID")
    return evaluate_documents(
      docs["manifest"],docs["profile"],docs["catalog"],
      docs["scope_batch_verify"],docs["censoring_verify"]
    )

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))

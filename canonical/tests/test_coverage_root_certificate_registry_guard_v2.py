import json
from copy import deepcopy
from pathlib import Path
from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime.coverage_root_certificate_registry_guard_v2 import validate

ROOT=Path(__file__).resolve().parents[2]
AUTH="13c470645b037bbb46245c687dd35197b420d51a"
MISSION=json.loads((ROOT/"canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text())
BASE=json.loads((ROOT/"canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json").read_text())
ROOTS=("CC_R1_REALITY_CONTAINMENT_V1","CC_R2_MISSION_SOUNDNESS_V1","CC_R3_TERMINAL_CLOSURE_V1")

def doc():
 c={"claim_kind":"PROPERTY_CERTIFICATE","mission_blob_sha":AUTH,"scope_sha256":"3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d","target_predicate_sha256":"4967b35be044567ae9fbcd01f2443996dc675f3154fd386790f79301ae9cff09","semantics_sha256":"bdb1e40284acf8f93f0552143ccfb2a3246428a1862c3f37907a00b20d18fc3e","epoch":"2026-10-10T18:05:00+02:00","authority_id":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF","terminal_credit_delta":0}
 c["claim_id"]=compute_claim_id(c)
 d=deepcopy(BASE);d["active_claim"]=c;d["claim_binding_policy"]["mission_binding_mode"]="MISSION_AUTHORITY_BLOB"
 d["certificate_slots"]=[{"root_id":r,"status":"OPEN_NO_GLOBAL_CERTIFICATE_BOUND","certificate":None,"semantic_verifier":None,"independent_verification":None} for r in ROOTS]
 d["currently_proved_root_certificates"]=0;d["currently_open_root_certificates"]=3;d["r4_proof_closure"]=False
 return d

def test_exact_authority_mode_passes():
 out=validate(doc(),current_mission_pointer=MISSION,current_mission_authority_blob_sha=AUTH)
 assert out["pass"] is True,out

def test_mode_is_not_inferred():
 d=doc();d["claim_binding_policy"].pop("mission_binding_mode")
 out=validate(d,current_mission_pointer=MISSION,current_mission_authority_blob_sha=AUTH)
 assert "CURRENT_MISSION_POINTER_BLOB_REQUIRED_FOR_ACTIVE_CLAIM" in out["errors"]

def test_stale_authority_fails():
 d=doc();d["active_claim"]["mission_blob_sha"]="f"*40;d["active_claim"]["claim_id"]=compute_claim_id(d["active_claim"])
 out=validate(d,current_mission_pointer=MISSION,current_mission_authority_blob_sha=AUTH)
 assert "ACTIVE_CLAIM_MISSION_AUTHORITY_BINDING_STALE" in out["errors"]

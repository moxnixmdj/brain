from __future__ import annotations
import json
from hashlib import sha1
from pathlib import Path
from canonical.runtime import coverage_claim_scope_guard_v2 as cg
from canonical.runtime import professional_r12_universal_positive_gate_totality_verified_v1 as u

SCHEMA="PROJECT_BRAIN_R12_REPAIRED_SEMANTIC_PROPERTY_VERIFY_V1"
NEW="c6ce8218b33a09567078979c307ba3fe2a0591244c0da0c2348f89547e200775"
OLD="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE="3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d"
MISSION="13c470645b037bbb46245c687dd35197b420d51a"
P={
"new":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261011_V3.json","caf80a84e89c4d1e7d2820e79e94874422bdfa24"),
"old":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json","7b26ddba501358d42d6fa342efd27d389bb30654"),
"mission":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json",MISSION),
"pointer":("canonical/governance/CURRENT_MISSION_OBJECTIVE.json",None),
"r2":("canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json","8fc8057152ba26cd91643ec75d8853d421b59cba"),
"uv":("canonical/verification/PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_CC_R3_COMPOSITION_INDEPENDENT_VERIFY_20261011_V1.json","bb9eaa24afa423c638e4cd3e619d843ee9e7e042"),
"c8":("canonical/verification/PROFESSIONAL_R12_STABLE_C8_NONVACUITY_VERIFY_20261010_V1.json","6ed0f5d253d0fc734af2998e86ad72f73fe8c073"),
"split":("canonical/verification/PROFESSIONAL_R12_SEMANTIC_SPEC_SPLIT_GUARD_INDEPENDENT_VERIFY_20261011_V1.json","60602fb3b0ffdab3626c041ec43c83d008bb5c24")
}
def blob(p):
 b=p.read_bytes();return sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(root,k):
 rel,h=P[k];p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("MISSING:"+k)
 if h and blob(p)!=h:raise ValueError("DRIFT:"+k)
 return json.loads(p.read_text())
def fail(r):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":r,"semantic_property_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 try:
  n,o,m,ptr,r2,uv,c8,split=[load(root,k) for k in ("new","old","mission","pointer","r2","uv","c8","split")]
 except Exception as e:return fail(type(e).__name__+":"+str(e))
 g=cg.validate_claim(n,current_pointer=ptr,mission_authority=m,mission_authority_blob_sha=MISSION)
 if g.get("pass") is not True or g.get("claim_id")!=NEW:return fail("NEW_CLAIM_INVALID")
 if n.get("scope_sha256")!=SCOPE or o.get("scope_sha256")!=SCOPE:return fail("SCOPE_CHANGED")
 if n.get("mission_blob_sha")!=MISSION or o.get("mission_blob_sha")!=MISSION:return fail("MISSION_CHANGED")
 pr=n.get("preservation") or {}
 if pr.get("real_mission_unchanged") is not True or pr.get("root_contract_unchanged") is not True:return fail("PRESERVATION_UNPROVED")
 if pr.get("weaker_positive_gate") is not False or pr.get("unresolved_material_positive_authority_allowed") is not False:return fail("REPAIR_WEAKENED")
 unresolved=str((r2.get("claim_scoped_terms") or {}).get("unresolved_binding") or "")
 if "BLOCKS_POSITIVE_CERTIFICATION" not in unresolved or "ABSTENTION" not in unresolved:return fail("R2_FAIL_CLOSED_RULE_MISSING")
 if not str(split.get("status") or "").startswith("PASS__SECOND_INDEPENDENT_SPRITE"):return fail("SPEC_SPLIT_UNVERIFIED")
 live=u.verify(repo_root=root)
 if live.get("pass") is not True or live.get("material_defeater_totality_proved") is not True or live.get("cc_r3_terminal_closure_proved") is not True:return fail("UNIVERSAL_TOTALITY_UNPROVED")
 if live.get("stable_c8_nonvacuity_proved") is not True:return fail("LIVE_C8_UNPROVED")
 if (live.get("generator_closure") or {}).get("fail_closed_on_unknown") is not True:return fail("FAIL_CLOSED_UNKNOWN_UNPROVED")
 t=uv.get("truth") or {}
 if not str(uv.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE") or t.get("material_defeater_totality_proved") is not True or t.get("cc_r3_terminal_closure_proved") is not True:return fail("UNIVERSAL_INDEPENDENT_UNPROVED")
 rs=c8.get("reasoning") or {};cs=c8.get("consequence") or {}
 if cs.get("r12_c8_nonvacuity_proved") is not True or rs.get("witness_is_real_executed_route") is not True or rs.get("witness_is_independently_replayed") is not True:return fail("REAL_C8_UNPROVED")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__REPAIRED_R12_SEMANTIC_PROPERTY_TRUTH","semantic_claim_id":NEW,"predecessor_claim_id":OLD,"semantic_scope_sha256":SCOPE,"semantic_target_predicate_sha256":n["target_predicate_sha256"],"semantic_semantics_sha256":n["semantics_sha256"],"claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,"cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,"r4_proof_realization_authority":True,"leaf_semantic_satisfied":True,"semantic_property_truth_authority":True,"predecessor_authority_transported":False,"new_primitive_required":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

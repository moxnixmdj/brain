import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
PATHS={
"robust_theorem":ROOT/"canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_CONSTRUCTIVE_ADEQUACY_THEOREM_20261009_V1.json",
"robust_certificate":ROOT/"canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json",
"robust_binding":ROOT/"canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_BINDING_20261009_V1.json",
"robust_verification":ROOT/"canonical/verification/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261009_V1.json",
"robust_seal":ROOT/"canonical/verification/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_FINAL_INTEGRATION_SEAL_20261009_V1.json",
"registry":ROOT/"canonical/runtime/p3_conditioned_policy_adequacy_registry_v1.py",
"complement_theorem":ROOT/"canonical/governance/CURSORBENCH_THREE_REGION_COMPLEMENT_NONIDENTIFIABILITY_20261009_V1.json",
"complement_runtime":ROOT/"canonical/runtime/cursorbench_three_region_complement_nonidentifiability_v1.py",
"complement_verification":ROOT/"canonical/verification/CURSORBENCH_THREE_REGION_COMPLEMENT_NONIDENTIFIABILITY_INDEPENDENT_VERIFICATION_20261009_V1.json",
}
def blob(p):
 d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_binds_three_region_frontier_without_target_transfer():
 a=json.loads(AUTH.read_text(encoding="utf-8"))
 r=a["authoritative_sources"]["coding_robust_finite_multi_interpretation_constructive_region_20261009_v1"]
 c=a["authoritative_sources"]["cursorbench_three_region_complement_nonidentifiability_20261009_v1"]
 assert blob(PATHS["robust_theorem"])==r["theorem"]["git_blob_sha"]
 assert blob(PATHS["robust_certificate"])==r["certificate"]["git_blob_sha"]
 assert blob(PATHS["robust_binding"])==r["binding"]["git_blob_sha"]
 assert blob(PATHS["robust_verification"])==r["independent_verification"]["git_blob_sha"]
 assert blob(PATHS["robust_seal"])==r["final_integration_seal"]["git_blob_sha"]
 assert blob(PATHS["registry"])==r["registry"]["git_blob_sha"]
 assert blob(PATHS["complement_theorem"])==c["theorem"]["git_blob_sha"]
 assert blob(PATHS["complement_runtime"])==c["runtime"]["git_blob_sha"]
 assert blob(PATHS["complement_verification"])==c["independent_verification"]["git_blob_sha"]
 live=a["live_truth"]
 assert live["coding_specification_registered_coding_policy_count"]==3
 assert live["coding_specification_authenticated_constructive_region_count"]==3
 assert live["cursorbench_current_constructive_region_union_count"]==3
 assert live["cursorbench_current_constructive_region_union_distinct_condition_atom_count"]==18
 assert live["cursorbench_three_region_complement_nonidentifiability_proved"] is True
 assert live["cursorbench_current_static_evidence_identifies_three_region_complement_emptiness"] is False
 assert live["cursorbench_positive_adequacy_cover_closed"] is False
 assert live["coding_robust_finite_multi_interpretation_private_cursorbench_membership_proved"] is False
 rec=a["cursorbench_three_region_constructive_frontier_reconciliation_20261009_v1"]
 assert rec["private_cursorbench_membership_delta"]==0
 assert rec["whole_cursorbench_cover_delta"]==0
 assert rec["acceptance_credit_delta"]==0
 assert rec["terminal_credit_delta"]==0

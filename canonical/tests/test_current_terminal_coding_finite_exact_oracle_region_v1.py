import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
THM=ROOT/"canonical/governance/CODING_FINITE_EXACT_ORACLE_CONSTRUCTIVE_ADEQUACY_THEOREM_20261009_V1.json"
CERT=ROOT/"canonical/governance/CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"
BIND=ROOT/"canonical/governance/CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_BINDING_20261009_V1.json"
VER=ROOT/"canonical/verification/CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261009_V1.json"
RUNTIME=ROOT/"canonical/runtime/coding_finite_candidate_exact_oracle_solver_v1.py"
REG=ROOT/"canonical/runtime/p3_conditioned_policy_adequacy_registry_v1.py"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_binds_second_constructive_region_without_target_transfer():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    s=a["authoritative_sources"]["coding_finite_exact_oracle_constructive_region_20261009_v1"]
    assert blob(THM)==s["theorem"]["git_blob_sha"]
    assert blob(CERT)==s["certificate"]["git_blob_sha"]
    assert blob(BIND)==s["binding"]["git_blob_sha"]
    assert blob(VER)==s["independent_verification"]["git_blob_sha"]
    assert blob(RUNTIME)==s["runtime"]["git_blob_sha"]
    assert blob(REG)==s["registry"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["coding_finite_exact_oracle_constructive_region_verified"] is True
    assert live["coding_finite_exact_oracle_constructive_liveness_proved"] is True
    assert live["coding_finite_exact_oracle_private_cursorbench_membership_proved"] is False
    assert live["coding_finite_exact_oracle_whole_cursorbench_cover_proved"] is False
    assert live["coding_specification_registered_coding_policy_count"]==2
    assert live["coding_specification_authenticated_constructive_region_count"]==2
    assert set(live["coding_specification_authenticated_constructive_region_policy_ids"])=={
        "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1",
        "BRAIN_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1",
    }
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    rec=a["coding_finite_exact_oracle_constructive_region_terminal_reconciliation_20261009_v1"]
    assert rec["private_cursorbench_membership_delta"]==0
    assert rec["whole_cursorbench_cover_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0

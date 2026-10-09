import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
DOC=ROOT/"canonical/governance/CODING_TYPED_SPECIALIST_POLICY_COVER_DEFICIT_20261009_V1.json"
VER=ROOT/"canonical/verification/CODING_TYPED_SPECIALIST_POLICY_COVER_DEFICIT_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_terminal_binds_policy_cover_deficit_without_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    src=a["authoritative_sources"]["coding_typed_specialist_policy_cover_deficit_20261009_v1"]
    assert blob(DOC)==src["git_blob_sha"]
    assert blob(VER)==src["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["coding_typed_specialist_policy_cover_deficit_proved"] is True
    assert live["coding_typed_specialist_policy_cover_basis_atom_count"]==5
    assert live["coding_typed_specialist_policy_cover_total_boolean_valuations"]==32
    assert live["coding_typed_specialist_policy_cover_covered_valuations"]==1
    assert live["coding_typed_specialist_policy_cover_uncovered_valuations"]==31
    assert live["coding_current_registry_scope_complete_on_unconstrained_typed_lattice"] is False
    assert live["coding_current_registry_p3_closure_ready_without_new_policy_or_source_constraints"] is False
    rec=a["coding_typed_specialist_policy_cover_deficit_reconciliation_20261009_v1"]
    assert rec["target_realizability_of_uncovered_valuations_claimed"] is False
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0

if __name__=="__main__":
    test_terminal_binds_policy_cover_deficit_without_credit()
    print("PASS 1/1")

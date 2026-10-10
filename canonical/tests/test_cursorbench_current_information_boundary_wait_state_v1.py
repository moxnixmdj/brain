import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
A=ROOT/"canonical/governance/CURSORBENCH_CURRENT_INFORMATION_BOUNDARY_WAIT_STATE_RECONCILIATION_20261010_V1.json"

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_cursorbench_wait_state_is_exactly_bound_and_zero_credit():
    a=json.loads(A.read_text())
    for row in a["sources"].values():
        p=ROOT/row["path"]
        assert p.is_file(), row
        assert blob(p)==row["git_blob_sha"], row
    assert a["route_state"]["route_A"]["state"]=="DORMANT_PENDING_SOURCE_DELTA"
    assert len(a["route_state"]["route_A"]["remaining_objects"])==2
    assert a["route_state"]["target_membership"]["current_region_count"]==5
    assert a["route_state"]["target_membership"]["complement_emptiness_identified"] is False
    assert a["route_state"]["constructive_scope_theorem"]["state"]=="BLOCKED_BY_CURRENT_INFORMATION"
    assert a["route_state"]["finite_complete_cell"]["known_complete_v5_cells"]==["wal-recovery-ordering"]
    assert a["route_state"]["finite_complete_cell"]["known_complete_v5_cell_target_relevance_to_cursorbench"] is False
    assert a["route_state"]["sixth_region"]["current_registered_conditioned_policy_count"]==6
    assert a["route_state"]["sixth_region"]["current_registered_coding_constructive_policy_count"]==5
    assert a["scheduler"]["cursorbench_internal_execution_state"]=="DORMANT_INFORMATION_BOUNDARY"
    assert a["scheduler"]["immediate_internal_cursorbench_job"] is None
    assert a["execution_authority"] is False
    assert a["accounting"]["acceptance_credit_delta"]==0
    assert a["accounting"]["terminal_credit_delta"]==0
    assert a["terminal_authority"] is False

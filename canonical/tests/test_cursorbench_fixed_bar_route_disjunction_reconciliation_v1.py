import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "canonical/governance/CURSORBENCH_FIXED_BAR_ROUTE_DISJUNCTION_RECONCILIATION_20261009_V1.json"

def blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_cursorbench_route_disjunction_reconciles_threshold_and_four_atom_frontier():
    rec=json.loads(REC.read_text(encoding="utf-8"))
    for ref in rec["sources"].values():
        p=ROOT/ref["path"]
        assert blob(p)==ref["git_blob_sha"], ref

    a=rec["route_disjunction"]["route_A_threshold_lower_bound"]
    b=rec["route_disjunction"]["route_B_scope_complete_stronger_proof"]

    assert a["sufficient"] is True
    assert a["whole_scope_positive_adequacy_required"] is False
    assert a["current_state"]=="OPEN_BLOCKED"

    assert b["sufficient"] is True
    assert b["current_state"]=="OPEN_INTERNAL"
    assert b["current_specialist_edge_registered"] is True
    assert b["typed_acceptance_membership_atom_count_total"]==5
    assert b["typed_acceptance_membership_atom_count_structurally_internalized"]==1
    assert b["typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    assert len(b["remaining_external_membership_atoms"])==4

    assert rec["scheduler"]["current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert rec["accounting"]["acceptance_credit_delta"]==0
    assert rec["accounting"]["terminal_credit_delta"]==0

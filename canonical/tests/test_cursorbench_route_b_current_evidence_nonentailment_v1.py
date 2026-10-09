import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/CURSORBENCH_ROUTE_B_CURRENT_EVIDENCE_NONENTAILMENT_20261009_V1.json"

def test_current_route_b_evidence_admits_opposite_cover_worlds():
    p=json.loads(P.read_text(encoding="utf-8"))
    f=p["formal_nonentailment"]
    g=f["good_world"]; b=f["bad_world"]
    for key in ("S","K","U","T","F"):
        assert g[key]==b[key]
    assert g["H"] is True and b["H"] is False
    assert g["C"] is True and b["C"] is False
    assert p["independent_boolean_check"]["result"]["good_world_satisfiable"] is True
    assert p["independent_boolean_check"]["result"]["bad_world_satisfiable"] is True
    assert p["independent_boolean_check"]["result"]["premise_entails_cover"] is False
    assert p["independent_boolean_check"]["result"]["premise_entails_not_cover"] is False
    assert len(p["exact_escape_classes"])==3
    assert p["accounting"]["acceptance_credit_delta"]==0
    assert p["accounting"]["terminal_credit_delta"]==0

def test_theorem_preserves_future_escape_routes():
    p=json.loads(P.read_text(encoding="utf-8"))
    ids={x["id"] for x in p["exact_escape_classes"]}
    assert ids=={
        "CONSTRUCTIVE_SCOPE_THEOREM",
        "TARGET_RELEVANT_COMPLETE_ADEQUACY_EVIDENCE",
        "ROUTE_A_SCORE_LOWER_BOUND",
    }
    assert "NO_CLAIM_CURSORBENCH_ROUTE_B_IS_IMPOSSIBLE" in p["hard_nonclaims"]
    assert "NO_CLAIM_NO_CONSTRUCTIVE_SCOPE_THEOREM_CAN_BE_BUILT" in p["hard_nonclaims"]

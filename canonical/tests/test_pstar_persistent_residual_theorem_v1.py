import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"canonical/governance/PSTAR_PERSISTENT_RESIDUAL_THEOREM_20261007_V1.json"

def load(): return json.loads(P.read_text())

def test_routes():
    d=load()
    assert set(d["nonpersistent_routes"])=={"A","D","V","U","R"}

def test_positive_p_is_last_resort():
    d=load()
    req=" ".join(d["theorem"]["positive_p_requires"])
    assert "A_D_V_U_R" in req
    assert "ROUTE_SET_COMPLETE" in req

def test_failure_to_find_not_impossibility():
    assert "FAILURE_TO_FIND" in load()["theorem"]["warning"]

def test_zero_credit():
    assert all(v==0 for k,v in load()["accounting"].items() if k.endswith("_delta"))

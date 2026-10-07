import json
from pathlib import Path
from canonical.runtime.v13_native_artifact_mechanical_selected_cell_verifier_v1 import verify

ROOT=Path(__file__).resolve().parents[2]
B=ROOT/"canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json"

def test_current_cell_verifies():
    x=verify()
    assert x["pass"] is True,x
    assert x["cell_closed"] is True
    assert x["family_closed"] is False
    assert x["abc_closed"] is False
    assert x["terminal_credit_delta"]==0

def test_bundle_keeps_semantic_and_quality_scope_out():
    d=json.loads(B.read_text())
    c=d["selected_cell"]
    assert c["semantic_target_selection"] is False
    assert c["professional_quality_judgment"] is False
    assert "NO_WHOLE_ARTIFACT_FAMILY_CLOSURE" in d["hard_nonclaims"]

def test_d_finality_remains_open():
    d=json.loads(B.read_text())
    assert d["D_boundary"]["global_D_finality"]=="OPEN"

import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"canonical/governance/SYNTHESIS_MATCHED_QUALITY_NECESSITY_TRUTH_REPAIR_20261007_V1.json"

def load(): return json.loads(P.read_text())

def test_scope_dimensions_preserved():
    d=load()
    assert len(d["established_scope"]["dimensions"])==6
    assert d["truth_repair"]["preserve"]=="EVERY_TERMINALLY_USEFUL_SYNTHESIS_QUALITY_DISTINCTION"

def test_metric_identity_only_is_attacked():
    d=load()
    assert d["truth_repair"]["delete_only"]=="MATCHED_QUALITY_METRIC_IDENTITY_AS_UNCONDITIONAL_TERMINAL_AXIOM"
    assert "ADDITIONAL_USEFUL_QUALITY_DIMENSION" in d["truth_repair"]["reopen_if"]

def test_no_family_or_pstar_overclaim():
    d=load()
    assert "NO_CLAIM_SYNTHESIS_FAMILY_ACCEPTED" in d["hard_nonclaims"]
    assert "NO_CLAIM_P_STAR_EQUALS_ZERO" in d["hard_nonclaims"]

def test_zero_credit():
    assert all(v==0 for k,v in load()["accounting"].items() if k.endswith("_delta"))

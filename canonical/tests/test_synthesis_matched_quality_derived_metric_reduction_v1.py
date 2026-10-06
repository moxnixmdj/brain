import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"canonical/governance/SYNTHESIS_MATCHED_QUALITY_DERIVED_METRIC_REDUCTION_20261007_V1.json"

def load(): return json.loads(P.read_text())

def test_exact_five_components():
    assert len(load()["semantic_components"])==5

def test_matched_quality_is_derived():
    d=load()
    assert d["derivation"]["otherwise"]=="matched_quality=MIN_OF_FIVE_SEMANTIC_COMPONENT_SCORES"
    assert d["consequence"]["delete_as_independent_semantic_residual"]=="metric:matched_quality"

def test_performance_obligation_preserved():
    assert "NONINFERIOR" in load()["consequence"]["preserve_performance_obligation"]

def test_no_pstar_overclaim():
    assert "NO_CLAIM_P_STAR_EQUALS_ZERO" in load()["hard_nonclaims"]

def test_zero_credit():
    assert all(v==0 for k,v in load()["accounting"].items() if k.endswith("_delta"))

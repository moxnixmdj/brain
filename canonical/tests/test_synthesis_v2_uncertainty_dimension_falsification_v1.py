import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/SYNTHESIS_V2_UNCERTAINTY_DIMENSION_FALSIFICATION_20261007_V1.json"

def load():
    return json.loads(P.read_text())

def test_countermodel_reaches_non_ceiling_quality():
    c=load()["countermodel"]
    assert c["all_current_v2_declared_coordinates_hold"] is True
    assert c["required_uncertainty_units_total"]==1
    assert c["required_uncertainty_units_preserved"]==0
    assert c["frozen_uncertainty_component_score"]==0
    assert c["matched_quality_ceiling_reached"] is False

def test_runtime_audit_distinguishes_conflict_from_uncertainty():
    a=load()["source_audit"]
    assert a["runtime_contains_conflict_handling"] is True
    assert a["runtime_contains_uncertainty_binding"] is False
    assert a["runtime_contains_disagreement_binding"] is False

def test_repair_preserves_stronger_routes():
    opts=load()["truth_repair"]["minimum_repair_options"]
    assert len(opts)==3
    assert any("ZERO_REQUIRED_UNCERTAINTY" in x for x in opts)
    assert any("EXACT_REQUIRED_UNCERTAINTY" in x for x in opts)

def test_zero_credit():
    d=load()["accounting"]
    assert d["terminal_credit_delta"]==0
    assert d["capability_credit_delta"]==0

from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

def test_current_component_authority_is_exact_four_of_twelve():
    a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    t=a["truth"]
    assert t["frozen_interface_count"]==12
    assert t["current_admissible_scoped_proved"]==4
    assert t["current_open"]==8
    assert t["current_scoped_proved_components"]==["memory","recovery","tool discovery","delegation"]
    assert t["parent_composition_predicate_closed"] is False
    assert t["strict_opus55_acceptance_delta"]==0

def test_authority_binds_independent_v6_slice():
    a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    s=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V6.json")
    assert s["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert s["verified"]["scoped_proved_count"]==4
    assert s["verified"]["open_count"]==8
    assert s["verified"]["scoped_proved_components"]==["memory","recovery","tool discovery","delegation"]
    assert a["current_slice"]["verification_git_blob_sha"]=="175e9aa0736ff7246240837f94d535bfdcbadcd2"

def test_tool_discovery_is_narrow_and_parent_open():
    a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    assert "tool discovery" in a["truth"]["current_scoped_proved_components"]
    assert "coding" in a["open_components"] and "debugging" in a["open_components"]
    assert a["truth"]["parent_composition_predicate_closed"] is False
    assert a["capability_credit_delta"]==0 and a["family_credit_delta"]==0
    assert a["execution_authority"] is False and a["promotion_authority"] is False

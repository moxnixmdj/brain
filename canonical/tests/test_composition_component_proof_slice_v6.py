from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
INP=ROOT/"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json"
CAND=ROOT/"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_CANDIDATE_V6.json"

def test_v6_exact_four_of_twelve_current_source_slice():
    doc=json.loads(INP.read_text(encoding="utf-8"))
    out=evaluate(doc)
    assert out["errors"]==[],out
    proved=[x["component_id"] for x in out["interfaces"] if x["state"]=="SCOPED_PROVED"]
    open_=[x["component_id"] for x in out["interfaces"] if x["state"]=="OPEN"]
    assert proved==["memory","recovery","tool discovery","delegation"],proved
    assert len(proved)==4 and len(open_)==8
    assert out["all_used_component_interfaces_scoped_proved"] is False
    expected=json.loads(CAND.read_text(encoding="utf-8"))
    for key in ("schema","errors","claim_id","interfaces","all_used_component_interfaces_scoped_proved","rule","new_reality_units_consumed","capability_credit_delta","family_credit_delta"):
        assert out[key]==expected[key],(key,out[key],expected[key])

def test_v6_tool_discovery_receipt_is_current_independent_and_narrow():
    doc=json.loads(INP.read_text(encoding="utf-8"))
    r=next(x for x in doc["receipts"] if x["component_id"]=="tool discovery")
    assert r["receipt_id"]=="COMPOSITION_SCOPE_COMPLETE_BRIDGE::TOOL_DISCOVERY_SELECTION_AND_LEARNING::tool_discovery::V1"
    assert r["verified"] is True and r["independent"] is True
    assert r["contamination_clean"] is True and r["acceptance_scoped"] is True
    assert r["proved_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
    out=evaluate(doc)
    coding=next(x for x in out["interfaces"] if x["component_id"]=="coding")
    debugging=next(x for x in out["interfaces"] if x["component_id"]=="debugging")
    assert coding["state"]=="OPEN" and debugging["state"]=="OPEN"

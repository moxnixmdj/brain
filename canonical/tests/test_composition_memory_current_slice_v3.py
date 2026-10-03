from __future__ import annotations
import json
from pathlib import Path

from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

inp = json.loads((ROOT / "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_20261003_V3.json").read_text(encoding="utf-8"))
expected = json.loads((ROOT / "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261003_V3.json").read_text(encoding="utf-8"))

out = evaluate(inp)
assert out["status"] == "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN", out
states = {x["component_id"]: x["state"] for x in out["interfaces"]}
assert states["memory"] == "SCOPED_PROVED", out
assert sum(v == "SCOPED_PROVED" for v in states.values()) == 1, out
assert sum(v == "OPEN" for v in states.values()) == 11, out
assert states["tool discovery"] == "OPEN", out
assert states["delegation"] == "OPEN", out
assert out["all_used_component_interfaces_scoped_proved"] is False, out
assert out["capability_credit_delta"] == 0 and out["family_credit_delta"] == 0, out

for key in ("schema","status","errors","claim_id","all_used_component_interfaces_scoped_proved","rule","new_reality_units_consumed","capability_credit_delta","family_credit_delta"):
    assert out[key] == expected[key], (key, out[key], expected[key])

for got, exp in zip(out["interfaces"], expected["interfaces"]):
    for key in ("component_id","interface_id","required_properties","proved_properties","missing_properties","extra_receipt_properties_ignored","supporting_receipt_ids","state"):
        assert got[key] == exp[key], (got["component_id"], key, got[key], exp[key])

assert expected["scoped_proved_count"] == 1
assert expected["open_count"] == 11
assert expected["current_admissible_scoped_proved_components"] == ["memory"]
assert set(expected["historical_quarantined_components_not_counted"]) == {"tool discovery","delegation"}
assert expected["parent_composition_acceptance"] is False

print("test_composition_memory_current_slice_v3: PASS")

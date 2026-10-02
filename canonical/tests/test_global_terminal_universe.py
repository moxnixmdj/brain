import json
from pathlib import Path
from canonical.runtime.global_terminal_universe import build_universe

ROOT = Path(__file__).resolve().parents[2]
u = build_universe()
frozen = json.loads((ROOT / "canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json").read_text())
graph = json.loads((ROOT / "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json").read_text())
prequalification = json.loads((ROOT / "canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").read_text())

assert u == frozen
assert u["counts"]["families_total"] == 19
assert u["counts"]["families_closed"] == 2
assert u["counts"]["families_open_proof"] == 17

universe_lanes = {row["id"]: row for row in u["shared_mechanism_accounting"]["lanes"]}
graph_lanes = {row["id"]: row for row in graph["shared_mechanism_obligations"]}
assert {k.split("_", 1)[0] for k in universe_lanes} == {"M0", "M1", "M2", "M3", "M4", "M5"}
assert set(universe_lanes) == set(graph_lanes)

proof_only = set(graph.get("proof_only_mechanism_obligations", []))
open_mechanisms = list(graph.get("open_mechanism_residuals", []))
assert graph["open_mechanism_residual_count"] == len(open_mechanisms)

for lane_id, lane in universe_lanes.items():
    expected_hole = (
        "?P" if lane_id in proof_only
        else "?M" if lane_id in open_mechanisms
        else "CLOSED"
    )
    assert lane["hole_type"] == expected_hole, (lane_id, lane["hole_type"], expected_hole)

assert "G_REQUIRED_BEHAVIOR_CONTRACT_COMPLETENESS" not in u["global_cut"]["open_specification_holes"]
assert u["counts"]["open_specification_holes"] == 0
assert u["counts"]["open_mechanism_lanes"] == len(open_mechanisms)

shared_open = list(graph.get("shared_cross_lane_open_mechanisms", []))
gate_mech = [
    x["id"]
    for x in u["global_terminal_gates"]
    if x["hole_type"] == "?M" and not x["closed"]
]
assert u["global_cut"]["open_mechanism_holes"] == open_mechanisms + shared_open + gate_mech
assert "D0_NATIVE_STRUCTURED_ARTIFACT_EDIT_TAIL" not in u["global_cut"]["open_mechanism_holes"]
assert "M2_PROFESSIONAL_ARTIFACT_AND_DOCUMENT_CONTROL" not in u["global_cut"]["open_mechanism_holes"]
if "open_shared_cross_lane_mechanism_primitive_count" in u["counts"]:
    assert u["counts"]["open_shared_cross_lane_mechanism_primitive_count"] == len(shared_open)

# Donor-independence, unexplained-behavior, and composition-zero are terminal proof
# predicates. They remain mandatory for final closure but may not circularly block
# the exact portfolios that measure them.
if not open_mechanisms and not shared_open and not gate_mech:
    assert u["global_cut"]["exact_cut_ready"] is True
    assert u["global_cut"]["prequalification_ready"] is bool(prequalification["execution_authority"])
    assert u["global_cut"]["execution_ready"] is bool(prequalification["execution_authority"])
    assert u["execution_authority"]["fresh_terminal_evidence_allowed"] is bool(prequalification["execution_authority"])
    if prequalification["execution_authority"]:
        assert u["execution_authority"]["immediate_zero_reality_work"] == []
    else:
        assert u["execution_authority"]["immediate_zero_reality_work"] == prequalification["next"]
        assert u["status"].endswith("PREQUALIFICATION_BLOCKED")
else:
    assert u["global_cut"]["exact_cut_ready"] is False
    assert u["global_cut"]["execution_ready"] is False
    assert u["execution_authority"]["fresh_terminal_evidence_allowed"] is False
    assert u["execution_authority"]["immediate_zero_reality_work"] == (
        [f"CLOSE_OR_EXACTLY_BOUND_{x}" for x in open_mechanisms + shared_open]
        + [f"CLOSE_{x}" for x in gate_mech]
    )
assert u["terminal_prequalification"]["source"] == "canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json"
assert u["terminal_prequalification"]["execution_authority"] is bool(prequalification["execution_authority"])
assert u["local_v6_subcut"]["exact_minimum"] is True
assert u["local_v6_subcut"]["globally_authorized"] is False
assert len(u["local_v6_subcut"]["selected_observations"]) == 2

for lane in graph["shared_mechanism_obligations"]:
    if lane["id"].split("_", 1)[0] in {"M2", "M3", "M4", "M5"}:
        assert "canonical/capabilities/opus55/SHARED_BOUNDED_DECISION_PRIMITIVES_001.json" in lane.get("existing_evidence", [])

print("GLOBAL_TERMINAL_UNIVERSE_V1 verification: PASS")

# PR verification trigger: compiler behavior unchanged.

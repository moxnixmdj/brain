import json
from pathlib import Path
from canonical.runtime.global_terminal_universe import build_universe

ROOT = Path(__file__).resolve().parents[2]
u = build_universe()
frozen = json.loads((ROOT / "canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json").read_text())

assert u == frozen
assert u["counts"]["families_total"] == 19
assert u["counts"]["families_closed"] == 2
assert u["counts"]["families_open_proof"] == 17

lane_keys = {row["id"].split("_", 1)[0] for row in u["shared_mechanism_accounting"]["lanes"]}
assert lane_keys == {"M0", "M1", "M2", "M3", "M4", "M5"}

holes = {row["id"]: row["hole_type"] for row in u["shared_mechanism_accounting"]["lanes"]}
assert holes["M0_SEMANTIC_SPEC_AND_INDEPENDENT_ACCEPTANCE"] == "?P"
assert holes["M1_STRUCTURED_CONSTRUCTION_AND_GEOMETRIC_REALIZATION"] == "?P"
for key in (
    "M2_PROFESSIONAL_ARTIFACT_AND_DOCUMENT_CONTROL",
    "M3_INTERACTIVE_AGENCY_TOOL_AND_DELEGATION_CONTROL",
    "M4_RESEARCH_AND_UNKNOWN_DOMAIN_CONTROL",
    "M5_FAILURE_LOCALIZATION_SCOPE_AND_RECOVERY",
):
    assert holes[key] == "?M"

assert "G_REQUIRED_BEHAVIOR_CONTRACT_COMPLETENESS" not in u["global_cut"]["open_specification_holes"]
assert u["counts"]["open_specification_holes"] == 0
assert u["global_cut"]["exact_cut_ready"] is False
assert u["execution_authority"]["fresh_terminal_evidence_allowed"] is False
assert u["local_v6_subcut"]["exact_minimum"] is True
assert u["local_v6_subcut"]["globally_authorized"] is False
assert len(u["local_v6_subcut"]["selected_observations"]) == 2

graph = json.loads((ROOT / "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json").read_text())
for lane in graph["shared_mechanism_obligations"]:
    if lane["id"].split("_", 1)[0] in {"M2", "M3", "M4", "M5"}:
        assert "canonical/capabilities/opus55/SHARED_BOUNDED_DECISION_PRIMITIVES_001.json" in lane.get("existing_evidence", [])

print("GLOBAL_TERMINAL_UNIVERSE_V1 verification: PASS")

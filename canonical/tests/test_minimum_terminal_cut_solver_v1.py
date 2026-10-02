import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.minimum_terminal_cut_solver_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ir = compile_ir(
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
    load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"),
)
r = evaluate(ir)

assert r["status"] == "EXACT_TERMINAL_ACTION_CUT_COMPUTED", r
assert r["unresolved_predicate_count"] == 29, r
assert r["new_reality_units_consumed"] == 0
assert r["capability_credit_delta"] == 0
assert r["family_credit_delta"] == 0
assert r["execution_authority"] is False
assert r["promotion_authority"] is False

gaps = {x["precondition_id"]: x["blocked_target_predicates"] for x in r["blocked_preconditions"]}
assert "EXPLICIT_FINITE_WORLD_OR_HYPOTHESIS_SET_AVAILABLE" in gaps, r
assert "FROZEN_COMPOSITION_COMPONENT_INTERFACES_EXPLICIT" in gaps, r
assert "COMPOSITION_COMPONENT_SCOPED_PROOFS" in r["uncovered_predicates"], r

synthetic = {
    "status": "PASS",
    "predicates": [
        {"id": "P1", "state": "OPEN"},
        {"id": "P2", "state": "OPEN"},
    ],
    "actions": [
        {
            "id": "wide",
            "unresolved_target_predicates": ["P1", "P2"],
            "new_reality_units": 1,
            "available_now": True,
            "unsatisfied_preconditions": [],
            "critical_path": True,
        },
        {
            "id": "p1",
            "unresolved_target_predicates": ["P1"],
            "new_reality_units": 0,
            "available_now": True,
            "unsatisfied_preconditions": [],
            "critical_path": False,
        },
        {
            "id": "p2",
            "unresolved_target_predicates": ["P2"],
            "new_reality_units": 0,
            "available_now": True,
            "unsatisfied_preconditions": [],
            "critical_path": False,
        },
    ],
}
s = evaluate(synthetic)
assert s["selected_actions"] == ["p1", "p2"], s
assert s["selected_new_reality_units"] == 0, s
assert s["covered_predicate_count"] == 2, s

print("test_minimum_terminal_cut_solver_v1: PASS")

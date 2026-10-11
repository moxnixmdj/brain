import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
ir = compile_ir(registry, evidence, hypergraph)

proved_ids = {x["predicate_id"] for x in evidence["claims"] if x.get("state") == "PROVED"}
blocked_states = {"EXTERNAL_BLOCKED", "BLOCKED", "DEPENDENCY_BLOCKED"}
expected_blocked = sum(x.get("state") in blocked_states for x in evidence["claims"])
by_family = {}
for row in registry["predicates"]:
    by_family.setdefault(row["family"], set()).add(row["id"])
expected_closed_families = sum(ids <= proved_ids for ids in by_family.values())

assert ir["status"] == "PASS", ir
assert ir["predicate_count"] == len(registry["predicates"]), ir
assert ir["proved_predicate_count"] == len(proved_ids), ir
assert ir["unresolved_predicate_count"] == len(registry["predicates"]) - len(proved_ids), ir
assert ir["blocked_predicate_count"] == expected_blocked, ir
assert ir["closed_residual_family_count"] == expected_closed_families, ir
assert ir["uncovered_unresolved_predicates"] == [], ir
assert ir["new_reality_units_consumed"] == 0
assert ir["capability_credit_delta"] == 0
assert ir["family_credit_delta"] == 0
assert ir["execution_authority"] is False
assert ir["promotion_authority"] is False

actions = {x["id"]: x for x in ir["actions"]}
source_actions = {x["id"]: x for x in hypergraph["actions"]}
for aid, actual in actions.items():
    expected_unsatisfied = sorted(
        p["id"] for p in source_actions[aid].get("preconditions", [])
        if p.get("satisfied") is False
    )
    assert actual["unsatisfied_preconditions"] == expected_unsatisfied, (aid, actual)
    assert actual["available_now"] is (not expected_unsatisfied), (aid, actual)

print("test_acceptance_ir_compiler_v1: PASS")

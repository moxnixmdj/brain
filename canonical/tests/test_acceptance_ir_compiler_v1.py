import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ir = compile_ir(
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
    load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"),
)

assert ir["status"] == "PASS", ir
assert ir["predicate_count"] == 38, ir
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir
assert ir["blocked_predicate_count"] == 3, ir
assert ir["closed_residual_family_count"] == 2, ir
assert ir["uncovered_unresolved_predicates"] == [], ir
assert ir["new_reality_units_consumed"] == 0
assert ir["capability_credit_delta"] == 0
assert ir["family_credit_delta"] == 0
assert ir["execution_authority"] is False
assert ir["promotion_authority"] is False

actions = {x["id"]: x for x in ir["actions"]}
assert actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["available_now"] is True
assert actions["RUN_EPISTEMIC_CLOSURE_DIRECT_JUDGMENT_SUBTRACTION"]["available_now"] is False
assert actions["RUN_EPISTEMIC_CLOSURE_DIRECT_JUDGMENT_SUBTRACTION"]["unsatisfied_preconditions"] == [
    "EXPLICIT_FINITE_WORLD_OR_HYPOTHESIS_SET_AVAILABLE"
]
assert actions["RUN_COMPOSITION_COMPONENT_PROOF_SLICER"]["available_now"] is False
assert actions["RUN_COMPOSITION_COMPONENT_PROOF_SLICER"]["unsatisfied_preconditions"] == [
    "FROZEN_COMPOSITION_COMPONENT_INTERFACES_EXPLICIT"
]

print("test_acceptance_ir_compiler_v1: PASS")

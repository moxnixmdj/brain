import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_evaluate
from canonical.runtime.minimum_terminal_cut_solver_v1 import evaluate as cut_evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


receipt = load("canonical/verification/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
activation = load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_ACTIVATION_V1.json")
manifest = load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
slice_input = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json")
slice_expected = load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261002_V1.json")

assert receipt["status"] == "INDEPENDENT_PUBLIC_RUNNER_PASS__LITERAL_12_INTERFACE_RECOMPUTATION__ZERO_CREDIT", receipt
assert activation["status"] == "ACTIVE_INDEPENDENT_PASS__12_LITERAL_INTERFACES_EXPLICIT__RECEIPT_BINDINGS_OPEN__ZERO_CREDIT", activation
assert manifest["isolated_component_interface_count"] == 12, manifest
assert activation["exact_state"]["component_interfaces_explicit"] is True
assert activation["exact_state"]["family_bindings_complete"] is False
assert activation["exact_state"]["receipt_bindings_complete"] is False
assert activation["capability_credit_delta"] == 0
assert activation["family_credit_delta"] == 0
assert activation["execution_authority"] is False
assert activation["promotion_authority"] is False

action = next(a for a in hypergraph["actions"] if a["id"] == "RUN_COMPOSITION_COMPONENT_PROOF_SLICER")
pre = next(p for p in action["preconditions"] if p["id"] == "FROZEN_COMPOSITION_COMPONENT_INTERFACES_EXPLICIT")
assert pre["satisfied"] is True, pre
assert pre["evidence"] == "canonical/verification/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json", pre

slice_actual = slice_evaluate(slice_input)
assert slice_actual == slice_expected, (slice_actual, slice_expected)
assert slice_actual["all_used_component_interfaces_scoped_proved"] is False
assert len(slice_actual["interfaces"]) == 12
assert all(x["state"] == "OPEN" for x in slice_actual["interfaces"])

ir = compile_ir(
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
    load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
    hypergraph,
)
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir
cut = cut_evaluate(ir)
assert cut["status"] == "EXACT_TERMINAL_ACTION_CUT_COMPUTED", cut
assert cut["covered_predicate_count"] == 29, cut
assert cut["uncovered_predicates"] == [], cut
assert "RUN_COMPOSITION_COMPONENT_PROOF_SLICER" in cut["selected_actions"], cut
assert cut["selected_new_reality_units"] == 0, cut
assert cut["capability_credit_delta"] == 0
assert cut["family_credit_delta"] == 0
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False

print("test_composition_interface_activation_v1: PASS")

import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

receipt = load("canonical/verification/OPUS55_BRAIN_WITNESS_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
normalization = load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json")
refinement = load("canonical/governance/OPUS55_PROTOCOL_IMPLICATION_GATE_REFINEMENT_V1.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")

assert receipt["target_atom_mapping_verified"] is False, receipt
assert receipt["semantic_implication_verified"] is False, receipt
assert normalization["witness_normalization_verified"] is True, normalization
assert normalization["semantic_implication_verified"] is False, normalization
assert all(w["normalized_target_atoms"] == [] for w in normalization["witnesses"])
assert all(w["semantic_implications"] == [] for w in normalization["witnesses"])

state = refinement["exact_gate_state"]
assert state["brain_witness_catalog_independent_pass"] is True, state
assert state["brain_witness_target_atom_metric_bindings_independent_pass"] is False, state
assert state["brain_witness_contamination_admissibility_independent_pass"] is False, state
assert state["protocol_implication_scope_algebra_available"] is False, state

actions = {a["id"]: a for a in hypergraph["actions"]}
imp = actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]
pre = {p["id"]: p for p in imp["preconditions"]}
assert pre["MATCHED_BRAIN_WITNESS_CATALOG_INDEPENDENT_PASS"]["satisfied"] is True, pre
assert pre["MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS"]["satisfied"] is False, pre
assert pre["MATCHED_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_INDEPENDENT_PASS"]["satisfied"] is False, pre

ir = compile_ir(registry, evidence, hypergraph)
ir_actions = {a["id"]: a for a in ir["actions"]}
assert ir_actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["available_now"] is False, ir_actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]
assert ir_actions["SEARCH_SCOPE_COMPLETE_STRONGER_PROOFS_FOR_MATCHED_RESIDUAL"]["available_now"] is True
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir

print("test_protocol_implication_gate_refinement_v1: PASS")

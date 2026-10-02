import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.minimum_terminal_cut_solver_v1 import evaluate as cut_evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


receipt = load("canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
activation = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_ACTIVATION_V1.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")

assert receipt["status"] == "INDEPENDENT_PUBLIC_RUNNER_PASS__11_OF_11_TARGETS__47_OF_47_ATOMS__10_OF_10_METRICS_SOURCE_BOUND__ZERO_CREDIT", receipt
assert activation["status"] == "ACTIVE_INDEPENDENT_PASS__TARGET_SOURCE_PROVENANCE_VERIFIED__BRAIN_WITNESS_NORMALIZATION_OPEN__ZERO_CREDIT", activation
assert activation["exact_state"]["target_source_provenance_verified"] is True
assert activation["exact_state"]["semantic_implication_verified"] is False
assert activation["exact_state"]["brain_witness_normalization_verified"] is False

actions = {a["id"]: a for a in hypergraph["actions"]}
imp = actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]
diff = actions["RUN_FINITE_DIFFERENTIAL_DOMINANCE_ELIMINATION"]

ip = {p["id"]: p for p in imp["preconditions"]}
dp = {p["id"]: p for p in diff["preconditions"]}

assert ip["MATCHED_TARGET_NORMALIZATION_INDEPENDENT_PASS"]["satisfied"] is True, ip
assert ip["MATCHED_BRAIN_WITNESS_NORMALIZATION_INDEPENDENT_PASS"]["satisfied"] is False, ip
assert dp["MATCHED_TARGET_NORMALIZATION_INDEPENDENT_PASS"]["satisfied"] is True, dp
assert dp["COMPLETE_FROZEN_FINITE_SHARED_CRITERION_SCOPE_AVAILABLE_PER_TARGET"]["satisfied"] is False, dp

ir = compile_ir(registry, evidence, hypergraph)
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir
ir_actions = {a["id"]: a for a in ir["actions"]}
assert ir_actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["available_now"] is False, ir_actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]
assert ir_actions["RUN_FINITE_DIFFERENTIAL_DOMINANCE_ELIMINATION"]["available_now"] is False, ir_actions["RUN_FINITE_DIFFERENTIAL_DOMINANCE_ELIMINATION"]
assert ir_actions["SEARCH_SCOPE_COMPLETE_STRONGER_PROOFS_FOR_MATCHED_RESIDUAL"]["available_now"] is True

cut = cut_evaluate(ir)
assert cut["status"] == "EXACT_TERMINAL_ACTION_CUT_COMPUTED", cut
assert cut["covered_predicate_count"] == 29, cut
assert cut["uncovered_predicates"] == [], cut
assert "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA" not in cut["selected_actions"], cut
assert "SEARCH_SCOPE_COMPLETE_STRONGER_PROOFS_FOR_MATCHED_RESIDUAL" in cut["selected_actions"], cut
assert cut["selected_new_reality_units"] == 0, cut
assert cut["capability_credit_delta"] == 0
assert cut["family_credit_delta"] == 0
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False

print("test_matched_target_normalization_activation_v1: PASS")

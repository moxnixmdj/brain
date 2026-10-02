from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.minimum_terminal_cut_solver_v1 import evaluate as cut_evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
hypergraph=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")

ir=compile_ir(registry,evidence,hypergraph)
assert ir["status"] in {"PASS","PASS_WITH_UNCOVERED_ACTION_TARGETS"}, ir
assert ir["predicate_count"] == 38, ir
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir
actions={a["id"]:a for a in ir["actions"]}
assert actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["available_now"] is True, actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]
assert actions["RUN_COMPOSITION_COMPONENT_PROOF_SLICER"]["available_now"] is True, actions["RUN_COMPOSITION_COMPONENT_PROOF_SLICER"]

cut=cut_evaluate(ir)
assert cut["status"] == "EXACT_TERMINAL_ACTION_CUT_COMPUTED", cut
assert cut["unresolved_predicate_count"] == 29, cut
assert cut["covered_predicate_count"] == 29, cut
assert cut["uncovered_predicates"] == [], cut
assert cut["selected_new_reality_units"] == 0, cut
assert cut["capability_credit_delta"] == 0, cut
assert cut["family_credit_delta"] == 0, cut
assert cut["execution_authority"] is False, cut
assert cut["promotion_authority"] is False, cut
print(json.dumps({
    "status":"PASS",
    "proved_predicates":ir["proved_predicate_count"],
    "unresolved_predicates":ir["unresolved_predicate_count"],
    "available_implication_algebra":actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["available_now"],
    "available_composition_slicer":actions["RUN_COMPOSITION_COMPONENT_PROOF_SLICER"]["available_now"],
    "covered_predicates":cut["covered_predicate_count"],
    "selected_actions":cut["selected_actions"],
    "selected_new_reality_units":cut["selected_new_reality_units"],
},sort_keys=True))

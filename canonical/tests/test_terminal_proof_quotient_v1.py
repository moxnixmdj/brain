import json
from pathlib import Path

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.terminal_proof_quotient_v1 import evaluate as quotient_evaluate
from canonical.runtime.composition_receipt_autobinder_v1 import evaluate as autobind_evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
manifest = load("canonical/governance/TERMINAL_PROOF_QUOTIENT_MANIFEST_V1.json")

ir = compile_ir(registry, evidence, hypergraph)
assert ir["proved_predicate_count"] == 9, ir
assert ir["unresolved_predicate_count"] == 29, ir

quotient = quotient_evaluate(ir, manifest)
assert quotient["status"] == "PASS_EXACT_LOSSLESS_UNRESOLVED_QUOTIENT", quotient
assert quotient["unresolved_predicate_count"] == 29, quotient
assert quotient["covered_predicate_count"] == 29, quotient
assert quotient["uncovered_predicates"] == [], quotient
assert quotient["multiply_assigned_predicates"] == [], quotient
counts = {x["id"]: x["target_count"] for x in quotient["fronts"]}
assert counts == {
    "COMPOSITION_COMPONENT_PROOF_FRONT": 1,
    "JUDGMENT_SOURCE_FRONT": 2,
    "MATCHED_AND_SCOPE_PROOF_FRONT": 11,
    "PUBLIC_BAR_AND_ROUTE_FRONT": 15,
}, counts
assert quotient["capability_credit_delta"] == 0
assert quotient["family_credit_delta"] == 0
assert quotient["execution_authority"] is False
assert quotient["promotion_authority"] is False

# The live composition slice intentionally contains no claim-bound receipts yet.
slice_input = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json")
baseline = autobind_evaluate(slice_input)
assert baseline["status"] == "RESIDUAL_EXACT_INTERFACE_RECEIPTS_OPEN", baseline
assert baseline["bound_interface_count"] == 0, baseline
assert baseline["open_interface_count"] == 12, baseline
assert baseline["all_used_component_interfaces_scoped_proved"] is False

# Exact explicit receipt metadata can bind; names or family membership alone cannot.
synthetic = json.loads(json.dumps(slice_input))
first = synthetic["interfaces"][0]
synthetic["receipts"] = [{
    "receipt_id": "synthetic://exact",
    "claim_id": synthetic["claim_id"],
    "component_id": first["component_id"],
    "interface_id": first["interface_id"],
    "properties": ["SCOPED_ACCEPTANCE_PROOF"],
    "verified": True,
    "independent": True,
    "contamination_clean": True,
    "acceptance_scoped": True,
    "source_path": "synthetic/path",
    "source_sha": "deadbeef"
}]
one = autobind_evaluate(synthetic)
assert one["bound_interface_count"] == 1, one
assert one["open_interface_count"] == 11, one

bad = json.loads(json.dumps(synthetic))
bad["receipts"][0]["acceptance_scoped"] = False
rejected = autobind_evaluate(bad)
assert rejected["bound_interface_count"] == 0, rejected

print("test_terminal_proof_quotient_v1: PASS")

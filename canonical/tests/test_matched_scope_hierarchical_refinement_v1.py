import json
from pathlib import Path

from canonical.runtime.terminal_certificate_cut_v1 import evaluate as cut_evaluate
from canonical.runtime.terminal_information_dominance_v1 import evaluate as dominance_evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

global_frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
sub = load("canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json")
hyper = load("canonical/governance/MATCHED_SCOPE_BINDING_SUBHYPERGRAPH_V1.json")

parent = next(x for x in global_frontier["certificates"] if x["id"] == "MATCHED_SCOPE_BINDING_CERTIFICATE")
parent_targets = set(parent["target_predicates"])

assert set(sub["unresolved_predicates"]) == parent_targets
assert len(parent_targets) == 11
assert len(sub["certificates"]) == 11
assert len(hyper["actions"]) == 11

seen_targets = set()
for cert in sub["certificates"]:
    assert len(cert["target_predicates"]) == 1, cert
    assert len(cert["requires"]) == 2, cert
    target = cert["target_predicates"][0]
    assert target in parent_targets
    assert target not in seen_targets
    seen_targets.add(target)
    assert all(req.startswith(target + "::") for req in cert["requires"]), cert

action_targets = set()
for action in hyper["actions"]:
    assert len(action["target_predicates"]) == 1, action
    target = action["target_predicates"][0]
    assert target in parent_targets
    assert target not in action_targets
    action_targets.add(target)
    assert len(action["outputs"]) == 2
    assert all(out.startswith(target + "::") for out in action["outputs"]), action
    assert action["new_reality_units"] == 0

assert seen_targets == parent_targets
assert action_targets == parent_targets

cut = cut_evaluate(sub)
assert cut["status"] == "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED", cut
assert cut["unresolved_predicate_count"] == 11, cut
assert cut["certificate_candidate_count"] == 11, cut
assert cut["covered_predicate_count"] == 11, cut
assert cut["uncovered_predicates"] == [], cut
assert cut["selected_certificate_count"] == 11, cut
assert cut["selected_new_reality_units"] == 0, cut

dom = dominance_evaluate(sub)
assert dom["status"] == "EXACT_INFORMATION_DOMINANCE_COMPUTED", dom
assert dom["certificate_count"] == 11, dom
assert dom["dominated_certificate_ids"] == [], dom
assert len(dom["nondominated_certificate_ids"]) == 11, dom
assert dom["best_full_frontier_bundle"]["covered_predicate_count"] == 11, dom
assert dom["best_full_frontier_bundle"]["unique_requirement_count"] == 22, dom

assert sub["capability_credit_delta"] == 0
assert sub["family_credit_delta"] == 0
assert sub["execution_authority"] is False
assert sub["promotion_authority"] is False
assert hyper["capability_credit_delta"] == 0
assert hyper["family_credit_delta"] == 0

print("test_matched_scope_hierarchical_refinement_v1: PASS")

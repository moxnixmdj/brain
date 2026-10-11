import json
from pathlib import Path

from canonical.runtime.terminal_certificate_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
frontier = json.loads((ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V2.json").read_text(encoding="utf-8"))
out = evaluate(frontier)

assert out["status"] == "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED", out
assert out["unresolved_predicate_count"] == 31, out
assert out["certificate_candidate_count"] == 15, out
assert out["covered_predicate_count"] == 31, out
assert out["uncovered_predicates"] == [], out
assert out["selected_certificate_count"] == 15, out
assert out["selected_new_reality_units"] == 0, out
assert "MATCHED_SCOPE_BINDING_CERTIFICATE" in out["selected_certificates"], out
assert "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" in out["selected_certificates"], out
assert "DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" in out["selected_certificates"], out

# The two reopened families have the same certificate class but distinct propositions.
classes = [q for q in out["quotient_classes"] if q["certificate_class"] == "ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS"]
assert len(classes) == 2, out
assert all(len(q["member_certificate_ids"]) == 1 for q in classes), out

# The scope-completeness correction must stay in the frontier.
assert "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in out["covered_predicates"], out
assert "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in out["covered_predicates"], out

assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("test_terminal_certificate_cut_v2: PASS")

import json
from pathlib import Path

from canonical.runtime.terminal_certificate_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V1.json")
out = evaluate(frontier)

assert out["status"] == "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED", out
assert out["unresolved_predicate_count"] == 31, out
assert out["certificate_candidate_count"] == 13, out
assert out["covered_predicate_count"] == 31, out
assert out["uncovered_predicates"] == [], out
assert out["selected_certificate_count"] == 13, out
assert out["selected_new_reality_units"] == 0, out
assert "MATCHED_SCOPE_BINDING_CERTIFICATE" in out["selected_certificates"], out
assert "COMPOSITION_INTERFACE_RECEIPT_BINDING_CERTIFICATE" in out["selected_certificates"], out
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

# Fail closed: a certificate may not silently claim a predicate outside the frontier.
bad = json.loads(json.dumps(frontier))
bad["certificates"][0]["target_predicates"].append("NOT_A_FRONTIER_PREDICATE")
failed = evaluate(bad)
assert failed["status"] == "FAIL_CLOSED", failed
assert any(x.startswith("CERTIFICATE_TARGET_OUTSIDE_FRONTIER") for x in failed["errors"]), failed

# Exact quotient behavior: genuinely identical certificate obligations are grouped,
# but merely overlapping targets are not merged.
tiny = {
    "unresolved_predicates": ["P1", "P2"],
    "certificates": [
        {"id": "A", "certificate_class": "X", "target_predicates": ["P1"], "requires": ["R"], "new_reality_units": 0},
        {"id": "B", "certificate_class": "X", "target_predicates": ["P1"], "requires": ["R"], "new_reality_units": 0},
        {"id": "C", "certificate_class": "X", "target_predicates": ["P1", "P2"], "requires": ["R2"], "new_reality_units": 0},
    ],
}
tiny_out = evaluate(tiny)
assert tiny_out["covered_predicate_count"] == 2, tiny_out
assert tiny_out["selected_certificates"] == ["C"], tiny_out
same = [q for q in tiny_out["quotient_classes"] if q["member_certificate_ids"] == ["A", "B"]]
assert len(same) == 1, tiny_out

print("test_terminal_certificate_cut_v1: PASS")

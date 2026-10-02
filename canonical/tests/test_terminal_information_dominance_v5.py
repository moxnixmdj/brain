import json
from pathlib import Path

from canonical.runtime.terminal_information_dominance_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
projection = load("canonical/governance/TERMINAL_INFORMATION_DOMINANCE_V5_PROJECTION.json")
out = evaluate(frontier)

assert out["status"] == "EXACT_INFORMATION_DOMINANCE_COMPUTED", out
p = projection["projection"]

assert out["unresolved_predicate_count"] == p["unresolved_predicate_count"] == 31
assert out["certificate_count"] == p["certificate_count"] == 17
assert out["highest_direct_coverage_count"] == p["highest_direct_coverage_count"] == 11
assert out["highest_direct_coverage_certificate_ids"] == p["highest_direct_coverage_certificate_ids"]
assert out["dominated_certificate_ids"] == p["dominated_certificate_ids"] == []
assert out["nondominated_certificate_ids"] == p["nondominated_certificate_ids"]

best = out["best_full_frontier_bundle"]
exp = p["best_full_frontier_bundle"]
assert best["certificate_ids"] == exp["certificate_ids"]
assert best["covered_predicate_count"] == exp["covered_predicate_count"] == 31
assert best["unique_requirement_count"] == exp["unique_requirement_count"] == 20
assert best["new_reality_units"] == exp["new_reality_units"] == 0

assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert projection["capability_credit_delta"] == 0
assert projection["family_credit_delta"] == 0
assert projection["execution_authority"] is False
assert projection["promotion_authority"] is False

print("test_terminal_information_dominance_v5: PASS")

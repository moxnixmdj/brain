import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "canonical/evidence/CURSORBENCH_4_0_ROUNDED_SCORE_LATTICE_NONIDENTIFIABILITY_20261010_V1.json"

def fits(score, n):
    return any(abs(100.0 * k / n - score) < 0.05 for k in range(n + 1))

def test_distinct_public_score_denominators_are_compatible():
    j = json.loads(E.read_text())
    scores = j["public_owner_source"]["scores_percent"]
    assert len(scores) == 68
    for n in (983, 1000, 1001):
        assert all(fits(score, n) for score in scores)

def test_no_real_scoring_claim_or_credit():
    j = json.loads(E.read_text())
    assert j["deduction"]["rounded_score_lattice_identifies_unique_denominator"] is False
    assert j["deduction"]["score_lattice_only_route_can_close_route_a_denominator_blocker"] is False
    assert j["strong_hypothesis_granted_only_for_falsification"]["hypothesis_claimed_true_of_real_cursorbench"] is False
    assert j["accounting"]["terminal_credit_delta"] == 0

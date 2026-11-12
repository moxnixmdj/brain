"""The ruler must reject every known instrument defect before it judges a learner.

Pins the pre-registration itself, plus the properties that make the adjudicator a
measurement instrument rather than a status string: fail closed, mandatory cache
and random arms, separate success accounting, and no inferred verdicts for claims
that were not measured.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools.learning_claim_adjudicator_v1 import (  # noqa: E402
    PREREGISTRATION,
    Arm,
    Experiment,
    _arm,
    _exp,
    adjudicate,
    calibration_controls,
    preflight,
)


def _good_arms() -> dict[str, Arm]:
    n = 8
    return {
        "cold": _arm([10.0] * n),
        "warm": _arm([5.0] * n),
        "cache_only": _arm([10.0] * n),
        "random": _arm([12.0] * n),
    }


def test_preregistration_is_fixed_and_stopping_rule_exists() -> None:
    t = PREREGISTRATION["thresholds"]
    assert t["min_held_out_tasks"] == 5
    assert t["min_mean_cost_ratio_warm_vs_cold"] == 1.5
    assert t["min_paired_win_fraction"] == 0.8
    assert t["min_incremental_ratio_warm_vs_cache"] == 1.5
    assert t["max_cost_outlier_multiple"] == 100.0
    assert "No threshold" in PREREGISTRATION["stopping_rule"]
    assert PREREGISTRATION["thresholds_fixed_before_any_future_real_run"] is True
    assert PREREGISTRATION["independent_timestamp_or_signature"] is False


def test_all_calibration_controls_pass() -> None:
    controls = calibration_controls()
    assert len(controls) == 9
    for name, result in controls.items():
        assert result["calibrated"], (name, result)


def test_real_compounding_is_accepted() -> None:
    out = adjudicate(_exp(_good_arms()))
    assert out["verdict"] == "COMPOUNDING"
    assert out["claims"][0]["status"] == "PASS"


def test_pure_cache_is_not_compounding() -> None:
    arms = _good_arms()
    arms["warm"] = _arm([10.0] * 8)
    out = adjudicate(_exp(arms))
    assert out["verdict"] == "NO_COMPOUNDING"
    assert any("MEAN_RATIO_TOO_SMALL" in r for r in out["claims"][0]["reasons"])


def test_cache_only_winning_blocks_the_claim_even_when_warm_is_fast() -> None:
    arms = _good_arms()
    arms["cache_only"] = _arm([5.0] * 8)
    out = adjudicate(_exp(arms))
    assert out["verdict"] == "NO_COMPOUNDING"
    assert any("CACHE_ONLY_ARM_ALSO_WINS" in r for r in out["claims"][0]["reasons"])


def test_cheaper_but_wronger_is_rejected() -> None:
    arms = _good_arms()
    arms["warm"] = _arm([1.0] * 8, [False] * 8)
    out = adjudicate(_exp(arms))
    assert out["verdict"] == "NO_COMPOUNDING"
    assert any("CHEAPER_BUT_WRONGER" in r for r in out["claims"][0]["reasons"])


def test_cache_control_must_not_explain_the_warm_gain() -> None:
    arms = _good_arms()
    arms["cache_only"] = _arm([6.7] * 8)
    out = adjudicate(_exp(arms))
    assert out["verdict"] == "NO_COMPOUNDING"
    assert any("WARM_NOT_INCREMENTALLY_BETTER_THAN_CACHE" in r
               for r in out["claims"][0]["reasons"])


def test_random_arm_is_mandatory_and_blocks_a_coin_flip() -> None:
    arms = _good_arms()
    del arms["random"]
    assert "MISSING_ARM:random" in preflight(_exp(arms))
    arms = _good_arms()
    arms["warm"] = _arm([10.0, 2.0] * 4)
    arms["random"] = _arm([6.0] * 8)
    out = adjudicate(_exp(arms))
    assert out["verdict"] == "NO_COMPOUNDING"
    assert any("DOES_NOT_BEAT_RANDOM_ARM" in r for r in out["claims"][0]["reasons"])
    arms = _good_arms()
    arms["random"] = _arm([12.0] * 8, [True] * 8)
    arms["warm"] = _arm([5.0] * 8, [True, True, True, True, True, True, False, False])
    out = adjudicate(_exp(arms))
    assert any("RANDOM_ARM_HAS_MORE_SUCCESSES" in r
               for r in out["claims"][0]["reasons"])


def test_backward_transfer_regression_is_detected() -> None:
    arms = _good_arms()
    out = adjudicate(_exp(arms, source_kind_costs_before=(4.0, 4.0),
                          source_kind_costs_after=(9.0, 9.0)))
    assert any("BACKWARD_TRANSFER_REGRESSION" in r
               for r in out["claims"][0]["reasons"])


def test_instrument_defects_fail_closed_without_scoring_claims() -> None:
    defects = [
        dict(held_out_kind="kind_A"),
        dict(verifier_author="producer"),
        dict(held_out_scorer_hash="d" * 64),
        dict(arms={**_good_arms(), "warm": _arm([5.0] * 8, task_ids=["wrong"] * 8)}),
        dict(arms={k: v for k, v in _good_arms().items() if k != "cache_only"}),
        dict(arms={**_good_arms(), "warm": _arm([1.0] * 7 + [10.0 ** 6])}),
    ]
    for override in defects:
        arms = override.pop("arms", None) or _good_arms()
        out = adjudicate(_exp(arms, **override))
        assert out["verdict"] == "INSTRUMENT_INVALID", override
        assert "claims" not in out
        assert out["preflight_errors"]
        if override.get("held_out_scorer_hash") == "d" * 64:
            assert "SCORER_NOT_HELD_OUT" in out["preflight_errors"]


def test_unmeasured_claims_are_never_inferred() -> None:
    out = adjudicate(_exp(_good_arms()))
    statuses = {c["claim_id"]: c["status"] for c in out["claims"]}
    assert statuses["C1_cross_kind_compounding"] == "PASS"
    for key in ("C2_one_shot_new_kind", "C3_self_authored_structural_test",
                "C4_interface_evolution", "C5_verifier_independent_success"):
        assert statuses[key] == "NOT_MEASURED", (key, statuses)


def test_one_shot_claim_with_extra_interactions_is_refused() -> None:
    out = adjudicate(_exp(_good_arms(), one_shot_new_kind={
        "held_out_success": 1.0, "extra_interactions": 2}))
    c2 = [c for c in out["claims"] if c["claim_id"] == "C2_one_shot_new_kind"][0]
    assert c2["status"] == "FAIL"
    assert "extra interactions" in c2["reason"]


def test_cited_defect_documents_exist() -> None:
    for name in PREREGISTRATION["sources_of_known_instrument_defects"]:
        assert (ROOT / name).is_file(), name

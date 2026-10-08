from canonical.runtime.frontiercode_robust_score_lower_bound_v1 import evaluate


def receipt():
    return {
        "verified": True,
        "independent": True,
        "source_path": "canonical/verification/test.json",
        "source_sha": "a" * 40,
    }


def base():
    return {
        "target_score_fraction": 0.5464,
        "task_count": 100,
        "trials_per_task": 5,
        "groups": [],
    }


def group(gid, multiplicity, blocker=True, lb=0.0):
    out = {
        "group_id": gid,
        "multiplicity": multiplicity,
        "all_blockers_pass_proved": blocker,
        "passed_rubric_weight_lower_bound": lb,
    }
    if blocker:
        out["blocker_pass_receipt"] = receipt()
    if lb > 0:
        out["passed_weight_receipt"] = receipt()
    return out


def test_public_categories_without_blocker_or_weight_proof_have_zero_lower_bound():
    p = base()
    p["groups"] = [group("UNKNOWN_PUBLIC_TAXONOMY", 500, blocker=False, lb=0.0)]
    out = evaluate(p)
    assert out["pass"] is True
    assert out["robust_score_lower_bound_fraction"] == "0"
    assert out["target_met_by_robust_lower_bound"] is False


def test_proved_blockers_without_positive_weight_bound_still_have_zero_lower_bound():
    p = base()
    p["groups"] = [group("BLOCKERS_ONLY", 500, blocker=True, lb=0.0)]
    out = evaluate(p)
    assert out["pass"] is True
    assert out["robust_score_lower_bound_fraction"] == "0"


def test_full_score_on_274_of_500_is_sufficient():
    p = base()
    p["groups"] = [
        group("FULL", 274, blocker=True, lb=1.0),
        group("UNKNOWN", 226, blocker=False, lb=0.0),
    ]
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["robust_score_lower_bound_fraction"] == "0.548"
    assert out["target_met_by_robust_lower_bound"] is True


def test_full_score_on_273_of_500_is_not_sufficient():
    p = base()
    p["groups"] = [
        group("FULL", 273, blocker=True, lb=1.0),
        group("UNKNOWN", 227, blocker=False, lb=0.0),
    ]
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["robust_score_lower_bound_fraction"] == "0.546"
    assert out["target_met_by_robust_lower_bound"] is False


def test_uniform_05464_lower_bound_on_all_cells_meets_target_exactly():
    p = base()
    p["groups"] = [group("ALL", 500, blocker=True, lb=0.5464)]
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["robust_score_lower_bound_fraction"] == "0.5464"
    assert out["target_met_by_robust_lower_bound"] is True


def test_positive_weight_without_independent_receipt_fails_closed():
    p = base()
    g = group("BAD", 500, blocker=True, lb=0.8)
    del g["passed_weight_receipt"]
    p["groups"] = [g]
    out = evaluate(p)
    assert out["pass"] is False
    assert any("PASSED_WEIGHT_RECEIPT_NOT_OBJECT" in x for x in out["errors"])


def test_blocker_pass_without_receipt_fails_closed():
    p = base()
    g = group("BAD", 500, blocker=True, lb=0.8)
    del g["blocker_pass_receipt"]
    p["groups"] = [g]
    out = evaluate(p)
    assert out["pass"] is False
    assert any("BLOCKER_PASS_RECEIPT_NOT_OBJECT" in x for x in out["errors"])


def test_multiplicity_must_equal_100_times_5():
    p = base()
    p["groups"] = [group("SHORT", 499, blocker=True, lb=1.0)]
    out = evaluate(p)
    assert out["pass"] is False
    assert any("GROUP_MULTIPLICITY_SUM_MISMATCH" in x for x in out["errors"])


def test_weight_lower_bound_out_of_range_fails_closed():
    p = base()
    p["groups"] = [group("BAD", 500, blocker=True, lb=1.01)]
    out = evaluate(p)
    assert out["pass"] is False
    assert any("PASSED_WEIGHT_LB_OUT_OF_RANGE" in x for x in out["errors"])


def test_duplicate_group_ids_fail_closed():
    p = base()
    p["groups"] = [
        group("DUP", 250, blocker=True, lb=1.0),
        group("DUP", 250, blocker=True, lb=1.0),
    ]
    out = evaluate(p)
    assert out["pass"] is False
    assert any("GROUP_ID_DUPLICATE" in x for x in out["errors"])

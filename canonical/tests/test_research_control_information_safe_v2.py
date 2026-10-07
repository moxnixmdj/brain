from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as v1
from canonical.runtime import research_control_information_safe_proof_v2 as v2


def _source_ids(case):
    return [row["source_id"] for row in case["source_catalog"]]


def test_v1_collision_counterexample_is_real():
    case = v1.generate_case(766, 0)
    ids = _source_ids(case)
    assert len(ids) != len(set(ids))
    assert ids.count("S-R2-40168") == 2

    out = v1.run_episode(case, candidate.next_action)
    assert out["pass"] is False, out
    assert out["reason"] == "ACTION_BUDGET_EXHAUSTED", out


def test_v2_repairs_exact_v1_counterexample_without_changing_policy():
    case = v2.generate_case(766, 0)
    ids = _source_ids(case)
    assert len(ids) == len(set(ids))

    out = v2.run_episode(case, candidate.next_action)
    assert out["pass"] is True, out
    assert out["reason"] == "PASS", out


def test_v2_source_identity_is_structurally_total():
    for seed in (0, 1, 2, 17, 766, 4096, -1, -997):
        for ordinal in range(18):
            case = v2.generate_case(seed, ordinal)
            ids = _source_ids(case)
            assert len(ids) == len(set(ids)), (seed, ordinal, ids)


def test_v2_policy_regression_sweep():
    for seed in range(128):
        for ordinal in range(12):
            case = v2.generate_case(seed, ordinal)
            out = v2.run_episode(case, candidate.next_action)
            assert out["pass"] is True, (seed, ordinal, out)


def test_v2_preserves_zero_credit_boundary():
    out = v2.run_batch(766, 24, candidate.next_action)
    assert out["all_pass"] is True, out
    assert out["failed"] == 0
    assert out["terminal_authority"] is False
    assert out["capability_credit_delta"] == 0

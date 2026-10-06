from canonical.runtime.terminal_falsification_control_loop_v1 import compile_control_loop

def _base_claim(cid, lane, status="ACTIVE", cost=1, targets=None, **extra):
    claim = {
        "id": cid,
        "lane": lane,
        "status": status,
        "cost_units": cost,
        "target_truth_obligations": list(targets or [cid]),
    }
    claim.update(extra)
    return claim

def test_falsified_route_is_dead_and_successor_is_schedulable():
    state = {
        "known_open_truth_obligations": 1,
        "claims": [
            _base_claim("OLD", "UNIVERSE_AUTHORITY", "FALSIFIED"),
            _base_claim("NEW", "UNIVERSE_AUTHORITY", "ACTIVE", successor_of="OLD"),
        ],
    }
    out = compile_control_loop(state)
    assert "OLD" in out.dead_claim_ids
    assert out.unrepaired_dead_claim_ids == ()
    assert out.ordered_claim_ids == ("NEW",)
    assert out.proof_credit_delta == 0

def test_nonexhaustive_survival_never_gets_proof_credit():
    state = {
        "known_open_truth_obligations": 1,
        "claims": [_base_claim("U", "UNIVERSE_AUTHORITY", "SURVIVED_NONEXHAUSTIVE")],
    }
    out = compile_control_loop(state)
    assert out.verdicts[0]["proof_credit"] == 0
    assert out.universe_complete is False
    assert out.terminal_ready is False

def test_proved_label_without_receipts_is_zero_credit():
    state = {
        "known_open_truth_obligations": 0,
        "claims": [_base_claim("U", "UNIVERSE_AUTHORITY", "PROVED")],
    }
    out = compile_control_loop(state)
    assert out.universe_complete is False
    assert out.terminal_ready is False

def test_invalid_receipt_is_zero_credit():
    state = {
        "known_open_truth_obligations": 0,
        "claims": [
            _base_claim(
                "U",
                "UNIVERSE_AUTHORITY",
                "PROVED",
                proof_receipts=[{"path":"x","git_blob_sha":"not-a-sha"}],
            )
        ],
    }
    out = compile_control_loop(state)
    assert out.universe_complete is False
    assert out.terminal_ready is False

def test_content_addressed_proved_universe_can_close_authority_lane():
    state = {
        "known_open_truth_obligations": 0,
        "claims": [
            _base_claim(
                "U",
                "UNIVERSE_AUTHORITY",
                "PROVED",
                proof_receipts=[{"path":"x","git_blob_sha":"0"*40}],
            )
        ],
    }
    out = compile_control_loop(state)
    assert out.universe_complete is True
    assert out.terminal_ready is True

def test_all_live_universe_claims_must_be_proved():
    state = {
        "known_open_truth_obligations": 1,
        "claims": [
            _base_claim(
                "COVERAGE",
                "UNIVERSE_AUTHORITY",
                "PROVED",
                proof_receipts=[{"path":"coverage","git_blob_sha":"2"*40}],
            ),
            _base_claim("DOMINANCE", "UNIVERSE_AUTHORITY", "ACTIVE"),
        ],
    }
    out = compile_control_loop(state)
    assert out.universe_complete is False
    assert out.terminal_ready is False
    assert out.ordered_claim_ids == ("DOMINANCE",)

def test_universe_lane_has_strict_precedence():
    state = {
        "known_open_truth_obligations": 2,
        "claims": [
            _base_claim("U", "UNIVERSE_AUTHORITY", "ACTIVE", cost=100, targets=["U"]),
            _base_claim("P", "PERFORMANCE_WITNESS", "ACTIVE", cost=1, targets=["a"], target_truth_obligation_count=100),
        ],
    }
    out = compile_control_loop(state)
    assert out.ordered_claim_ids[0] == "U"

def test_nonuniverse_lanes_rank_by_reachability_per_cost():
    state = {
        "known_open_truth_obligations": 3,
        "claims": [
            _base_claim("U", "UNIVERSE_AUTHORITY", "ACTIVE"),
            _base_claim("E", "EFFECT_CLOSURE", "ACTIVE", cost=4, targets=["e"], target_truth_obligation_count=4),
            _base_claim("P", "PERFORMANCE_WITNESS", "ACTIVE", cost=2, targets=["p"], target_truth_obligation_count=10),
        ],
    }
    out = compile_control_loop(state)
    assert out.ordered_claim_ids == ("U", "P", "E")

def test_dependency_on_falsified_claim_blocks_without_successor():
    state = {
        "known_open_truth_obligations": 2,
        "claims": [
            _base_claim("U", "UNIVERSE_AUTHORITY", "ACTIVE"),
            _base_claim("OLD_EFFECT", "EFFECT_CLOSURE", "FALSIFIED"),
            _base_claim("CHILD", "OWNERSHIP", "ACTIVE", depends_on=["OLD_EFFECT"]),
        ],
    }
    out = compile_control_loop(state)
    assert "CHILD" in out.blocked_claim_ids
    assert "OLD_EFFECT" in out.unrepaired_dead_claim_ids
    assert "CHILD" not in out.ordered_claim_ids

def test_live_successor_unblocks_dependency_without_resurrecting_old_route():
    state = {
        "known_open_truth_obligations": 3,
        "claims": [
            _base_claim("U", "UNIVERSE_AUTHORITY", "ACTIVE"),
            _base_claim("OLD_EFFECT", "EFFECT_CLOSURE", "FALSIFIED"),
            _base_claim("NEW_EFFECT", "EFFECT_CLOSURE", "ACTIVE", successor_of="OLD_EFFECT"),
            _base_claim("CHILD", "OWNERSHIP", "ACTIVE", depends_on=["OLD_EFFECT"]),
        ],
    }
    out = compile_control_loop(state)
    assert "OLD_EFFECT" in out.dead_claim_ids
    assert "OLD_EFFECT" not in out.unrepaired_dead_claim_ids
    assert "CHILD" not in out.blocked_claim_ids
    assert "NEW_EFFECT" in out.ordered_claim_ids
    assert "CHILD" in out.ordered_claim_ids


def test_transitive_live_successor_repairs_entire_lineage():
    state = {
        "known_open_truth_obligations": 1,
        "claims": [
            _base_claim("OLD", "UNIVERSE_AUTHORITY", "FALSIFIED"),
            _base_claim("MID", "UNIVERSE_AUTHORITY", "FALSIFIED", successor_of="OLD"),
            _base_claim("NEW", "UNIVERSE_AUTHORITY", "ACTIVE", successor_of="MID"),
        ],
    }
    out = compile_control_loop(state)
    assert "OLD" in out.dead_claim_ids
    assert "MID" in out.dead_claim_ids
    assert out.unrepaired_dead_claim_ids == ()
    assert out.ordered_claim_ids == ("NEW",)

def test_dependency_on_ancestor_unblocks_through_transitive_successor():
    state = {
        "known_open_truth_obligations": 2,
        "claims": [
            _base_claim("U", "UNIVERSE_AUTHORITY", "ACTIVE"),
            _base_claim("OLD_EFFECT", "EFFECT_CLOSURE", "FALSIFIED"),
            _base_claim("MID_EFFECT", "EFFECT_CLOSURE", "FALSIFIED", successor_of="OLD_EFFECT"),
            _base_claim("NEW_EFFECT", "EFFECT_CLOSURE", "ACTIVE", successor_of="MID_EFFECT"),
            _base_claim("CHILD", "OWNERSHIP", "ACTIVE", depends_on=["OLD_EFFECT"]),
        ],
    }
    out = compile_control_loop(state)
    assert "OLD_EFFECT" not in out.unrepaired_dead_claim_ids
    assert "MID_EFFECT" not in out.unrepaired_dead_claim_ids
    assert "CHILD" not in out.blocked_claim_ids
    assert "NEW_EFFECT" in out.ordered_claim_ids
    assert "CHILD" in out.ordered_claim_ids

def test_unrepaired_dead_claim_prevents_terminal_readiness():
    state = {
        "known_open_truth_obligations": 0,
        "claims": [
            _base_claim(
                "U",
                "UNIVERSE_AUTHORITY",
                "PROVED",
                proof_receipts=[{"path":"u","git_blob_sha":"1"*40}],
            ),
            _base_claim("BROKEN", "EFFECT_CLOSURE", "FALSIFIED"),
        ],
    }
    out = compile_control_loop(state)
    assert out.universe_complete is True
    assert "BROKEN" in out.unrepaired_dead_claim_ids
    assert out.terminal_ready is False

def run_all():
    tests = [
        test_falsified_route_is_dead_and_successor_is_schedulable,
        test_nonexhaustive_survival_never_gets_proof_credit,
        test_proved_label_without_receipts_is_zero_credit,
        test_invalid_receipt_is_zero_credit,
        test_content_addressed_proved_universe_can_close_authority_lane,
        test_all_live_universe_claims_must_be_proved,
        test_universe_lane_has_strict_precedence,
        test_nonuniverse_lanes_rank_by_reachability_per_cost,
        test_dependency_on_falsified_claim_blocks_without_successor,
        test_live_successor_unblocks_dependency_without_resurrecting_old_route,
        test_transitive_live_successor_repairs_entire_lineage,
        test_dependency_on_ancestor_unblocks_through_transitive_successor,
        test_unrepaired_dead_claim_prevents_terminal_readiness,
    ]
    for test in tests:
        test()
    return len(tests)

if __name__ == "__main__":
    print(f"PASS {run_all()}/13")

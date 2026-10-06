from hashlib import sha256
from canonical.runtime.terminal_falsification_control_loop_v2 import compile_control_loop

SHA = "0" * 40
BIND = {"path": "canonical/governance/FRONTIER.json", "git_blob_sha": SHA}

def _fingerprint(inputs):
    rows = sorted(f"{x['path']}:{x['git_blob_sha']}" for x in inputs)
    return sha256("\n".join(rows).encode("utf-8")).hexdigest()

def _state(claims, open_count=1):
    inputs = [dict(BIND)]
    return {
        "authoritative_inputs": inputs,
        "frontier_fingerprint": _fingerprint(inputs),
        "known_open_truth_obligations": open_count,
        "claims": claims,
    }

def _claim(cid, lane, status="ACTIVE", cost=1, targets=None, **extra):
    c = {
        "id": cid,
        "lane": lane,
        "status": status,
        "cost_units": cost,
        "target_truth_obligations": list(targets or [cid]),
    }
    c.update(extra)
    return c

def _stable(claim):
    claim["stable_under_universe_expansion"] = True
    claim["expansion_stability_receipt"] = {
        "path": "canonical/verification/STABILITY.json",
        "git_blob_sha": "1" * 40,
    }
    return claim

def _aggregate(cid, lane, members, status="ACTIVE", cost=1, **extra):
    return _claim(
        cid,
        lane,
        status=status,
        cost=cost,
        targets=[cid],
        target_truth_obligation_count=len(members),
        target_expansion={
            "aggregate_id": cid,
            "members": list(members),
            "receipt": {
                "path": "canonical/governance/TOURNAMENT.json",
                "git_blob_sha": "2" * 40,
            },
        },
        **extra,
    )

def test_rejects_inflated_unbound_leverage_count():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _claim("P", "PERFORMANCE_WITNESS", cost=1, targets=["P"], target_truth_obligation_count=100),
    ])
    try:
        compile_control_loop(s)
    except ValueError as e:
        assert "target_expansion" in str(e)
    else:
        raise AssertionError("inflated unbound count accepted")

def test_accepts_exact_content_addressed_aggregate_expansion():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _stable(_aggregate("P", "PERFORMANCE_WITNESS", ["a", "b", "c"], cost=1)),
    ], open_count=4)
    out = compile_control_loop(s)
    pv = [v for v in out.verdicts if v["claim_id"] == "P"][0]
    assert pv["resolved_target_count"] == 3
    assert out.ordered_claim_ids == ("U", "P")

def test_rejects_duplicate_aggregate_members():
    c = _aggregate("P", "PERFORMANCE_WITNESS", ["a", "b", "c"])
    c["target_expansion"]["members"] = ["a", "a", "c"]
    s = _state([_claim("U", "UNIVERSE_AUTHORITY"), c])
    try:
        compile_control_loop(s)
    except ValueError as e:
        assert "unique" in str(e)
    else:
        raise AssertionError("duplicate expansion accepted")

def test_rejects_bad_aggregate_receipt():
    c = _aggregate("P", "PERFORMANCE_WITNESS", ["a", "b"])
    c["target_expansion"]["receipt"]["git_blob_sha"] = "bad"
    s = _state([_claim("U", "UNIVERSE_AUTHORITY"), c])
    try:
        compile_control_loop(s)
    except ValueError as e:
        assert "content-addressed" in str(e)
    else:
        raise AssertionError("bad expansion receipt accepted")

def test_rejects_frontier_fingerprint_drift():
    s = _state([_claim("U", "UNIVERSE_AUTHORITY")])
    s["frontier_fingerprint"] = "f" * 64
    try:
        compile_control_loop(s)
    except ValueError as e:
        assert "frontier_fingerprint mismatch" in str(e)
    else:
        raise AssertionError("stale frontier fingerprint accepted")

def test_universe_open_blocks_unstable_nonuniverse_work():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _claim("E", "EFFECT_CLOSURE"),
    ], open_count=2)
    out = compile_control_loop(s)
    assert "E" in out.blocked_claim_ids
    assert out.ordered_claim_ids == ("U",)

def test_universe_open_allows_only_proof_carrying_stable_work():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _stable(_claim("E", "EFFECT_CLOSURE", targets=["e"])),
    ], open_count=2)
    out = compile_control_loop(s)
    assert "E" not in out.blocked_claim_ids
    assert out.ordered_claim_ids == ("U", "E")

def test_stability_boolean_without_receipt_fails_closed():
    c = _claim("E", "EFFECT_CLOSURE")
    c["stable_under_universe_expansion"] = True
    s = _state([_claim("U", "UNIVERSE_AUTHORITY"), c], open_count=2)
    try:
        compile_control_loop(s)
    except ValueError as e:
        assert "stability requires a content-addressed receipt" in str(e)
    else:
        raise AssertionError("assertion-only stability accepted")

def test_strict_dependency_mode_requires_proved_receipt():
    dep = _claim("U", "UNIVERSE_AUTHORITY")
    child = _stable(_claim(
        "P",
        "PERFORMANCE_WITNESS",
        depends_on=["U"],
        dependency_mode="REQUIRE_PROVED",
    ))
    s = _state([dep, child], open_count=2)
    out = compile_control_loop(s)
    assert "P" in out.blocked_claim_ids

def test_strict_dependency_mode_unblocks_on_proved_receipt():
    dep = _claim(
        "U",
        "UNIVERSE_AUTHORITY",
        status="PROVED",
        proof_receipts=[{"path": "canonical/verification/U.json", "git_blob_sha": "3" * 40}],
    )
    child = _claim(
        "P",
        "PERFORMANCE_WITNESS",
        depends_on=["U"],
        dependency_mode="REQUIRE_PROVED",
    )
    s = _state([dep, child], open_count=1)
    out = compile_control_loop(s)
    assert out.universe_complete is True
    assert "P" not in out.blocked_claim_ids
    assert out.ordered_claim_ids == ("P",)

def test_falsified_route_requires_live_successor():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _claim("OLD", "EFFECT_CLOSURE", status="FALSIFIED"),
    ], open_count=2)
    out = compile_control_loop(s)
    assert "OLD" in out.unrepaired_dead_claim_ids
    assert out.terminal_ready is False

def test_survival_is_zero_credit():
    u = _claim("U", "UNIVERSE_AUTHORITY", status="SURVIVED_EXHAUSTIVE")
    s = _state([u], open_count=1)
    out = compile_control_loop(s)
    assert out.universe_complete is False
    assert out.verdicts[0]["proof_credit"] == 0

def test_proved_universe_with_receipt_can_close_authority_lane():
    u = _claim(
        "U",
        "UNIVERSE_AUTHORITY",
        status="PROVED",
        proof_receipts=[{"path": "canonical/verification/U.json", "git_blob_sha": "4" * 40}],
    )
    s = _state([u], open_count=0)
    out = compile_control_loop(s)
    assert out.universe_complete is True
    assert out.terminal_ready is True

def test_aggregate_leverage_ranking_uses_resolved_members_not_declared_metadata():
    s = _state([
        _claim("U", "UNIVERSE_AUTHORITY"),
        _stable(_aggregate("P", "PERFORMANCE_WITNESS", ["a", "b", "c", "d"], cost=2)),
        _stable(_aggregate("E", "EFFECT_CLOSURE", ["e1", "e2", "e3"], cost=1)),
    ], open_count=8)
    out = compile_control_loop(s)
    assert out.ordered_claim_ids == ("U", "E", "P")

def run_all():
    tests = [
        test_rejects_inflated_unbound_leverage_count,
        test_accepts_exact_content_addressed_aggregate_expansion,
        test_rejects_duplicate_aggregate_members,
        test_rejects_bad_aggregate_receipt,
        test_rejects_frontier_fingerprint_drift,
        test_universe_open_blocks_unstable_nonuniverse_work,
        test_universe_open_allows_only_proof_carrying_stable_work,
        test_stability_boolean_without_receipt_fails_closed,
        test_strict_dependency_mode_requires_proved_receipt,
        test_strict_dependency_mode_unblocks_on_proved_receipt,
        test_falsified_route_requires_live_successor,
        test_survival_is_zero_credit,
        test_proved_universe_with_receipt_can_close_authority_lane,
        test_aggregate_leverage_ranking_uses_resolved_members_not_declared_metadata,
    ]
    for test in tests:
        test()
    return len(tests)

if __name__ == "__main__":
    print(f"PASS {run_all()}/14")

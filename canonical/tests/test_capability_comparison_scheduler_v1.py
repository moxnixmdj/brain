from canonical.runtime.capability_comparison_scheduler_v1 import (
    CapabilityComparisonError,
    compile_program,
    select_exact_portfolio,
)


def registry():
    rows = [
        ("P1", "CODING"),
        ("P2", "CODING"),
        ("P3", "FINANCE"),
    ]
    return {"predicates": [{"id": i, "family": f} for i, f in rows]}


def quotient():
    return {"independent_open_obligations": ["Q1", "Q2", "Q3"]}


def program():
    return {
        "audit_obligations": [
            {"audit_id":"A1","quotient_obligation_id":"Q1","predicate_ids":["P1"],"capability_families":["CODING"]},
            {"audit_id":"A2","quotient_obligation_id":"Q2","predicate_ids":["P2"],"capability_families":["CODING"]},
            {"audit_id":"A3","quotient_obligation_id":"Q3","predicate_ids":["P3"],"capability_families":["FINANCE"]},
        ] + [
            {"audit_id":f"X{i}","quotient_obligation_id":f"XQ{i}","predicate_ids":[f"XP{i}"],"capability_families":[f"XF{i}"]}
            for i in range(10)
        ]
    }


def expanded_registry_and_quotient():
    p = program()
    r = registry()
    q = quotient()
    for row in p["audit_obligations"][3:]:
        r["predicates"].append({"id":row["predicate_ids"][0],"family":row["capability_families"][0]})
        q["independent_open_obligations"].append(row["quotient_obligation_id"])
    return p, r, q


def test_compile_deduplicates_audits_into_capability_families():
    p, r, q = expanded_registry_and_quotient()
    out = compile_program(p, r, q)
    assert out["audit_obligation_count"] == 13
    assert out["capability_family_count"] == 12
    assert out["capability_clusters"][0]["capability_family"] == "CODING"
    assert out["capability_clusters"][0]["audit_count"] == 2
    assert out["automatic_score_to_capability_transfer"] is False
    assert out["automatic_capability_to_score_transfer"] is False


def test_compile_rejects_family_mismatch():
    p, r, q = expanded_registry_and_quotient()
    p["audit_obligations"][0]["capability_families"] = ["WRONG"]
    try:
        compile_program(p, r, q)
    except CapabilityComparisonError as e:
        assert "FAMILY_BINDING_MISMATCH" in str(e)
    else:
        raise AssertionError("must fail closed")


def test_compile_requires_exact_current_quotient_cover():
    p, r, q = expanded_registry_and_quotient()
    q["independent_open_obligations"].append("UNBOUND")
    try:
        compile_program(p, r, q)
    except CapabilityComparisonError as e:
        assert "QUOTIENT_COVER_NOT_EXACT" in str(e)
    else:
        raise AssertionError("must fail closed")


def witness(wid, caps, audits, wall, ext=0, compute=0, spend=0, risk=0):
    return {
        "witness_id": wid,
        "closes_capability_families": caps,
        "explicitly_entails_audit_ids": audits,
        "independently_verified": True,
        "scope_complete": True,
        "brain_owned": True,
        "external_general_purpose_runtime_cognition": 0,
        "wall_clock_units": wall,
        "external_dependency_units": ext,
        "compute_units": compute,
        "incremental_spend_usd": spend,
        "evidence_risk_units": risk,
    }


def test_exact_portfolio_prefers_one_shared_witness_over_two_slower_witnesses():
    candidates = [
        witness("coding-shared", ["CODING"], ["A1","A2"], 2),
        witness("a1-only", ["CODING"], ["A1"], 2),
        witness("a2-only", ["CODING"], ["A2"], 2),
    ]
    out = select_exact_portfolio(
        candidates,
        required_capability_families=["CODING"],
        required_audit_ids=["A1","A2"],
    )
    assert out["forced_complete"] is True
    assert out["selected_witness_ids"] == ["coding-shared"]


def test_exact_portfolio_minimizes_wall_clock_before_compute():
    candidates = [
        witness("fast-heavy", ["CODING"], ["A1"], 1, compute=100),
        witness("slow-light", ["CODING"], ["A1"], 2, compute=0),
    ]
    out = select_exact_portfolio(
        candidates,
        required_capability_families=["CODING"],
        required_audit_ids=["A1"],
    )
    assert out["selected_witness_ids"] == ["fast-heavy"]


def test_unknown_cost_fails_closed():
    bad = witness("bad", ["CODING"], ["A1"], 1)
    del bad["wall_clock_units"]
    try:
        select_exact_portfolio(
            [bad],
            required_capability_families=["CODING"],
            required_audit_ids=["A1"],
        )
    except CapabilityComparisonError as e:
        assert "WALL_CLOCK_REQUIRED" in str(e)
    else:
        raise AssertionError("must fail closed")


def test_external_runtime_cognition_is_ineligible():
    bad = witness("teacher", ["CODING"], ["A1"], 1)
    bad["external_general_purpose_runtime_cognition"] = 1
    try:
        select_exact_portfolio(
            [bad],
            required_capability_families=["CODING"],
            required_audit_ids=["A1"],
        )
    except CapabilityComparisonError as e:
        assert "EXTERNAL_RUNTIME_COGNITION_MUST_BE_ZERO" in str(e)
    else:
        raise AssertionError("must fail closed")


def test_capability_only_witness_does_not_fake_benchmark_receipt():
    candidates = [witness("capability-only", ["CODING"], [], 1)]
    out = select_exact_portfolio(
        candidates,
        required_capability_families=["CODING"],
        required_audit_ids=["A1"],
    )
    assert out["forced_complete"] is False
    assert out["missing_audit_ids"] == ["A1"]

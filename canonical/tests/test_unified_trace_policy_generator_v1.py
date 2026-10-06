from canonical.runtime.unified_trace_policy_generator_v1 import (
    FiniteTracePolicy,
    Observation,
    PolicyStep,
    TracePolicyError,
    compile_finite_behavior,
    representation_demo,
)


def expect_error(fn, text):
    try:
        fn()
    except TracePolicyError as exc:
        assert str(exc) == text
    else:
        raise AssertionError("expected TracePolicyError")


def test_multimodal_rows_share_one_policy_interface():
    out = representation_demo()
    assert out["all_exact"] is True
    assert set(out["modalities"]) == {"image/png", "text/plain", "ui/state"}
    assert out["terminal_credit_delta"] == 0


def test_modality_is_bound_without_changing_policy_api():
    image = Observation("image/png", b"x")
    text = Observation("text/plain", b"x")
    assert FiniteTracePolicy.key("task", b"s", image) != FiniteTracePolicy.key(
        "task", b"s", text
    )


def test_state_is_load_bearing():
    obs = Observation("text/plain", b"x")
    rows = [
        ("task", b"s0", obs, PolicyStep("answer", b"a", b"s1")),
        ("task", b"s1", obs, PolicyStep("answer", b"b", b"s2")),
    ]
    p = compile_finite_behavior(rows)
    assert p.step("task", b"s0", obs).next_payload == b"a"
    assert p.step("task", b"s1", obs).next_payload == b"b"


def test_unbound_policy_state_fails_closed():
    obs = Observation("text/plain", b"x")
    p = compile_finite_behavior(
        [("task", b"s0", obs, PolicyStep("answer", b"a", b"s1"))]
    )
    expect_error(
        lambda: p.step("task", b"other", obs),
        "UNBOUND_POLICY_STATE",
    )


def test_nonfunctional_behavior_rejected():
    obs = Observation("image/png", b"x")
    expect_error(
        lambda: compile_finite_behavior(
            [
                ("task", b"s", obs, PolicyStep("answer", b"a", b"s1")),
                ("task", b"s", obs, PolicyStep("answer", b"b", b"s1")),
            ]
        ),
        "NONFUNCTIONAL_BEHAVIOR",
    )

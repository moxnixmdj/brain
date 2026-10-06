from canonical.runtime.v7_layered_equal_or_better_countermodel_v1 import (
    compile_countermodel,
    construct_countermodel,
    mixed_target_relative_resource_dominance,
    v7_capability_target,
)


def test_equal_capability_owned_zero_spend_can_pass_v7_with_more_compute():
    assert v7_capability_target(
        brain_success=1.0,
        opus_success=1.0,
        brain_owned=True,
        donor_independent=True,
        spend_usd=0.0,
    ) is True
    assert mixed_target_relative_resource_dominance(
        brain_success=1.0,
        opus_success=1.0,
        brain_compute=2.0,
        opus_compute=1.0,
    ) is False


def test_countermodel_is_constructive():
    out = construct_countermodel()
    assert out["v7_capability_target_true"] is True
    assert out["mixed_resource_dominance_false"] is True
    assert out["countermodel_valid"] is True


def test_compiler_grants_truth_repair_only():
    out = compile_countermodel()
    assert out["status"].startswith("PASS__")
    assert out["classification"] == "TRUTH_REPAIR"
    assert out["terminal_credit"] is False


def test_ownership_is_not_optional():
    assert v7_capability_target(
        brain_success=1.0,
        opus_success=1.0,
        brain_owned=False,
        donor_independent=True,
        spend_usd=0.0,
    ) is False


def test_zero_spend_is_absolute_not_relative_to_opus():
    assert v7_capability_target(
        brain_success=1.0,
        opus_success=1.0,
        brain_owned=True,
        donor_independent=True,
        spend_usd=0.0,
    ) is True
    assert v7_capability_target(
        brain_success=1.0,
        opus_success=1.0,
        brain_owned=True,
        donor_independent=True,
        spend_usd=1.0,
    ) is False

from __future__ import annotations


def v7_capability_target(
    *,
    brain_success: float,
    opus_success: float,
    brain_owned: bool,
    donor_independent: bool,
    spend_usd: float,
) -> bool:
    return (
        brain_success >= opus_success
        and brain_owned
        and donor_independent
        and spend_usd == 0.0
    )


def mixed_target_relative_resource_dominance(
    *,
    brain_success: float,
    opus_success: float,
    brain_compute: float,
    opus_compute: float,
) -> bool:
    return (
        brain_success >= opus_success
        and brain_compute <= opus_compute
    )


def construct_countermodel() -> dict[str, object]:
    opus_success = 1.0
    brain_success = 1.0
    opus_compute = 1.0
    brain_compute = 2.0

    terminal = v7_capability_target(
        brain_success=brain_success,
        opus_success=opus_success,
        brain_owned=True,
        donor_independent=True,
        spend_usd=0.0,
    )
    mixed = mixed_target_relative_resource_dominance(
        brain_success=brain_success,
        opus_success=opus_success,
        brain_compute=brain_compute,
        opus_compute=opus_compute,
    )
    return {
        "v7_capability_target_true": terminal,
        "mixed_resource_dominance_false": not mixed,
        "countermodel_valid": terminal and not mixed,
        "brain_compute_units": brain_compute,
        "opus_compute_units": opus_compute,
    }


def compile_countermodel() -> dict[str, object]:
    out = construct_countermodel()
    if out["countermodel_valid"] is not True:
        return {
            "status": "FAIL_CLOSED",
            "error": "V7_LAYERING_COUNTERMODEL_NOT_CONSTRUCTED",
        }
    return {
        "status": "PASS__V7_CAPABILITY_PARITY_AND_ROUTE_OPTIMIZATION_MUST_BE_LAYERED",
        "classification": "TRUTH_REPAIR",
        "terminal_credit": False,
        "minimum_repair": (
            "CAPABILITY_DISTRIBUTIONAL_NONINFERIORITY"
            "+ABSOLUTE_OWNERSHIP_FEASIBILITY"
            "+POST_GATE_ROUTE_OPTIMIZATION"
        ),
    }

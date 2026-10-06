from __future__ import annotations


def composition_countermodel() -> dict[str, object]:
    opus_internal = 1
    brain_internal = 0

    isolated_brain_noninferior = brain_internal >= opus_internal

    # Different downstream implementations can compensate for different internal
    # representations while preserving the same terminal behavior.
    opus_terminal = "SUCCESS" if opus_internal == 1 else "FAIL"
    brain_terminal = "SUCCESS" if brain_internal == 0 else "FAIL"

    opus_constraints = {
        "safety": True,
        "scope": True,
        "continuation": True,
        "ownership": True,
    }
    brain_constraints = dict(opus_constraints)

    composition_parity = (
        opus_terminal == brain_terminal
        and all(opus_constraints.values())
        and brain_constraints == opus_constraints
    )

    return {
        "isolated_component_brain_noninferior": isolated_brain_noninferior,
        "opus_terminal": opus_terminal,
        "brain_terminal": brain_terminal,
        "terminal_distribution_equal": opus_terminal == brain_terminal,
        "hard_constraints_equal_and_pass": (
            brain_constraints == opus_constraints
            and all(brain_constraints.values())
        ),
        "composition_parity_holds": composition_parity,
    }


def compile_necessity_falsifier() -> dict[str, object]:
    out = composition_countermodel()
    valid = (
        out["isolated_component_brain_noninferior"] is False
        and out["composition_parity_holds"] is True
        and out["terminal_distribution_equal"] is True
        and out["hard_constraints_equal_and_pass"] is True
    )
    if not valid:
        return {
            "status": "FAIL_CLOSED",
            "reason": "COUNTERMODEL_NOT_CONSTRUCTED",
        }
    return {
        "status": "PASS__STANDALONE_COMPONENT_PARITY_NOT_NECESSARY_FOR_COMPOSITION_PARITY",
        "countermodel_valid": True,
        "candidate_deleted_obligation": "COMPOSITION_COMPONENT_SCOPED_PROOFS",
        "preserve_separate_component_capability_obligations": True,
        "preserve_composition_success_and_invariant_obligations": True,
        "terminal_credit": False,
    }

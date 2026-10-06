from __future__ import annotations

from typing import Mapping, Sequence


def target_terminal(
    target: Sequence[str],
    dominates: Mapping[str, bool],
    owned: Mapping[str, bool],
) -> bool:
    return all(dominates.get(x) is True and owned.get(x) is True for x in target)


def literal_full_superset_dominance(
    trace_superset: Sequence[str],
    dominates: Mapping[str, bool],
    owned: Mapping[str, bool],
) -> bool:
    return all(dominates.get(x) is True and owned.get(x) is True for x in trace_superset)


def declared_target_certificate(
    declared_target: Sequence[str],
    dominates: Mapping[str, bool],
    owned: Mapping[str, bool],
) -> bool:
    return target_terminal(declared_target, dominates, owned)


def overreach_countermodel() -> dict[str, object]:
    trace_superset = ("a", "b")
    actual_target = ("a",)
    dominates = {"a": True, "b": False}
    owned = {"a": True, "b": True}
    terminal = target_terminal(actual_target, dominates, owned)
    full_scope = literal_full_superset_dominance(trace_superset, dominates, owned)
    return {
        "terminal_goal_true": terminal,
        "literal_full_superset_dominance": full_scope,
        "falsifies_necessity_of_full_superset_dominance": terminal and not full_scope,
    }


def underbinding_countermodel() -> dict[str, object]:
    declared = ("a",)
    dominates = {"a": True, "b": False}
    owned = {"a": True, "b": True}

    w1_actual = ("a",)
    w2_actual = ("a", "b")

    cert_w1 = declared_target_certificate(declared, dominates, owned)
    cert_w2 = declared_target_certificate(declared, dominates, owned)
    terminal_w1 = target_terminal(w1_actual, dominates, owned)
    terminal_w2 = target_terminal(w2_actual, dominates, owned)

    return {
        "declared_certificate_w1": cert_w1,
        "declared_certificate_w2": cert_w2,
        "terminal_w1": terminal_w1,
        "terminal_w2": terminal_w2,
        "same_declared_certificate_different_terminal_truth": (
            cert_w1 == cert_w2 and terminal_w1 != terminal_w2
        ),
        "proves_target_completeness_binding_is_necessary": (
            cert_w1 and cert_w2 and terminal_w1 and not terminal_w2
        ),
    }


def compile_falsification() -> dict[str, object]:
    over = overreach_countermodel()
    under = underbinding_countermodel()
    if over["falsifies_necessity_of_full_superset_dominance"] is not True:
        return {"status": "FAIL_CLOSED", "error": "OVERREACH_COUNTERMODEL_NOT_CONSTRUCTED"}
    if under["proves_target_completeness_binding_is_necessary"] is not True:
        return {"status": "FAIL_CLOSED", "error": "UNDERBINDING_COUNTERMODEL_NOT_CONSTRUCTED"}
    return {
        "status": "PASS__CURRENT_THEOREM_MUST_BE_TARGET_RELATIVE_AND_TARGET_COMPLETE",
        "literal_full_superset_reading_falsified": True,
        "target_completeness_binding_required": True,
        "terminal_credit": False,
        "classification": "TRUTH_REPAIR",
    }

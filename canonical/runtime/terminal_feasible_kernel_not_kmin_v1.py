from __future__ import annotations


def minimality_necessity_countermodel() -> dict[str, object]:
    a = {"info_units": 10, "terminal": True}
    b = {"info_units": 1000, "terminal": True}
    return {
        "a": a,
        "b": b,
        "b_is_minimal": False,
        "b_terminal": b["terminal"],
        "exact_minimality_necessary_for_terminal": False,
    }


def compile_repair() -> dict[str, object]:
    w = minimality_necessity_countermodel()
    if not w["b_terminal"] or w["b_is_minimal"]:
        return {"status": "FAIL_CLOSED"}
    return {
        "status": "PASS__KMIN_NOT_TERMINAL_NECESSITY",
        "successor": "FEASIBLE_OWNED_DOMINANCE_WITNESS",
        "kmin_role": "RESOURCE_OPTIMIZATION_OR_POST_TERMINAL_COMPRESSION",
        "terminal_credit": False,
    }

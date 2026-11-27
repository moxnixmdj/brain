from canonical.runtime.terminal_feasible_kernel_not_kmin_v1 import (
    compile_repair,
    minimality_necessity_countermodel,
)


def test_nonminimal_system_can_still_satisfy_terminal():
    out = minimality_necessity_countermodel()
    assert out["b_terminal"] is True
    assert out["b_is_minimal"] is False
    assert out["exact_minimality_necessary_for_terminal"] is False


def test_repair_selects_feasible_owned_witness():
    out = compile_repair()
    assert out["status"] == "PASS__KMIN_NOT_TERMINAL_NECESSITY"
    assert out["successor"] == "FEASIBLE_OWNED_DOMINANCE_WITNESS"
    assert out["terminal_credit"] is False

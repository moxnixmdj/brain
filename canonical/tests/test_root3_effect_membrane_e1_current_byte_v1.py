from pathlib import Path
import ast

from canonical.runtime import root3_effect_membrane_e1_current_byte_v1 as e1


def test_current_exact_bytes_pass():
    out = e1.evaluate()
    assert out["pass"] is True, out
    assert out["e1_closed_for_bound_bytes"] is True
    assert out["effect_totality_closed"] is False


def test_signature_drift_is_detectable():
    tree = ast.parse("def run_shell(step):\n    pass\n")
    node = e1._defs(tree)["run_shell"]
    assert e1._signature(node) != e1.EXPECTED_SIGNATURES["run_shell"]


def test_missing_wrapper_binding_is_detectable():
    tree = ast.parse("def install_complete_mediation(astra, monitor):\n    pass\n")
    assert e1._wrapper_bindings(tree) != e1.EXPECTED_CHANNELS

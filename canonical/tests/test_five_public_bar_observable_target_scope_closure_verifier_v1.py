from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "canonical/runtime/five_public_bar_observable_target_scope_closure_verifier_v1.py"


spec = importlib.util.spec_from_file_location("scope_verifier", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_current_main_scope_reduction_passes_fail_closed_verifier():
    result = module.verify(ROOT)
    assert result["status"] == "PASS"
    assert result["family_count"] == 5
    assert result["acceptance_credit_delta"] == 0
    assert result["fresh_reality_units_consumed"] == 0


def test_verifier_has_nontrivial_checks():
    result = module.verify(ROOT)
    assert result["check_count"] >= 20
    assert "negative_literal_target_checks" in result["checks"]

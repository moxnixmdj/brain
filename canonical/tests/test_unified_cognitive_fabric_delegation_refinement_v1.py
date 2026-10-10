from pathlib import Path
from canonical.runtime.unified_cognitive_fabric_delegation_refinement_v1 import prove

ROOT = Path(__file__).resolve().parents[2]

def test_unified_fabric_is_a_nonamplifying_delegation_membrane():
    out = prove(ROOT)
    assert out["pass"] is True, out
    assert out["delegation_refinement_verified"] is True
    assert out["no_direct_external_effect_calls"] is True
    assert out["no_authority_true_literals"] is True
    assert out["all_canonical_runtime_calls_classified"] is True
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0

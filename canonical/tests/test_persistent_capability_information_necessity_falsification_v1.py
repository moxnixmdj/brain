import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "canonical/governance/PERSISTENT_CAPABILITY_INFORMATION_NECESSITY_FALSIFICATION_20261007_V1.json"


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_terminal_objective_is_unchanged():
    d = load()
    assert d["terminal_objective"] == (
        "PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_"
        "AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"
    )


def test_separator_theorem_is_preserved():
    d = load()
    assert "NO_CLAIM_THE_ORIGINAL_SEPARATOR_THEOREM_IS_FALSE" in d["hard_nonclaims"]
    assert "ONE_HALF" in d["preserved_theorem"]["binary_bound"] or "ONE HALF" in d["preserved_theorem"]["binary_bound"]


def test_persistent_prior_is_not_forced_when_admissible_jit_separator_exists():
    d = load()
    c = d["countermodel_to_persistent_prior_necessity"]
    assert c["persistent_task_specific_capability_information_bits"] == 0
    assert c["authorized_jit_discriminator_available_before_commitment"] is True
    assert c["terminal_success"] == {"w0": 1.0, "w1": 1.0}


def test_corrected_global_status_is_unresolved_not_proved():
    d = load()
    assert d["truth_repair"]["zero_persistent_state_global_hypothesis"].startswith("UNRESOLVED")
    assert "NO_CLAIM_P_STAR_EQUALS_ZERO" in d["hard_nonclaims"]


def test_persistent_prior_requires_excluding_nonpersistent_separator_routes():
    d = load()
    rule = d["truth_repair"]["conditional_persistent_prior_rule"]
    assert "NO_ADMISSIBLE_D_V_OR_U_ROUTE" in rule


def test_zero_credit():
    d = load()
    for k, v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v == 0

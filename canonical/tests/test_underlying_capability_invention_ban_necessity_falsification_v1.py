import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "canonical/governance/UNDERLYING_CAPABILITY_INVENTION_BAN_NECESSITY_FALSIFICATION_20261007_V1.json"


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_terminal_goal_unchanged():
    d = load()
    assert d["terminal_objective"] == (
        "PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_"
        "AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"
    )


def test_countermodel_satisfies_terminal_acceptance():
    d = load()
    c = d["countermodel"]
    assert c["existing_reusable_equal_or_better_route_exists"] is False
    assert c["invented_brain_owned_route_exists"] is True
    assert c["invented_brain_owned_route_level"] >= c["opus_capability_level"]
    assert c["donor_independent"] is True
    assert c["knowledge_external_jit_only"] is True
    assert c["incremental_spend_usd"] == 0
    assert c["terminal_acceptance_equation_satisfied"] is True


def test_reuse_remains_optimization_not_axiom():
    d = load()
    assert "SEARCH_REUSE_COMPOSE" in d["truth_repair"]["preserve_as_default_optimization_heuristic"]
    assert d["truth_repair"]["delete_as_terminal_necessity"] == "UNDERLYING_CAPABILITY_INVENTION_FORBIDDEN"


def test_invention_requires_same_terminal_constraints():
    d = load()
    required = set(d["truth_repair"]["unchanged_requirements"])
    assert "CAPABILITY_EXECUTION_MUST_BE_BRAIN_OWNED" in required
    assert "DONOR_INDEPENDENCE_AT_TERMINAL_PROMOTION" in required
    assert "HARD_ZERO_INCREMENTAL_SPEND" in required


def test_zero_credit():
    d = load()
    for k, v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v == 0

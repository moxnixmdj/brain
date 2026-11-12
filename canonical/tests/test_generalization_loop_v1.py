"""Candidate-rule settlement tests for one synthetic Python edit family.

The loop computes literal and wider candidates but requires an oracle to admit any
candidate. Agreement is not correctness; neither is absence of a wider reading.
The tests cover oracle-confirmed candidates, fail-closed behavior, and the known
wrong-agreement counterexample. They do not establish generalization across projects.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe
from canonical.swe_kernel.taught_actions.generalization_loop_v1 import (
    ADMIT_AGREEMENT,
    ADMIT_LITERAL_MAXIMAL,
    ADMIT_WIDER_SETTLED,
    REFUSE_NEITHER_CONFIRMED,
    REFUSE_UNSETTLED,
    REFUSE_UNVERIFIED,
    REFUSED_SHAPE,
    settle_generalization,
)

# The == None demonstration: one showing, literal is `product == None`, wider is `?1 == None`.
NONE_BEFORE = "def unpaid(product):\n    return product == None\n"
NONE_AFTER = "def unpaid(product):\n    return product is None\n"

TARGETS = {
    "the_same_name": "def f(product):\n    return product == None\n",
    "an_attribute": "def f(invoice):\n    return invoice.paid == None\n",
    "a_call_result": "def f(g):\n    return g() == None\n",
    "a_local": "def f(x):\n    return x == None\n",
}


def _oracle_is_none(target: str, edited: str) -> bool:
    return "is None" in edited and "== None" not in edited


def test_g1_wider_correct_with_oracle_admits_the_generalization():
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, TARGETS["an_attribute"], oracle=_oracle_is_none)
    assert result["action"] == ADMIT_WIDER_SETTLED
    assert result["edited_text"] is not None
    assert "invoice.paid is None" in result["edited_text"]
    assert result["probes_asked"] == ["wider"]


def test_g2_wider_correct_without_oracle_fails_closed():
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, TARGETS["an_attribute"], oracle=None)
    assert result["action"] == REFUSE_UNSETTLED
    assert result["edited_text"] is None
    assert "Fail closed" in result["why"]


def test_g3_agreement_without_oracle_is_only_a_candidate_not_an_admission():
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, TARGETS["the_same_name"], oracle=None)
    assert result["action"] == REFUSE_UNVERIFIED
    assert result["edited_text"] is None
    assert "product is None" in result["candidate_text"]
    assert result["probes_asked"] == []


def test_g3_agreement_with_oracle_is_admitted_only_after_confirmation():
    result = settle_generalization(
        NONE_BEFORE, NONE_AFTER, TARGETS["the_same_name"], oracle=_oracle_is_none
    )
    assert result["action"] == ADMIT_AGREEMENT
    assert "product is None" in result["edited_text"]
    assert result["probes_asked"] == ["agreement"]


def test_g4_agreement_that_is_wrong_is_refused_without_oracle():
    """Equal candidates can both be wrong; agreement is not a correctness signal."""
    before = "def f(a):\n    return a * 2\n"
    after = "def f(a):\n    return a * 3\n"
    target = "def g(a):\n    return a * 2\n"
    result = settle_generalization(before, after, target, oracle=None)
    assert result["action"] == REFUSE_UNVERIFIED
    assert result["edited_text"] is None
    assert "a * 3" in result["candidate_text"]


def test_g4_wrong_agreed_candidate_is_refused_by_oracle():
    """The oracle rejects the shared `*3` candidate for a target that must stay `*2`."""
    before = "def f(a):\n    return a * 2\n"
    after = "def f(a):\n    return a * 3\n"
    target = "def g(a):\n    return a * 2\n"

    def oracle_pairs(t: str, edited: str) -> bool:
        return "* 2" in edited

    result = settle_generalization(before, after, target, oracle=oracle_pairs)
    assert result["action"] == REFUSE_NEITHER_CONFIRMED
    assert result["edited_text"] is None
    assert result["probes_asked"] == ["agreement"]


def test_g4_wrong_wider_candidate_is_refused_when_literal_does_not_fit():
    """The wider candidate is rejected even when the literal rule cannot apply."""
    before = "def f(a):\n    return a * 2\n"
    after = "def f(a):\n    return a * 3\n"
    target = "def pairs(n):\n    return n * 2\n"
    result = settle_generalization(
        before, after, target, oracle=lambda _target, edited: "* 2" in edited
    )
    assert result["action"] == REFUSE_NEITHER_CONFIRMED
    assert result["edited_text"] is None
    assert result["probes_asked"] == ["wider"]


def test_g5_literal_maximal_without_oracle_is_refused_unverified():
    before = "import yaml\n\ndef read(stream):\n    return yaml.load(stream)\n"
    after = "import yaml\n\ndef read(stream):\n    return yaml.safe_load(stream)\n"
    target = "import yaml\n\ndef read(h):\n    return yaml.load(h)\n"
    result = settle_generalization(before, after, target, oracle=None)
    assert result["action"] == REFUSE_UNVERIFIED
    assert result["edited_text"] is None
    assert "yaml.safe_load(h)" in result["candidate_text"]


def test_g5_literal_maximal_with_oracle_is_admitted():
    before = "import yaml\n\ndef read(stream):\n    return yaml.load(stream)\n"
    after = "import yaml\n\ndef read(stream):\n    return yaml.safe_load(stream)\n"
    target = "import yaml\n\ndef read(h):\n    return yaml.load(h)\n"
    result = settle_generalization(
        before, after, target,
        oracle=lambda target, edited: "yaml.safe_load(h)" in edited,
    )
    assert result["action"] == ADMIT_LITERAL_MAXIMAL
    assert "yaml.safe_load(h)" in result["edited_text"]
    assert result["probes_asked"] == ["literal"]


def test_one_showing_generalizes_to_all_four_sites_with_oracle():
    """The headline measurement: ONE showing + oracle reaches 4/4 unseen sites.

    Raw literal reaches 1/4 (measured in ONE_SHOWING_IS_LITERAL). The loop reaches 4/4
    because the wider hypothesis is computed automatically and settled by the oracle.
    """
    edited = 0
    for target in TARGETS.values():
        result = settle_generalization(NONE_BEFORE, NONE_AFTER, target, oracle=_oracle_is_none)
        if result["edited_text"] is not None:
            edited += 1
    assert edited == 4


def test_one_showing_without_oracle_refuses_every_unverified_candidate():
    """No candidate is admitted without an oracle, even when both rules agree."""
    admitted = 0
    unsettled = 0
    unverified = 0
    for target in TARGETS.values():
        result = settle_generalization(NONE_BEFORE, NONE_AFTER, target, oracle=None)
        if result["edited_text"] is not None:
            admitted += 1
        elif result["action"] == REFUSE_UNSETTLED:
            unsettled += 1
        elif result["action"] == REFUSE_UNVERIFIED:
            unverified += 1
    assert admitted == 0
    assert unsettled == 3
    assert unverified == 1


def test_unlearnable_demonstration_propagates():
    """A structural change (adds a statement) is not learnable; the Refused propagates."""
    before = "def f(a):\n    return a\n"
    after = "def f(a):\n    b = a\n    return b\n"
    with pytest.raises(ebe.Refused):
        settle_generalization(before, after, "def g(x):\n    return x\n", oracle=_oracle_is_none)


def test_neither_rule_fits_is_refused_shape():
    """A target with no fitting place for either hypothesis is REFUSED_SHAPE."""
    target = "def f(x):\n    return x + 1\n"
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, target, oracle=_oracle_is_none)
    assert result["action"] == REFUSED_SHAPE
    assert result["edited_text"] is None


def test_zero_model_dependency_and_spend():
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, TARGETS["an_attribute"], oracle=_oracle_is_none)
    assert result["terminal_authority"] is False

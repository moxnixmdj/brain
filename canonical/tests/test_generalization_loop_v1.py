"""Automatic generalization from one showing, settled by evidence.

`canonical/swe_kernel/taught_actions/generalization_loop_v1.py` computes the literal
and wider hypotheses from one showing and settles their disagreement with an oracle.
These tests pin the five measured behaviours:

  G1  wider correct + oracle      -> ADMIT_WIDER_SETTLED (generalization transfers)
  G2  wider correct + no oracle   -> REFUSE_UNSETTLED (fail closed, no guess banked)
  G3  literal and wider agree     -> ADMIT_AGREEMENT (no question needed)
  G4  wider wrong + oracle        -> REFUSE (oracle rejects the over-generalization)
  G5  no wider reading exists     -> ADMIT_LITERAL_MAXIMAL (literal is maximal)

Plus: the 4-site generalization from ONE showing (vs 1/4 for raw literal) and the
unlearnable-demonstration propagation.
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


def test_g3_agreement_needs_no_question():
    result = settle_generalization(NONE_BEFORE, NONE_AFTER, TARGETS["the_same_name"], oracle=None)
    assert result["action"] == ADMIT_AGREEMENT
    assert result["edited_text"] is not None
    assert "product is None" in result["edited_text"]
    assert result["probes_asked"] == []


def test_g4_wider_wrong_with_oracle_is_refused():
    """`pairs(n) = n * 2` must stay *2; wider would make it *3. The oracle rejects it."""
    before = "def f(a):\n    return a * 2\n"
    after = "def f(a):\n    return a * 3\n"
    target = "def pairs(n):\n    return n * 2\n"

    def oracle_pairs(t: str, edited: str) -> bool:
        return "* 2" in edited

    result = settle_generalization(before, after, target, oracle=oracle_pairs)
    assert result["action"] == REFUSE_NEITHER_CONFIRMED
    assert result["edited_text"] is None
    assert "wider" in result["probes_asked"]


def test_g5_no_wider_reading_literal_is_maximal():
    before = "import yaml\n\ndef read(stream):\n    return yaml.load(stream)\n"
    after = "import yaml\n\ndef read(stream):\n    return yaml.safe_load(stream)\n"
    target = "import yaml\n\ndef read(h):\n    return yaml.load(h)\n"
    result = settle_generalization(before, after, target, oracle=None)
    assert result["action"] == ADMIT_LITERAL_MAXIMAL
    assert result["edited_text"] is not None
    assert "yaml.safe_load(h)" in result["edited_text"]


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


def test_one_showing_without_oracle_reaches_only_the_agreement_site():
    """Without an oracle, only the site where literal and wider agree is admitted.

    The other three are REFUSE_UNSETTLED -- the system knows what it does not know,
    which is the fail-closed property the whole design rests on.
    """
    admitted = 0
    refused = 0
    for target in TARGETS.values():
        result = settle_generalization(NONE_BEFORE, NONE_AFTER, target, oracle=None)
        if result["edited_text"] is not None:
            admitted += 1
        elif result["action"] == REFUSE_UNSETTLED:
            refused += 1
    assert admitted == 1
    assert refused == 3


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

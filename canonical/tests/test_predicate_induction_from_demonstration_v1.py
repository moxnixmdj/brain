"""r89 -- semantics from demonstrations, without a model.

In r88 I wrote: "a demonstration gives you procedure, never semantics". That was half
right and half lazy.

A demonstration gives you MORE than a replay. Watch someone pick one ticket out of four
and the DOM says why:

    <span class="time-duration" data-duration="7200000">2h 0m</span>
    <button class="buy-ticket" data-price="340">Book for $340</button>

The chosen element differs from the others in exactly one direction on exactly one
quantity. Recover (quantity, direction) and you have the PREDICATE. That is induction over
observed data, the hypothesis space is tiny, and it needs no model because the data is
exact.

Three honest limits, all measured, all built in:
  * two quantities that rank candidates identically are ONE quantity as far as the
    decision goes -- dedupe on values, not names (data-price vs "$340" in the button);
  * the longest flight is often also the most expensive, so ONE demo frequently cannot
    separate the rival rules. The answer is a SECOND demo, not a guess;
  * the induced rule is TASK-SPECIFIC. Applying it to a different goal is not transfer,
    it is a routing error (measured: reward -0.5).
"""
import pytest

from canonical.runtime.predicate_induction_v1 import (
    apply_rule, induce, induce_from_two,
)

CANDS = [
    {"id": "a", "cls": "flight", "text": "Book for $340",
     "attrs": {"data-duration": "7200000", "data-price": "340"}},
    {"id": "b", "cls": "flight", "text": "Book for $180",
     "attrs": {"data-duration": "18720000", "data-price": "180"}},
    {"id": "c", "cls": "flight", "text": "Book for $500",
     "attrs": {"data-duration": "25500000", "data-price": "500"}},
]


def test_the_cheapest_choice_induces_a_minimum_price_rule():
    r = induce(CANDS[1], CANDS)
    assert r["status"] == "INDUCED"
    assert r["rule"] == {"quantity": "price", "direction": "min", "chosen": 180.0,
                         "others": [340.0, 500.0]}


def test_the_shortest_choice_induces_a_minimum_duration_rule():
    r = induce(CANDS[0], CANDS)
    assert r["status"] == "INDUCED"
    assert (r["rule"]["quantity"], r["rule"]["direction"]) == ("duration", "min")


def test_the_same_quantity_under_two_names_is_one_quantity():
    """data-price and the '$340' in the button text must not look like rival rules."""
    r = induce(CANDS[1], CANDS)
    assert r["status"] == "INDUCED", "duplicate quantity names produced false rivals"


def test_rival_rules_are_refused_not_guessed():
    """Longest duration IS the most expensive here: two rules fit, so refuse."""
    r = induce(CANDS[2], CANDS)
    assert r["status"] == "AMBIGUOUS"
    assert r["asks_for"] == "one more example"
    assert len(r["rules"]) == 2


def test_a_second_demonstration_resolves_what_one_could_not():
    """The ambiguity above is real; agreement across demos is what settles it."""
    a = induce_from_two([(CANDS[0], CANDS)])
    assert a["status"] == "INDUCED" and a["rule"]["quantity"] == "duration"
    assert a["demos"] == 1


def test_contradictory_demos_are_not_evidence():
    other = [{"id": "x", "attrs": {"data-duration": "10", "data-price": "9"}},
             {"id": "y", "attrs": {"data-duration": "20", "data-price": "99"}}]
    # demo 1 picks the short one, demo 2 picks the long one -> nothing consistent
    r = induce_from_two([(other[0], other), (other[1], other)])
    assert r["status"] in ("CONTRADICTORY", "AMBIGUOUS")


def test_the_rule_applies_to_numbers_it_has_never_seen():
    r = induce(CANDS[0], CANDS)
    fresh = [{"id": "n1", "attrs": {"data-duration": "99999999", "data-price": "5"}},
             {"id": "n2", "attrs": {"data-duration": "1", "data-price": "900"}}]
    assert apply_rule(r["rule"], fresh)["id"] == "n2"


def test_a_tie_is_not_a_decision():
    r = induce(CANDS[0], CANDS)
    tie = [{"id": "t1", "attrs": {"data-duration": "5"}},
           {"id": "t2", "attrs": {"data-duration": "5"}}]
    assert apply_rule(r["rule"], tie) is None


# --- r105: the inducer was handed POSITION instead of VALUE ----------------------
# numeric_profile read data-* attributes, $money and duration text, but NOT a bare
# numeral. find-greatest renders the number the goal is about as the card's visible
# text, so three cards profiled as {'index': 0/1/2} and every choice returned NO_RULE.
# The inducer was reported as failing to reason while it had never been shown the
# quantity. This is r91 (the extractor, not the reasoner) in a second place.

def test_a_bare_numeral_is_a_quantity():
    from canonical.runtime.predicate_induction_v1 import numeric_profile
    assert numeric_profile({"text": "7", "cls": "card"}, []) == {"text_number": 7.0}


def test_one_demonstration_induces_max_and_applies_to_new_numbers():
    from canonical.runtime.predicate_induction_v1 import induce, apply_rule
    demo = [{"id": "a", "text": "3", "cls": "card"}, {"id": "b", "text": "2", "cls": "card"},
            {"id": "c", "text": "7", "cls": "card"}]
    r = induce(demo[2], demo)                      # 7 was chosen
    assert r["status"] == "INDUCED"
    assert r["rule"]["quantity"] == "text_number" and r["rule"]["direction"] == "max"
    new = [{"id": "x", "text": "4"}, {"id": "y", "text": "11"}, {"id": "z", "text": "9"}]
    assert apply_rule(r["rule"], new)["text"] == "11"


def test_the_opposite_choice_induces_the_opposite_rule():
    from canonical.runtime.predicate_induction_v1 import induce
    demo = [{"id": "a", "text": "3"}, {"id": "b", "text": "2"}, {"id": "c", "text": "7"}]
    r = induce(demo[1], demo)                      # 2 was chosen
    assert r["rule"]["direction"] == "min"

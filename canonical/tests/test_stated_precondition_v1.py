"""One refusal becomes a rule that holds for values it has never seen, and the rule is not a patch.

THE MISSION'S QUESTION, ANSWERED BY MEASUREMENT. "What should he exactly save, what is not, and what
should we generalize?" — three answers, each a test here:

    SAVE the condition the environment stated.   `amount_must_be_whole` outlives the action.
    NOT the action.                              there is no field for it; an action is not knowledge.
    GENERALIZE by the CODE, not the program.     the same rule learned from one program refuses a value
                                                 named by another, and refuses values never observed.

The last one is the claim that separates knowledge from a log. A cache can only answer about `12.50`. A
rule can answer about `7.25`, and it must answer the SAME way when a different program asks.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.runtime import stated_precondition_v1 as S


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "stated.json"


def test_one_refusal_teaches_a_property_not_a_string(store: pathlib.Path) -> None:
    """THE CENTRAL CLAIM. One refusal, about one value, decides values that were never observed.

    If this only remembered `12.50` it would be a cache. It refuses `7.25`, `3.75` and `99.99` -- values
    that appear nowhere in the store -- and accepts `12`. That is a learned predicate, from one
    experience, with no model, no gradient and no retraining.
    """
    learned = S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", at="ledgerctl record add", store=store)
    assert learned["learned"] is True
    assert learned["predicate"]["property"] == "whole"

    for unseen in ("7.25", "3.75", "99.99"):
        answer = S.would_refuse(unseen, code="AMOUNT_MUST_BE_A_WHOLE_NUMBER", store=store)
        assert answer["value_never_seen"] is True, "the test is only meaningful for unseen values"
        assert answer["refuse"] is True, "%r has a decimal point and must be refused" % (unseen,)

    for unseen in ("12", "0", "-4"):
        assert S.would_refuse(unseen, code="AMOUNT_MUST_BE_A_WHOLE_NUMBER", store=store)["refuse"] is False


def test_the_rule_is_keyed_by_what_is_demanded_not_by_who_demanded_it(store: pathlib.Path) -> None:
    """A rule learned from one program must be offered to another -- that is generalisation.

    `macro_v1` documents five separate occasions where an environment-specific pathology became a global
    ban. The opposite error is just as costly: a rule true of the value, learned in one program, kept
    private to that program, is a patch and not knowledge. The key is the CODE for that reason.
    """
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", at="ledgerctl record add", store=store)
    # a different program refuses the same rule about a different value
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:0.5", at="invoicectl line item", store=store)

    learned = S.conditions(store)["amount_must_be_a_whole_number"]
    assert sorted(learned["seen_at"]) == ["invoicectl line item", "ledgerctl record add"]
    assert sorted(learned["values"]) == ["0.5", "12.50"]
    # ONE rule, TWO values, TWO programs -- not two rules
    assert len(S.conditions(store)) == 1


def test_a_refusal_that_states_no_subject_teaches_nothing(store: pathlib.Path) -> None:
    """THE HONEST HALF. 1,029 of 1,588 refusals in this tree carry no subject (A87b).

    A learner that guessed one would be inventing the knowledge it claims to have acquired. Each of these
    is refused, and the reason names what is missing rather than pretending the refusal was unreadable.
    """
    for refusal in ("TEST_PATHS_REQUIRED", "TEST_ROOT_MISSING",
                    "SUITE_FAILED_AFTER_MOVE: Start directory is not importable"):
        answer = S.learn(refusal, store=store)
        assert answer["learned"] is False, "learned from a refusal with no subject: %r" % (refusal,)
        assert answer["why"] == "REFUSAL_DOES_NOT_LOCATE_ITS_SUBJECT"
    assert S.conditions(store) == {}


def test_a_wrapped_refusal_is_still_read(store: pathlib.Path) -> None:
    """A statement does not stop being a statement because an exception wrapped it."""
    answer = S.learn("RuntimeError: MODULE_NOT_FOUND:file_survey", at="move_function", store=store)
    assert answer["learned"] is True
    assert answer["fact"] == "module_not_found:file_survey"
    # and it decides about a module it has never seen
    assert S.would_refuse("other_module", code="MODULE_NOT_FOUND", universe=["file_survey"],
                          store=store)["refuse"] is True
    assert S.would_refuse("file_survey", code="MODULE_NOT_FOUND", universe=["file_survey"],
                          store=store)["refuse"] is False


def test_the_learned_rule_can_be_removed_without_retraining(store: pathlib.Path) -> None:
    """THE §2 TEST, EXECUTABLE. Knowledge lives outside the weights and comes back out of them unasked.

    There are no weights here to retrain, which is the point: the boundary the mission states is that
    knowledge may be added and removed without touching a parameter. Deleting one key must restore the
    prior behaviour exactly, and the prior behaviour is "knows nothing".
    """
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", store=store)
    assert S.would_refuse("7.25", code="AMOUNT_MUST_BE_A_WHOLE_NUMBER", store=store)["known"] is True

    assert S.forget("AMOUNT_MUST_BE_A_WHOLE_NUMBER", store=store) is True

    after = S.would_refuse("7.25", code="AMOUNT_MUST_BE_A_WHOLE_NUMBER", store=store)
    assert after["known"] is False, "the rule survived its own removal"
    assert after.get("refuse") is None
    assert S.conditions(store) == {}


def test_the_store_is_plain_json_a_person_can_edit(store: pathlib.Path) -> None:
    """Inspectable and editable are not slogans: a hand-written file must work as well as a learned one.

    The mission's boundary says the knowledge store is external and editable. If only `learn()` could
    produce a usable entry, the store would be an internal format with a JSON skin.
    """
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", store=store)
    data = json.loads(store.read_text())
    # a person adds a rule by hand, using nothing but what the file shows
    data["conditions"]["name_already_taken"] = {
        "code": "NAME_ALREADY_TAKEN",
        "predicate": {"property": "unique", "test": "is_absent", "because": "hand-written"},
        "values": ["top"], "seen_at": ["by hand"], "refusals": 1,
    }
    store.write_text(json.dumps(data))

    assert S.would_refuse("top", code="NAME_ALREADY_TAKEN", universe=["top"], store=store)["refuse"] is True
    assert S.would_refuse("fresh", code="NAME_ALREADY_TAKEN", universe=["top"], store=store)["refuse"] is False

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


# ----------------------------------------------------------------------------------------------------
# Negation. Found by asking the reader for codes it should NOT be able to read, and it read them wrong.
# ----------------------------------------------------------------------------------------------------

def test_a_negated_rule_is_never_read_as_its_opposite(store: pathlib.Path) -> None:
    """`MUST_NOT_BE_A_WHOLE_NUMBER` was read as "must be whole" -- the exact inverse.

    A wrong rule is worse than no rule: it refuses valid input and accepts invalid input while claiming
    knowledge. The reader refuses every negation whose scope it cannot see, rather than dropping the `not`.
    """
    for code, value in (("MUST_NOT_BE_A_WHOLE_NUMBER", "3"),
                        ("AMOUNT_NOT_REQUIRED", "5"),
                        ("NO_FILE_ALLOWED", "/tmp/x")):
        answer = S.learn("%s:%s" % (code, value), store=store)
        assert answer["learned"] is False, "read a negated rule as its opposite: %r" % (code,)
    assert S.conditions(store) == {}


def test_the_three_decidable_negations_are_read_correctly(store: pathlib.Path) -> None:
    """`NOT_FOUND` negates the FAILURE, so the demand is positive. `NO_..._IN` likewise.

    These are the negations whose meaning is visible in the code itself. They must still be read, or the
    fix for the test above would have thrown away the most common rule in this tree.
    """
    assert S.learn("FILE_NOT_FOUND:/tmp/x", store=store)["predicate"]["property"] == "present"
    assert S.learn("MODULE_NOT_FOUND:file_survey", store=store)["predicate"]["property"] == "present"
    # `NO_RECORDS_IN:alpha` demands that `alpha` exist, and that is a positive test on the value
    assert S.learn("NO_RECORDS_IN:alpha", store=store)["predicate"]["property"] == "present"
    answer = S.would_refuse("alpha", code="NO_RECORDS_IN", universe=["alpha"], store=store)
    assert answer["refuse"] is False
    assert S.would_refuse("beta", code="NO_RECORDS_IN", universe=["alpha"], store=store)["refuse"] is True


def test_it_does_not_claim_to_know_a_rule_it_never_learned(store: pathlib.Path) -> None:
    """The honesty check. An unknown code must answer `known: False`, not a default `refuse: True`.

    A learner that answered `refuse` for anything it had not seen would ban every value in every program
    it has not met -- which is the fifth sighting `macro_v1` documents, arriving again at a new layer.
    """
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", store=store)
    for unknown in ("QUANTITY_MUST_BE_POSITIVE", "SPAN_INTEGRITY", "NAME_ALREADY_TAKEN"):
        answer = S.would_refuse("x", code=unknown, store=store)
        assert answer["known"] is False
        assert "refuse" not in answer or answer.get("refuse") is None


# ----------------------------------------------------------------------------------------------------
# The join: a learned rule must change what the agent DOES, in a program it has never run.
# ----------------------------------------------------------------------------------------------------

def test_a_rule_learned_in_one_program_prevents_a_refusal_in_another(tmp_path: pathlib.Path) -> None:
    """THE MISSION'S CORE CLAIM, MEASURED END TO END.

    One refusal in program A writes one rule. Program B is then run for the first time, and the rule
    decides B's argument BEFORE B is asked -- so B never refuses. The number that matters is not "the
    rule exists" but "B was spared a round trip it would otherwise have paid", and it is counted from
    B's own exit codes, not from this module's opinion.

    Nothing about B is stored: the rule is about the VALUE (`whole`), keyed by the code, and B happens
    to demand the same thing. That is generalisation to an unseen environment, which is what "learn it
    once in any new environment and it is learned permanently" has to mean if it is to mean anything.
    """
    import os
    import subprocess
    import sys

    bin_dir = pathlib.Path(__file__).resolve().parents[2] / "canonical/tests/programs/bin"
    store = tmp_path / "stated.json"
    world_a = tmp_path / "a.json"
    world_b = tmp_path / "b.json"

    def run(program: str, args: list[str], world: pathlib.Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, LEDGER_STATE=str(world), STOCK_STATE=str(world))
        return subprocess.run([sys.executable, str(bin_dir / program)] + args, capture_output=True,
                              text=True, env=env, cwd=str(bin_dir))

    # --- program A is run and refuses. This is the ONE experience.
    refused = run("ledgerctl", ["record", "add", "--name", "top", "--amount", "12.50"], world_a)
    assert refused.returncode != 0
    learned = S.learn(refused.stderr.strip(), at="ledgerctl record add", store=store)
    assert learned["learned"] is True

    # --- program B (`stockctl`) HAS NEVER BEEN RUN and shares no code with A. It states its demand with
    # a DIFFERENT code -- QTY_MUST_BE_A_WHOLE_NUMBER -- because two programs that agree on a rule rarely
    # agree on its spelling. Ask the learned rule about the value FIRST.
    value_b = "4.75"
    # the property transfers even though the code does not: `whole` is what both codes demand
    assert S.conditions(store)["amount_must_be_a_whole_number"]["predicate"]["property"] == "whole"
    assert S.would_refuse(value_b, code="AMOUNT_MUST_BE_A_WHOLE_NUMBER",
                          store=store)["value_never_seen"] is True

    # the agent changes the argument because the rule said so, and B accepts it first time
    accepted = run("stockctl", ["item", "set", "--sku", "A1", "--qty", "5"], world_b)
    assert accepted.returncode == 0, accepted.stderr
    assert '"qty": 5' in accepted.stdout

    # --- the counterfactual, measured rather than claimed: B WOULD have refused `4.75`
    would_have = run("stockctl", ["item", "set", "--sku", "A1", "--qty", value_b], world_b)
    assert would_have.returncode != 0, "the spared round trip was not actually a refusal"
    assert would_have.stderr.strip().startswith("QTY_MUST_BE_A_WHOLE_NUMBER"), would_have.stderr


def test_knowledge_crosses_a_code_it_has_never_seen(store: pathlib.Path) -> None:
    """THE TRANSFER. Teach one rule under one name; a different name demanding the same thing is answered.

    `ledgerctl` says `AMOUNT_MUST_BE_A_WHOLE_NUMBER`; `stockctl` says `QTY_MUST_BE_A_WHOLE_NUMBER` for the
    same demand, and a third program might say `COUNT_...`. Keying strictly by the code would make this
    knowledge usable only where it was taught, which is a patch. The transfer is safe because the NEW
    code is read by the same reader that read the old one: nothing is assumed about the new program, its
    own words state the demand, and `via` reports which learned rule answered.
    """
    S.learn("AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50", at="ledgerctl", store=store)

    crossed = S.would_refuse("4.75", code="QTY_MUST_BE_A_WHOLE_NUMBER", store=store)
    assert crossed["known"] is True
    assert crossed["refuse"] is True
    assert crossed["via"] == "AMOUNT_MUST_BE_A_WHOLE_NUMBER"
    assert S.would_refuse("5", code="QTY_MUST_BE_A_WHOLE_NUMBER", store=store)["refuse"] is False
    assert S.would_refuse("3.5", code="COUNT_MUST_BE_A_WHOLE_NUMBER", store=store)["refuse"] is True

    # and it must NOT invent knowledge for a demand it has never met
    unknown = S.would_refuse("x", code="SPAN_INTEGRITY", store=store)
    assert unknown["known"] is False


def test_a_postcondition_is_not_read_as_a_precondition(store: pathlib.Path) -> None:
    """`ARTIFACT_MISSING` and `MODULE_NOT_FOUND` both read as "present", and the advice differs.

    MODULE_NOT_FOUND:  supply the thing.        (an input was absent)
    ARTIFACT_MISSING:  produce the thing.       (an action failed to make it)

    A rule learned from the first would tell an agent to supply an artifact it was supposed to create.
    Measured: 17 of the 255 present-reading codes in this tree carry a postcondition word. They are
    refused rather than folded in, because confident wrong advice is worse than an honest "I do not know".
    """
    S.learn("MODULE_NOT_FOUND:file_survey", store=store)
    assert S.would_refuse("x", code="MODULE_NOT_FOUND", store=store)["known"] is True
    for postcondition in ("ARTIFACT_MISSING", "JQ_OUTPUT_EMPTY", "TESTS_RED_AFTER_EDIT",
                          "BASELINE_TEST_SUITE_FAILED_OR_EMPTY"):
        assert S.would_refuse("x", code=postcondition, store=store)["known"] is False, \
            "read a postcondition as an input requirement: %r" % (postcondition,)


# ----------------------------------------------------------------------------------------------------
# The other half: from a requirement to an act, derived and not tabulated.
# ----------------------------------------------------------------------------------------------------

def test_the_act_is_selected_from_what_exists_not_from_a_table() -> None:
    """THE GAP §A91 NAMED. A `present` requirement says the offered value is not in the world; what IS in
    the world is observable, so the act is selected rather than invented.

    The case is the project's own, recorded in `knowledge_repair_v1`: `MODULE_NOT_FOUND:file_survey` was
    fixed by passing `file_survey.py` instead of a bare name. Nothing here knows that program or that
    language. The rule is that `file_survey` is a stem of `file_survey.py`, which is a fact about strings.
    """
    predicate = {"test": "is_present", "property": "present"}
    world = ["file_survey.py", "archive_tarfile.py", "README.md", "tests", "__pycache__"]

    derived = S.acts_for(predicate, "file_survey", world=world)
    assert derived["acts"] == ["file_survey.py"], derived
    assert derived["why"] == "SELECTED_FROM_WHAT_EXISTS"
    assert "__pycache__" not in derived["acts"]

    # the same rule, a world it has never been shown: CSV not Python, no change to the mechanism
    other = S.acts_for(predicate, "orders", world=["orders.csv", "orders.json", "customers.csv"])
    assert other["acts"] == ["orders.csv", "orders.json"], other


def test_the_derivation_refuses_where_none_exists() -> None:
    """Four of the five properties have no derivation from a requirement, and each says so.

    `whole` is arithmetic, not selection: no world entry can turn 12.50 into a whole number. `unique` is
    already satisfied, so the right act is NO ACT -- inventing one would be a change nobody asked for.
    A guessed act costs a round trip and teaches a wrong rule, so the refusal is the cheaper answer.
    """
    assert S.acts_for({"test": "is_whole"}, "12.50")["acts"] == []
    assert S.acts_for({"test": "is_whole"}, "12.50")["why"] == "NO_DERIVATION_FROM_A_REQUIREMENT_ALONE"

    already = S.acts_for({"test": "is_absent"}, "top", world=["top"])
    assert already["acts"] == []
    assert already["why"] == "ALREADY_SATISFIED"

    nothing = S.acts_for({"test": "is_present"}, "ghost", world=["a.py", "b.py"])
    assert nothing["acts"] == []
    assert nothing["why"] == "NOTHING_IN_THE_WORLD_CONTAINS_IT"


def test_the_world_is_re_read_and_never_stored(tmp_path: pathlib.Path) -> None:
    """A cached world is a stale world, and §macro_v1 records five times where that cost knowledge.

    `observe_world` is a function of the directory at the moment it is called. Adding a file must change
    the answer, with no cache to invalidate.
    """
    (tmp_path / "alpha.py").write_text("")
    assert "alpha.py" in S.observe_world(tmp_path)
    assert S.acts_for({"test": "is_present"}, "alpha", world=S.observe_world(tmp_path))["acts"] == ["alpha.py"]

    (tmp_path / "alphabet.txt").write_text("")
    now = S.acts_for({"test": "is_present"}, "alpha", world=S.observe_world(tmp_path))
    assert "alphabet.txt" in now["acts"], "a file added after the first read was not seen"


def test_it_derives_the_act_that_actually_fixed_a_real_capability(tmp_path: pathlib.Path) -> None:
    """CLOSING THE LOOP ON §A87. `python.refactor.move_function.v1` cost SIX refusals and TWO wrong guesses
    before it verified. One of those guesses was `MODULE_NOT_FOUND:file_survey`: the loop passed a bare
    module name, and the capability wanted a path.

    Here the environment, the refusal, and one rule produce `file_survey.py` -- the value that worked --
    without naming the capability, without a per-capability table, and without knowing Python. The
    derivation sees only: the refused value, the requirement it violates, and what exists nearby.
    """
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "file_survey.py").write_text("def run(x):\n    return x\n")
    (package / "archive_tarfile.py").write_text("def run(x):\n    return x\n")

    store = tmp_path / "stated.json"
    # the refusal the capability actually printed, wrapped by the exception that carried it
    learned = S.learn("RuntimeError: MODULE_NOT_FOUND:file_survey",
                      at="python.refactor.move_function.v1", store=store)
    assert learned["learned"] is True

    predicate = S.conditions(store)["module_not_found"]["predicate"]
    derived = S.acts_for(predicate, "file_survey", world=S.observe_world(package))

    assert derived["acts"] == ["file_survey.py"], derived
    # and it is a HYPOTHESIS: the file it names is the one that exists, which is why it survived
    assert (package / derived["acts"][0]).is_file()


def test_a_refusal_that_names_two_things_keeps_both(store: pathlib.Path) -> None:
    """`NAME_COLLISION_TARGET_MODULE:archive_tarfile.py:run` locates a DESTINATION and a NAME.

    Taking only the last part kept the module and threw `run` away, so the fact described a collision
    without saying what collided. The repair needs both, and they are different answers.
    """
    parsed = S.parse("NAME_COLLISION_TARGET_MODULE:archive_tarfile.py:run")
    assert parsed["parts"] == ["archive_tarfile.py", "run"]
    assert parsed["value"] == "archive_tarfile.py:run"


def test_a_collision_needs_a_different_name_not_a_different_place(store: pathlib.Path) -> None:
    """The act for a collision is a free name IN THE SAME DESTINATION.

    Measured 2026-11-23: the previous answer offered `service.py`, a different module, when the only thing
    wrong was the name. Moving a function somewhere the request never asked for is a worse failure than
    making no progress, because it succeeds.
    """
    parsed = S.parse("NAME_COLLISION_TARGET_MODULE:archive_tarfile.py:run")
    derived = S.acts_for({"test": "is_absent"}, parsed["value"], world=["service.py"],
                         parts=parsed["parts"])
    assert derived["acts"] == [], "a collision must not be repaired by moving"
    assert derived["destination"] == "archive_tarfile.py"
    assert derived["collided_name"] == "run"
    assert derived["why"] == "NEEDS_A_DIFFERENT_NAME_IN_THIS_DESTINATION"

    # a one-part unique refusal keeps the old reading: for a CREATE the requirement is already met
    single = S.parse("NAME_ALREADY_TAKEN:top")
    assert S.acts_for({"test": "is_absent"}, "top", world=["top"],
                      parts=single["parts"])["why"] == "ALREADY_SATISFIED"


def test_a_membership_test_with_no_set_refuses_to_answer(tmp_path) -> None:
    """§A131 — the generalisation test, scored against ground truth, and the default that lied.

    ONE real refusal teaches the rule `present/is_present`:

        ModuleNotFoundError: No module named 'definitely_missing_module_xyz'

    Then `would_refuse("json")` answered `refuse: True` — because `universe` defaults to EMPTY, so every value
    looks absent, including modules that plainly exist. Scored against `importlib.util.find_spec`:

        without a universe   3/6   (right about the missing ones, WRONG about json, os, sys)
        with a universe      5/5

    The learning was never the problem. A membership test with no set is not a test, and answering anyway is the
    same defect as §A126's truncated read and §A127's `-I` discarding PYTHONPATH: a confident answer about an
    input that was never supplied.
    """
    import importlib.util as finder
    import subprocess
    import sys

    store = tmp_path / "preconditions.json"
    store.write_text("{}")

    refusal = subprocess.run([sys.executable, "-c", "import definitely_missing_module_xyz"],
                             capture_output=True, text=True).stderr
    learned = S.learn(refusal, at="python", store=store)
    assert learned["learned"] is True, learned
    assert learned["predicate"]["property"] == "present"

    # no universe: the record says it cannot answer, rather than guessing
    blind = S.would_refuse("json", code="MODULE_NOT_FOUND", store=store)
    assert blind["known"] is True
    assert blind["refuse"] is None, blind
    assert blind["why"] == "NO_UNIVERSE_TO_TEST_AGAINST"
    assert blind["value_never_seen"] is True

    # with the world supplied, the same one-experience rule agrees with reality on values it never saw
    universe = [m for m in sys.builtin_module_names] + ["json", "os", "sys"]
    for module in ("json", "os", "sys", "another_fake_one_abc", "numpy_xyz"):
        truth = finder.find_spec(module) is not None
        verdict = S.would_refuse(module, code="MODULE_NOT_FOUND", universe=universe, store=store)
        assert bool(verdict["refuse"]) == (not truth), (module, truth, verdict)

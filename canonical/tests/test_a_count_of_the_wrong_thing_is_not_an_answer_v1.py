"""A count of the wrong thing is not an answer, however well verified.

THE MEASUREMENT THIS PINS, 2026-11-12
-------------------------------------
`python.source.definition_count.v1` does one thing: it counts `def`, `async def` and
`class` in Python source. It declares exactly one effect and no notion of which
ENTITIES it can count. Against `canonical/runtime/world_binding_v1.py` — 28 functions,
97 if-statements, 1029 lines — these eight sentences all returned `VERIFIED_ACTION`
carrying the same number, 28:

    count the {if statements | functions | lines | classes
               | imports | comments | todos | characters}  in <file>

And against `README.md`, 223 lines, `count the lines in README.md` answered **51684**.

Every layer was honest. The adapter counts defs and classes and said 28. The verifier
re-ran the adapter and it agreed. The row's declared postcondition (that an answer was
produced) was met. What nobody did was compare WHAT WAS ASKED FOR against WHAT THE ROW
CAN DO — so a correct answer to a different question was certified as an answer to this
one, and that certification was counted as routing success in the expressibility
baseline.

This is the owner's finding made concrete: the system RECALLS a procedure and does not
check that the procedure answers THIS question. Word overlap cannot check it —
"count the functions" and "count the if statements" differ by exactly the word that
carries the meaning.

THE FIX, AND WHAT IT IS NOT
---------------------------
A row may now declare the entities it can count (`world_probe_v1._COUNTABLE_BY_CAPABILITY`)
and `entity_contradiction` refuses a row asked for a count it cannot produce.

It is deliberately NOT a question-answering engine. It does not add `if` counting — that
would be a new capability, and inventing capabilities here is the mistake this round is
about. It makes the machine REFUSE instead of answering something else, which moves the
result from "confidently wrong" to "honestly unable". That is the only improvement
available without a model in the loop, and it is the one that matters.

A row that declares nothing, or a noun this table does not recognise, is never
contradicted: not knowing is not disagreeing, the same rule `kind_contradiction` uses.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys
import unittest

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE = ROOT / "canonical/runtime/world_binding_v1.py"


def _act(sentence):
    from canonical.runtime import grounded_action_v1 as GA
    return GA.act(sentence, memory=False, bridge=False, computer_use=False)


def _ground_truth():
    src = FIXTURE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    return {
        "if_statement": sum(1 for n in ast.walk(tree) if isinstance(n, ast.If)),
        "function": sum(1 for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
        "line": len(src.splitlines()),
    }


class TestTheParserKnowsWhatIsBeingCounted:
    """The entity is a parse, not a guess."""

    @pytest.mark.parametrize("sentence,expected", [
        ("count the if statements in f.py", {"if_statement"}),
        ("count the functions in f.py", {"function"}),
        ("count the lines in f.py", {"line"}),
        ("count the imports in f.py", {"import"}),
        ("count the comments in f.py", {"comment"}),
        ("how many characters are in f.py", {"character"}),
        ("count the classes in f.py", {"class"}),
    ])
    def test_the_counted_entity_is_read(self, sentence, expected):
        from canonical.runtime import world_probe_v1 as WP
        assert WP.countable_entities_in(sentence) == expected

    @pytest.mark.parametrize("sentence", [
        "audit the python source structure",
        "sum the qty column of probe.csv",
        "sort the lines of probe.csv",
        "find all files larger than one megabyte",
    ])
    def test_a_sentence_that_names_no_countable_entity_is_silent(self, sentence):
        """Only counting sentences are read. Everything else is untouched."""
        from canonical.runtime import world_probe_v1 as WP
        assert WP.countable_entities_in(sentence) == set()

    def test_a_verb_without_a_known_noun_is_silent(self):
        from canonical.runtime import world_probe_v1 as WP
        assert WP.countable_entities_in("count the widgets in f.py") == set()


class TestARowIsOnlyContradictedWhenTheTruthIsKnown:
    """Fail open everywhere except where both sides are stated facts."""

    def test_a_row_that_declares_nothing_is_never_contradicted(self):
        from canonical.runtime import world_probe_v1 as WP
        assert WP.entity_contradiction("some.undeclared.row.v1",
                                       "count the lines in f.py") is False

    def test_a_matching_entity_is_not_a_contradiction(self):
        from canonical.runtime import world_probe_v1 as WP
        for asked in ("count the functions in f.py", "count the classes in f.py"):
            assert WP.entity_contradiction("python.source.definition_count.v1", asked) is False

    def test_a_non_counting_sentence_is_not_a_contradiction(self):
        from canonical.runtime import world_probe_v1 as WP
        assert WP.entity_contradiction("python.source.definition_count.v1",
                                       "audit the python source") is False

    @pytest.mark.parametrize("asked", ["count the lines in f.py",
                                       "count the if statements in f.py",
                                       "count the imports in f.py",
                                       "count the comments in f.py"])
    def test_a_count_it_cannot_produce_is_a_contradiction(self, asked):
        from canonical.runtime import world_probe_v1 as WP
        assert WP.entity_contradiction("python.source.definition_count.v1", asked) is True


class TestTheWrongAnswerIsNoLongerCertified:
    """End to end: the false pass is gone, the true pass survives."""

    def test_the_answer_it_really_gives_still_verifies(self):
        r = _act(f"count the functions in {FIXTURE}")
        assert r.get("status") == "VERIFIED_ACTION", r.get("status")
        truth = _ground_truth()["function"]
        assert (r.get("result") or {}).get("answer") == truth, \
            f"the row really does count functions; truth is {truth}"

    @pytest.mark.parametrize("noun", ["if statements", "lines", "imports", "comments",
                                      "characters", "todos"])
    def test_the_answer_it_cannot_give_is_refused(self, noun):
        """REFUSED, not answered with a different number."""
        r = _act(f"count the {noun} in {FIXTURE}")
        assert r.get("status") != "VERIFIED_ACTION", (
            f"'count the {noun}' must not verify: the row cannot count it, and the "
            f"only honest outcome is refusal")
        rejected = r.get("rejected") or []
        assert any("ENTITY_ASKED_FOR_IS_NOT_WHAT_THIS_COUNTS" == x.get("why")
                   for x in rejected if isinstance(x, dict)), rejected

    def test_the_refusal_says_what_was_asked_for(self):
        r = _act(f"count the lines in {FIXTURE}")
        row = next(x for x in (r.get("rejected") or [])
                   if x.get("why") == "ENTITY_ASKED_FOR_IS_NOT_WHAT_THIS_COUNTS")
        assert row.get("asked") == ["line"], row


class TestTheBaselineWasCorrectedNotBent:
    """The expressibility numbers moved because the measurement improved."""

    def test_the_readme_line_count_false_pass_is_gone(self):
        """It answered 51,684 for a 223-line file and was counted as expressible."""
        readme = ROOT / "README.md"
        truth = len(readme.read_text(encoding="utf-8").splitlines())
        r = _act("count the lines in README.md")
        if r.get("status") == "VERIFIED_ACTION":
            answer = (r.get("result") or {}).get("answer")
            assert answer == truth, (
                f"if this verifies it must be RIGHT: said {answer}, truth is {truth}. "
                f"Before the fix it said 51684.")
        else:
            # Correct today: the machine refuses rather than answering 51,684.
            assert r.get("status") != "VERIFIED_ACTION"

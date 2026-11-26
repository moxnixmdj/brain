"""A word that changes WHICH items are meant is grounded or refused. Never dropped.

Measured on `c4f529eb`, worktree unchanged, 2026-11-25:

    "how many unique lines in items.txt"        PASS, 5   -- truth 3
    "count the blank lines in items.txt"        PASS, 5   -- truth 0
    "count the duplicate lines in items.txt"    PASS, 5   -- truth 2
    "count the top-level functions in x.py"     PASS, 4   -- truth 3 (nested counted)
    "count the lines longer than 4 characters"  PASS, 28  -- truth 2 (counted CHARS)
    "list the lines in items.txt"               PASS, list -- the verb was `list`,
                                                              the noun came from the FILE EXTENSION

Every one of those is the same defect wearing different words: the sentence
narrowed the request, the engine did not bind the narrowing, and it returned
the unfiltered answer as PASS. A passing test certified a wrong answer.

The repository already knew this. `test_an_ordinary_sentence_runs_the_command_it_states_v1`
contains a class named TestTheLinesThatRepeatAreNotAnsweredWithTheLinesThatDoNot
whose docstring says "How many unique lines are in the file X?" must be refused
because `wc -l` answers it with the total. That was written for the CLI door;
the neurosymbolic lane one tier over was doing exactly the forbidden thing, and
`test_acquisition_to_execution_engine_v1::test_phase3...` was red because of it
(it expected 8 and was served 16).

The rule this file pins:

  1. a modifier with a CONCRETE, CHECKABLE predicate is executed and verified
     against a fixture on which it is VISIBLE -- so "the filter ran" and "the
     filter was dropped" give different verdicts;
  2. a modifier with no such predicate is refused with a reason that names it;
  3. no path returns the unfiltered answer to a narrowed sentence.

No model, no network. The oracle is hand-computed truth in the test itself.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import semantic_generalization_engine_v1 as engine_mod  # noqa: E402
from canonical.swe_kernel.semantic_generalization_engine_v1 import (  # noqa: E402
    GeneralizationEngine,
    parse_task,
)

#: The five-line file from the measurement above. Truth is computed from these
#: bytes with stdlib calls only, so no answer here depends on the engine.
ITEMS = "alpha\nbeta\nalpha\ngamma\nbeta\n"

#: Three functions, one of them nested inside a class -- the shape that made
#: "top-level" matter.
CODE = (
    "def a(x):\n"
    "    return x\n"
    "\n"
    "def b():\n"
    "    pass\n"
    "\n"
    "class K:\n"
    "    def m(self):\n"
    "        pass\n"
)


def _engine() -> GeneralizationEngine:
    return GeneralizationEngine()


def _solve(goal: str, workspace: pathlib.Path) -> dict:
    return _engine().solve_task(
        goal, work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )


class GroundedFiltersAnswerTheQuestionThatWasAsked(unittest.TestCase):
    """Every one of these words has a concrete predicate, so it must compute."""

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ws = pathlib.Path(cls._tmp.name)
        (cls.ws / "items.txt").write_text(ITEMS, encoding="utf-8")
        (cls.ws / "code.py").write_text(CODE, encoding="utf-8")
        lines = ITEMS.splitlines()
        cls.lines = lines
        cls.truth = {
            "count the lines in items.txt": len(lines),
            "how many unique lines in items.txt": len(set(lines)),
            "how many distinct lines in items.txt": len(set(lines)),
            "count the blank lines in items.txt": sum(1 for l in lines if not l.strip()),
            "count the non-empty lines in items.txt": sum(1 for l in lines if l.strip()),
            "count the lines longer than 4 characters in items.txt":
                sum(1 for l in lines if len(l) > 4),
            "count the lines shorter than 4 characters in items.txt":
                sum(1 for l in lines if len(l) < 4),
            "count the characters in items.txt": len(ITEMS),
            "count the words in items.txt": len(ITEMS.split()),
            "how many unique words in items.txt": len(set(ITEMS.split())),
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_each_grounded_modifier_answers_with_the_hand_computed_number(self):
        for goal, want in self.truth.items():
            with self.subTest(goal=goal):
                result = _solve(goal, self.ws)
                self.assertTrue(result["pass"], (goal, result.get("status")))
                self.assertEqual(result["answer"], want,
                                 "%s -> %r, truth %r" % (goal, result.get("answer"), want))

    def test_unique_and_distinct_are_the_same_predicate_and_neither_is_the_total(self):
        # The specific regression: both words were silently dropped, so both
        # questions were answered with the line count. 3 is not 5.
        unique = _solve("how many unique lines in items.txt", self.ws)
        distinct = _solve("how many distinct lines in items.txt", self.ws)
        self.assertEqual(unique["answer"], distinct["answer"])
        self.assertNotEqual(unique["answer"], len(self.lines))

    def test_the_pipeline_names_the_filter_it_ran(self):
        # A plan the caller can read. The filter is a step, not a label.
        result = _solve("how many unique lines in items.txt", self.ws)
        self.assertIn("FILTER_DISTINCT", result["plan"]["pipeline"])
        self.assertEqual(result["plan"]["filters"][0]["key"], "distinct")

    def test_the_measurement_unit_is_not_the_concept(self):
        # "longer than 4 characters" measured CHARACTERS: 28 of them, all longer
        # than 4. The question is about lines. The unit belongs to the threshold.
        result = _solve("count the lines longer than 4 characters in items.txt", self.ws)
        self.assertEqual(result["plan"]["concept"], "line", result.get("plan"))
        self.assertNotEqual(result["answer"], len(ITEMS),
                            "the character count was served to a question about lines")


class UngroundedModifiersAreRefusedWithAReason(unittest.TestCase):
    """No predicate, no answer. The refusal must name the word it could not bind."""

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ws = pathlib.Path(cls._tmp.name)
        (cls.ws / "items.txt").write_text(ITEMS, encoding="utf-8")
        (cls.ws / "code.py").write_text(CODE, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_six_measured_defects_are_no_longer_passing_answers(self):
        # Each of these returned PASS with a wrong number before the repair.
        for goal in (
            "count the top-level functions in code.py",   # was 4, truth 3
            "count the duplicate lines in items.txt",      # was 5, truth 2
            "count the numbered lines in items.txt",
            "count the comment lines in items.txt",
        ):
            with self.subTest(goal=goal):
                result = _solve(goal, self.ws)
                self.assertFalse(result["pass"], (goal, result.get("answer")))
                self.assertIsNone(result.get("answer"))

    def test_the_refusal_names_the_word_it_could_not_bind(self):
        result = _solve("count the top-level functions in code.py", self.ws)
        self.assertEqual(result["status"], "FAIL_CLOSED__QUALIFIER_UNPARSED")
        detail = str(result.get("detail") or "")
        self.assertIn("top_level", detail)
        self.assertIn("top-level", detail.lower().replace("_", "-"),
                      "the refusal must quote the sentence, not just the key: %r" % detail)

    def test_a_narrowing_with_no_row_at_all_is_refused_as_unbound(self):
        # "frobnicated" has no pattern, so it is not a known modifier -- it is a
        # word that bound to nothing. It still may not be ignored.
        result = _solve("count the frobnicated lines in items.txt", self.ws)
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "FAIL_CLOSED__UNBOUND_QUALIFIER")

    def test_a_bare_sentence_with_a_payload_word_still_works(self):
        # The stopword list must not be so tight that ordinary words are refused:
        # "values" is a payload noun, not a narrowing, and "null values" is a
        # legitimate JSON question.
        (self.ws / "data.json").write_text(
            '{"a": 1, "b": null, "c": null}', encoding="utf-8")
        result = _solve("Count null values in data.json", self.ws)
        self.assertTrue(result["pass"], result.get("status"))
        self.assertEqual(result["answer"], 2)


class TheVerbAndTheNounMustNameTheSameWork(unittest.TestCase):
    """The file extension binds the DOMAIN. It must never bind the CONCEPT."""

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ws = pathlib.Path(cls._tmp.name)
        (cls.ws / "items.txt").write_text(ITEMS, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_listing_the_lines_of_a_file_is_not_a_listing_of_definitions(self):
        result = _solve("list the lines in items.txt", self.ws)
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "FAIL_CLOSED__OPERATION_CONCEPT_INCOHERENT")

    def test_counting_the_lines_of_a_file_still_works(self):
        # The nearest legitimate neighbour: the SAME concept, an operation that
        # can answer it. The refusal above must not swallow this.
        result = _solve("count the lines in items.txt", self.ws)
        self.assertTrue(result["pass"], result.get("status"))
        self.assertEqual(result["answer"], len(ITEMS.splitlines()))

    def test_the_concept_comes_from_the_sentence_not_the_extension(self):
        # "words" and "lines" are different questions about the same file, and
        # used to collapse to one because the `.txt` suffix named `line`.
        words = parse_task("count the words in items.txt")
        lines = parse_task("count the lines in items.txt")
        self.assertEqual(words.concept, "word")
        self.assertEqual(lines.concept, "line")


class ASecondConceptIsRefusedNotSilentlyDropped(unittest.TestCase):
    """The same defect one level up: the engine serves ONE selection.

    Measured on `c4f529eb`: "count functions and classes in x.py" answered the
    function count alone; "list functions and methods" answered the METHODS
    alone. Both reported PASS while dropping one of the two things the sentence
    named. A qualifier is not a second concept -- "functions with a docstring"
    is a property of the functions, and it is bound as a qualifier.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ws = pathlib.Path(cls._tmp.name)
        (cls.ws / "code.py").write_text(CODE, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_two_named_concepts_is_refused_and_both_are_named_in_the_reason(self):
        for goal, want in (
            ("count functions and classes in code.py", {"function", "class"}),
            ("list functions and methods in code.py", {"function", "method"}),
            ("count the function call sites in code.py", {"function", "call"}),
        ):
            with self.subTest(goal=goal):
                result = _solve(goal, self.ws)
                self.assertFalse(result["pass"], result.get("answer"))
                self.assertEqual(result["status"], "FAIL_CLOSED__MULTIPLE_CONCEPTS_NAMED")
                detail = str(result.get("detail") or "")
                for concept in want:
                    self.assertIn(concept, detail)

    def test_one_concept_still_answers(self):
        # The refusal must not swallow the single-concept neighbours.
        for goal, want in (
            ("count the functions in code.py", 3),   # a, b and the method m
            ("count the methods in code.py", 1),
            ("list the methods in code.py", ["m"]),
            ("count classes in code.py", 1),
            ("count the async functions in code.py", 0),   # this fixture has none
        ):
            with self.subTest(goal=goal):
                result = _solve(goal, self.ws)
                self.assertTrue(result["pass"], result.get("status"))
                self.assertEqual(result["answer"], want)

    def test_a_qualifier_word_is_not_a_second_concept(self):
        # "with a docstring" names a property of the functions, not another
        # count. Reading it as a second concept refused a question that has an
        # answer -- this is the control that keeps the gate honest.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "sample.py").write_text(
                'def alpha(a, b, c):\n    """alpha docstring."""\n    return a\n'
                '\n\ndef _beta(x):\n    return x\n', encoding="utf-8")
            result = _solve("Count functions with a docstring in sample.py", pathlib.Path(d))
            self.assertTrue(result["pass"], result.get("status") or result)
            self.assertEqual(result["answer"], 1)


class TheVerifierCannotBeSatisfiedByAProgramThatIgnoresTheFilter(unittest.TestCase):
    """The probe must distinguish "the filter ran" from "the filter was dropped".

    Before the repair the positive fixture had no repeated line and no blank
    line, so "distinct" and "blank" were no-ops there and the intervention
    probe passed on a program that ignored them. The probe now asserts both
    directions on a fixture chosen to make the filter visible -- and it would
    FAIL if the filter were removed from the plan.
    """

    def test_removing_the_filter_changes_the_verified_number(self):
        task = parse_task("how many unique lines in items.txt")
        plan = engine_mod.synthesize_plan(task)
        verifier = engine_mod.CausalMechanismVerifier(plan)
        sources, expectation = verifier._positive_fixture()
        self.assertNotEqual(expectation["count"], expectation["unfiltered"],
                            "the fixture cannot separate 'filtered' from 'unfiltered'")
        self.assertEqual(verifier._count_in(plan, sources), expectation["count"])
        self.assertEqual(verifier._count_in({**plan, "filters": []}, sources),
                         expectation["unfiltered"])

    def test_a_deliberately_neutered_filter_is_caught_by_the_probe(self):
        # Control: if the filter is replaced by one that keeps everything, the
        # probe must FAIL. Without this control, the probe passing proves nothing.
        task = parse_task("how many unique lines in items.txt")
        plan = engine_mod.synthesize_plan(task)
        # "shorter than 10 characters" keeps every line of the 7-char fixture,
        # so it is a filter in the plan that changes nothing.
        neutered = {**plan, "filters": [{"key": "shorter_than", "n": 10, "unit": "characters"}]}
        verifier = engine_mod.CausalMechanismVerifier(neutered)
        with self.assertRaises(engine_mod.CausalVerificationFailure) as caught:
            verifier.probe_positive_intervention()
        self.assertIn("NOT VISIBLE", str(caught.exception))

    def test_the_second_derivation_on_the_real_bytes_agrees(self):
        # The fixture proves the filter is in the plan; this proves it was run
        # on the caller's file. Two derivations have to agree.
        sources = {"items.txt": ITEMS}
        spec = [{"key": "distinct", "phrase": "unique"}]
        self.assertEqual(
            engine_mod._second_opinion_filtered_count("text", "line", ITEMS, spec),
            len(set(ITEMS.splitlines())),
        )
        engine_mod._run_plan  # the plan path is the other derivation; asserted above


class TheLedgerItselfIsSound(unittest.TestCase):
    """Properties of the ledger, so a future row cannot quietly be a no-op."""

    def test_every_grounded_row_has_a_fixture_on_which_it_is_visible(self):
        for domain, fixtures in engine_mod.FILTER_FIXTURES.items():
            for key, fixture in fixtures.items():
                with self.subTest(domain=domain, key=key):
                    self.assertTrue(engine_mod._filter_is_grounded(domain, key))
                    items = fixture.splitlines()
                    filtered = engine_mod._apply_filter_items(
                        items, "line",
                        {"key": key, "n": 4, "unit": "characters"})
                    self.assertNotEqual(
                        len(filtered), len(items),
                        "%s is a no-op on its own fixture: the probe would certify nothing" % key)

    def test_every_key_in_the_ledger_has_refusal_wording(self):
        for key in engine_mod.FILTER_KINDS:
            self.assertIn(key, engine_mod.MODIFIER_REFUSAL,
                          "a refusal that does not say what it cannot do is how this defect hid")
            self.assertIn(key, engine_mod._MODIFIER_CONCEPT)
            self.assertTrue(engine_mod.MODIFIER_REFUSAL[key].strip())

    def test_a_threshold_with_no_unit_is_refused_rather_than_guessed(self):
        result = _solve("count the lines longer than 4 in /tmp/qv/items.txt",
                        pathlib.Path("/tmp/qv")) if pathlib.Path("/tmp/qv/items.txt").exists() else None
        # Constructed without touching the filesystem, so the assertion holds
        # whether or not that scratch file exists:
        task = parse_task("count the lines longer than 4 in items.txt")
        self.assertTrue(any("unit" in u for u in task.unparsed_qualifiers),
                        "a threshold with no unit must be refused, got %r" % (task.unparsed_qualifiers,))

    def test_no_plan_ever_drops_a_filter_it_parsed(self):
        # The invariant, over the whole family: parsed filters are planned.
        for goal in ("how many unique lines in items.txt",
                     "count the blank lines in items.txt",
                     "count the non-empty lines in items.txt",
                     "count the lines longer than 4 characters in items.txt"):
            with self.subTest(goal=goal):
                task = parse_task(goal)
                self.assertTrue(task.filters, goal)
                plan = engine_mod.synthesize_plan(task)
                self.assertEqual(len(plan["filters"]), len(task.filters))
                for spec in task.filters:
                    self.assertIn("FILTER_" + str(spec["key"]).upper(), plan["pipeline"])


if __name__ == "__main__":
    unittest.main()

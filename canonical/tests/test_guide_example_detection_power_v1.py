"""What this round got wrong first, and the two numbers that must never drift nicer.

The failures, in the order they happened:

  1. **A mutated module compiled from `ast.unparse` renumbers every line.** The branch cross-tab
     then matched mutation sites against the *original* source's line numbers and reported
     `guide_reached: 0` on all sixteen functions -- a clean-looking result that meant nothing.
     The first test asserts the control module keeps the original line numbers, so a branch the
     guide enters is actually seen as entered.

  2. **A corpus built from the documented argument cannot test the documented example.** The
     first version perturbed the example's own arguments. The guide then scored 88% because the
     fault set was centred on the very input the guide checks. The second test asserts the random
     corpus contains none of the documented calls.

  3. **Boundary inputs were handed back as bare tuples** while the caller unpacked pairs, so the
     guard search crashed on the two modules that had untested branches. The third test asserts
     the shape.

And the measurements that must not drift into a friendlier form:

  * the guide's power is a fraction strictly between 0 and 1 -- a report of 1.0 would mean no
    fault was ever separated outside the documented input, which the witness rows contradict;
  * at least half of the decision branches the examples never enter are still unreached, i.e.
    the guide is not a coverage instrument;
  * the faults the guide misses are **constant** mutations, not operator swaps. If a later edit
    ever makes operator swaps the misses, the mechanism story in the report is wrong.
"""
from __future__ import annotations

import ast
import json
import pathlib
import random
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import guide_example_detection_power_v1 as subject  # noqa: E402

RECEIPT = REPO / "canonical/verification/GUIDE_EXAMPLE_DETECTION_POWER_20261127_V1.json"

FIXTURE = '''\
"""A receiver with one documented example, one guard, and nothing else."""


def double(value):
    """Twice the value.

    >>> double(3)
    6
    """
    if value < 0:
        raise ValueError("negative")
    return value * 2


def sign(value):
    """Report the sign.

    >>> sign(-2)
    'negative'
    """
    if value < 0:
        return "negative"
    return "other"


def classify(values):
    """Sort and report the middle.

    >>> classify([1, 3, 5])
    3
    >>> classify([1, 3, 5, 7])
    3
    """
    if not values:
        raise ValueError("empty")
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]
'''


TREE = ast.parse(FIXTURE)


def _function(name):
    return next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == name)


@pytest.fixture()
def fixture_module():
    return subject._materialize("spot_check_fixture_v1", FIXTURE, "<fixture>")


def test_the_control_keeps_the_original_line_numbers():
    """Bug 1: an unparsed control renumbers lines and silently empties the branch cross-tab."""
    module = subject._materialize("line_numbers_fixture_v1", FIXTURE, "<fixture>")
    function = _function("sign")
    examples = subject.usable_examples(module, "sign", subject._doc_examples(function))
    assert examples, "the fixture's example must run before line numbers mean anything"
    spans = subject.branch_spans(function)
    lines = subject.traced_lines(getattr(module, "sign"), lambda: subject._run_examples(module, "sign", examples))
    assert spans, "sign has one guard"
    reached = [span for span in spans if any(span["start"] <= line <= span["end"] for line in lines)]
    assert reached, "sign(-2) enters the then-branch; an unparsed control renumbers it away"
    assert min(lines) >= function.lineno, (min(lines), function.lineno)


def test_the_random_corpus_never_replays_a_documented_call(fixture_module):
    """Bug 2: a corpus centred on the example measures the example against itself."""
    function = _function("double")
    examples = subject._doc_examples(function)
    documented = {repr(call) for call in subject._documented_calls(examples[0], "double")}
    assert documented == {repr(((3,), {}))}
    corpus = subject.random_corpus("double", examples, random.Random(0), count=20)
    assert len(corpus) >= 12
    assert repr(((3,), {})) not in {repr(call) for call in corpus}


def test_boundary_inputs_are_call_pairs(fixture_module):
    """Bug 3: bare tuples made the guard search crash on exactly the modules that needed it."""
    function = _function("classify")
    pairs = subject.boundary_inputs("classify", subject._doc_examples(function), extra=[])
    assert pairs and all(isinstance(pair, tuple) and len(pair) == 2 for pair in pairs)
    assert any(args == ([],) for args, _ in pairs), "the empty list is the guard's own boundary"


def test_the_lattice_reaches_the_guard_the_example_never_enters(fixture_module):
    """The constructive half: name the unknown and give the input that reaches it."""
    function = _function("classify")
    examples = subject.usable_examples(fixture_module, "classify", subject._doc_examples(function))
    spans = subject.branch_spans(function)
    lines = subject.traced_lines(
        getattr(fixture_module, "classify"),
        lambda: subject._run_examples(fixture_module, "classify", examples),
    )
    reached = [span for span in spans if any(span["start"] <= line <= span["end"] for line in lines)]
    untested = [span for span in spans if span not in reached]
    assert untested, "the documented input is non-empty, so the empty guard cannot be entered"
    found = subject.reach_guards(getattr(fixture_module, "classify"), examples, spans, reached, [])
    assert found, "the boundary lattice must reach the empty-input guard"
    assert found[0]["input"].startswith("(([],)"), found


def test_two_faults_in_one_function_get_opposite_verdicts(fixture_module):
    """The whole point: `double(3) == 6` catches `2 -> 3` and cannot catch `value < 0` becoming `value < 1`."""
    function = _function("double")
    examples = subject.usable_examples(fixture_module, "double", subject._doc_examples(function))
    verdicts = {}
    for mutation in subject.candidate_mutations(function):
        mutated = subject._materialize(
            "spot_check_fixture_v1", ast.unparse(subject.mutate_function(TREE, "double", mutation)), "<fixture>"
        )
        verdicts[mutation.label] = subject._run_examples(mutated, "double", examples)["killed"]
    assert verdicts.get("const:2->3") is True, verdicts
    assert verdicts.get("const:0->1") is False, verdicts


def test_the_receipt_reports_a_fraction_and_keeps_its_denominator():
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    tally = report["tally"]
    assert 0 < tally["guide_detection_power"] < 1
    assert tally["separated"] < tally["mutants"], "some mutants must remain unseparated; the corpus is bounded"
    assert tally["guide_kills"] == sum(1 for m in report["modules"] for row in m["rows"] if row["separated"] and row["guide_killed"])


def test_the_guide_does_not_cover_two_thirds_of_the_decision_branches():
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    guards = report["tally"]["guards"]
    assert guards["branches"] >= 20
    assert guards["unreached_share"] > 0.5, guards
    assert 0 < guards["witnessed"] < guards["untested"], "the lattice reaches some, not all, unseen guards"


def test_constant_faults_escape_far_more_often_than_operator_faults():
    """A boundary fault moves a number; an operator fault changes the shape of the answer."""
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = [row for m in report["modules"] for row in m["rows"] if row["separated"]]
    const = [row for row in rows if row["mutation"].startswith("const:")]
    other = [row for row in rows if not row["mutation"].startswith("const:")]
    const_missed = sum(1 for row in const if not row["guide_killed"])
    other_missed = sum(1 for row in other if not row["guide_killed"])
    assert len(const) >= 20 and len(other) >= 40
    assert const_missed >= 10
    assert const_missed / len(const) > 5 * max(other_missed / len(other), 0.005)
    assert all("witness" in row for row in const + other if not row["guide_killed"]), "a miss without a call is not evidence"

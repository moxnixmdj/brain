"""The three mistakes this round made, held so they cannot come back.

Each test is a real failure from the build, in the order it happened:

  1. **A Python file was read with the markdown fence reader.** Six stdlib guides produced zero
     transcripts and the round nearly reported "the guides contain no examples". Python marks a
     literal block with `::` and an indent; it has no fences. The first test asserts that a source
     file and a README are read by different readers, and that the source one finds examples.

  2. **The expected output swallowed the prose after the example.** At module level the prompt, the
     answer and the following paragraph all sit at indent 0, so no rule over indentation can
     separate them -- and the `\"\"\"` that closes the docstring ended up inside the expected output.
     The fix was `ast`: it knows where a docstring ends. The second test asserts the expected output
     of a module-level doctest contains no prose and no docstring delimiter.

  3. **A doctest was replayed in a fresh namespace.** 39 examples were refused with
     `name 'mean' is not defined` when `mean` was in scope for the guide. `doctest.testmod` runs a
     module's docstring with `vars(module)` as globals; the third test asserts the replay does too.

And one measurement that must not drift into a friendlier form: **the checkable share of the
documentation is small.** The last test asserts it is under a quarter and over zero, because a
receipt that reported 100% would mean the round had started counting prose as execution.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import the_guide_is_a_test_suite_v1 as subject  # noqa: E402

RECEIPT = REPO / "canonical/verification/THE_GUIDE_IS_A_TEST_SUITE_20261204_V1.json"


@pytest.fixture(scope="module")
def receipt():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_every_declared_gate_holds(receipt):
    gates = receipt["verdict"]
    assert len(gates) == 7, sorted(gates)
    unmet = [name for name, row in gates.items() if not row["MET"]]
    assert not unmet, unmet


def test_a_source_file_and_a_readme_are_read_by_different_readers():
    """Mistake 1: the fence reader was used for Python source and found nothing."""
    import sysconfig

    stdlib = pathlib.Path(sysconfig.get_paths()["stdlib"])
    source = stdlib / "textwrap.py"
    if not source.exists():
        pytest.skip("no stdlib source on this machine")
    blocks = subject.guide_blocks("stdlib:textwrap", source)
    assert blocks, "the source reader found no docstring with a transcript"
    assert subject.docstring_blocks(source), "docstring_blocks returned nothing"
    # and the fence reader must not be what found them
    assert subject.fenced_blocks(source.read_text(errors="replace")) == []


def test_expected_output_of_a_module_doctest_is_the_answer_and_not_the_prose(receipt):
    """Mistake 2: prose and the closing triple-quote were counted as the command's output."""
    rows = receipt["examples"]["rows"]
    for row in rows:
        if not row.get("want"):
            continue
        joined = " ".join(row["want"])
        assert '"""' not in joined, row
        # a sentence of explanation is longer than any answer this corpus states
        assert not any(len(line) > 120 for line in row["want"]), row


def test_a_doctest_is_replayed_in_the_modules_own_namespace(receipt):
    """Mistake 3: 39 examples were refused for a name that the guide had in scope."""
    assert receipt["examples"]["refused_by_the_interpreter"] < receipt["examples"]["examples"]
    matched = receipt["examples"]["matched"]
    assert matched >= 100, matched
    # statistics' docstring writes `mean(...)`, never `statistics.mean(...)`; a replay in a fresh
    # namespace cannot match those, so the match count itself is the evidence
    statistics_hits = [row for row in receipt["examples"]["matched_rows"]
                       if row["guide"] == "stdlib:statistics"]
    assert statistics_hits, "no statistics example matched, so the namespace fix is gone"


def test_a_guide_contains_very_little_that_a_run_can_confirm(receipt):
    """The number the round's answer to the owner's question rests on."""
    totals = receipt["seam"]["totals"]
    assert totals["bytes"] > 100_000
    assert 0 < totals["checkable_share"] < 0.25, totals
    # and the prose is the majority, which is the finding
    assert totals["prose_bytes"] > totals["checkable_bytes"] * 3


def test_a_matched_example_separates_a_machine_made_wrong_input(receipt):
    """The guide's printed output is a check, not decoration."""
    decoys = receipt["decoys"]
    assert decoys["mutants"] >= 20, decoys["mutants"]
    assert decoys["separated"] > decoys["blind"], decoys
    # and the round must say how many mutants were equivalent by construction rather than
    # counting them as blindness
    assert "equivalent_unseparable" in decoys
    assert decoys["separated"] + decoys["equivalent_unseparable"] <= decoys["mutants"]


def test_the_store_admits_only_what_three_tests_allow(receipt):
    kept = receipt["kept"]
    assert kept["admitted"], "nothing was admitted, so the store contract is untested"
    for rule in kept["admitted"]:
        assert all(rule["tests"].values()), rule
    for rule in kept["refused"]:
        assert not all(rule["tests"].values()), rule
    assert kept["stored_bytes"] > 0


def test_a_rule_that_transferred_was_checked_on_inputs_no_guide_contains(receipt):
    transfer = receipt["transfer"]
    assert transfer["instances"] >= 2
    assert transfer["property_holds"] >= 1
    # the held-out inputs must not appear in any guide that was read
    for row in transfer["rows"]:
        for value in row["held_out"]:
            if isinstance(value, str):
                for guide in subject.default_guides().values():
                    if not guide.exists():
                        continue
                    assert value not in guide.read_text(errors="replace"), (value, guide)


def test_zero_model_calls_zero_parameters_zero_network(receipt):
    cost = receipt["cost"]
    assert cost["model_calls"] == 0
    assert cost["parameters_stored"] == 0
    assert cost["network_calls_at_run_time"] == 0


# --------------------------------------------------------------------------------------------------
# The circuit the round closed: `perfect_algorithm_v1.run()` used to fetch instant knowledge and then
# return `OPEN__NO_PLAN_AFTER_SCAN` unconditionally. These tests hold the wire in place, and they
# hold its four refusals too -- a path that can only succeed is the mistake this project keeps
# paying for.
# --------------------------------------------------------------------------------------------------

from canonical.swe_kernel import perfect_algorithm_v1 as algorithm  # noqa: E402

GOOD_DOCUMENT = """
    >>> statistics.median([2, 3, 4, 5])
    3.5
    >>> statistics.median([9, 1, 5])
    5
"""


def test_a_fetched_document_becomes_a_plan_only_through_its_own_printed_output():
    result = algorithm._plan_from_document(GOOD_DOCUMENT, ["statistics.median([1])"], "median")
    assert result["status"] == "PASS__PLAN_FROM_A_DOCUMENT", result
    assert result["plan"] == ["statistics.median([2, 3, 4, 5])", "statistics.median([9, 1, 5])"]
    assert "EXTERNAL_DOCUMENT" in result["authority"], result


def test_a_document_whose_printed_answer_is_wrong_plans_nothing():
    """The oracle is the document's own output. A transcript that does not reproduce it is not a
    plan, and this is the difference between reading a guide and trusting a guide."""
    wrong = "\n    >>> statistics.median([2, 3])\n    99\n"
    result = algorithm._plan_from_document(wrong, ["statistics.median([1])"], "median")
    assert result["status"] == "REFUSED__NOTHING_REPRODUCED_THE_DOCUMENTS_OUTPUT", result


def test_a_matched_command_outside_the_plan_space_is_seen_and_not_planned():
    """Documentation says what EXISTS on the machine, never what this call may DO."""
    result = algorithm._plan_from_document(GOOD_DOCUMENT, ["unrelated_program --flag"], "median")
    assert result["status"] == "REFUSED__NOTHING_MATCHED_INSIDE_THE_PLAN_SPACE", result
    assert result["seen_not_permitted"], result
    assert "plan" not in result or not result.get("plan")


def test_prose_with_no_transcript_is_refused_before_anything_is_run():
    result = algorithm._plan_from_document("Requests is a simple, yet elegant HTTP library.",
                                           ["x"], "g")
    assert result["status"] == "REFUSED__NO_TRANSCRIPT_IN_THE_DOCUMENT", result


def test_the_run_loop_reports_which_gate_refused_instead_of_only_opening():
    """`OPEN__NO_PLAN_AFTER_SCAN` must now carry the reason, not just the verdict."""
    import inspect

    source = inspect.getsource(algorithm.run)
    assert "_plan_from_document" in source, "the circuit is not wired into run()"
    assert '"steps"]["document_as_test_suite"]' in source, "the refusal is not reported"

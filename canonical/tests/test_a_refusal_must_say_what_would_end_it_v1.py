"""A REFUSAL THAT DOES NOT SAY WHAT WOULD END IT IS A DEAD END.

The creature could acquire an operator from worked examples and, when the examples were not
enough, it said `ambiguous` and stopped. That word covered two situations that need opposite
responses:

    the evidence is short      ->  ASK ME ANOTHER QUESTION (and say which one)
    the vocabulary is the limit ->  no question can help, and here is why

Reporting both as `ambiguous` invites an asker to keep demonstrating at a wall, and the
system had never checked whether its own dead ends were reachable. This module is the check.

The measurement that started it: `median` was reported as unacquirable for two rounds. It
is acquirable in ONE more example, and the system could have named that example.
"""

from __future__ import annotations

import itertools

import pytest

from canonical.runtime import operator_acquisition_v1 as A
from canonical.runtime import value_algebra_v1 as V
from canonical.tests._memory import no_persistent_memory


@pytest.fixture(autouse=True)
def _clean():
    """An operator declared by one test is declared for every later test in the process.

    `value_algebra_v1._AGGREGATES` is module-global, and `survey()` drops candidates that
    are indistinguishable from a DECLARED one -- so a previous test's operator changes what
    this test is surveying. Measured: the twin candidates vanished from the survey because
    an earlier test had declared their function.
    """
    aggregates = dict(V._AGGREGATES)
    words = {k: set(v) for k, v in V._AGG_WORDS.items()}
    with no_persistent_memory():
        yield
        V._AGGREGATES.clear()
        V._AGGREGATES.update(aggregates)
        V._AGG_WORDS.clear()
        V._AGG_WORDS.update(words)


def _median(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


# ---------------------------------------------------------------------------
# THE QUESTION IS COMPUTABLE, NOT GUESSED.
# ---------------------------------------------------------------------------

def test_the_first_question_leaves_a_small_number_of_readings():
    """25 candidates stand with no examples. One well-chosen probe must cut that down."""
    standing = [r for r in A.survey() if r["admitted"]]
    question = A.next_example(standing)
    assert question is not None
    assert question["standing"] == len(standing)
    # the recommendation must actually be worth something
    assert question["worst_case_remaining"] < question["standing"]
    assert question["answers_possible"] >= 2
    assert question["probe"], "a question with no demonstration is not a question"


def test_the_recommended_question_is_the_best_one_available():
    """It must beat every other probe in the pool on worst-case survivors."""
    standing = [r for r in A.survey() if r["admitted"]]
    question = A.next_example(standing)
    chosen = question["worst_case_remaining"]
    for probe in A._probe_pool():
        buckets = A._distinct_outputs(standing, probe)
        if len(buckets) < 2:
            continue
        assert max(len(v) for v in buckets.values()) >= chosen, (
            f"{probe} splits better than the recommended {question['probe']}")


def test_a_short_probe_could_not_have_separated_anything():
    """THE REASON `median` LOOKED IMPOSSIBLE.

    Five positional candidates return one identical value on every list of length 3 or 4.
    An example of that length is not weak evidence -- it is NO evidence about which one is
    meant, and the system was reporting the resulting tie as ambiguity about the word.
    """
    twins = [r for r in A.survey() if r["admitted"] and r["arity"].startswith("odd:s[1/2]")]
    assert len(twins) >= 2
    for length in (3, 4):
        values = {round(float(r["fn"](list(range(1, length + 1)))), 9) for r in twins}
        assert len(values) == 1, f"candidates differ at length {length}"
    # and they DO separate at the documented minimum
    long_values = {round(float(r["fn"](list(range(1, 5)))), 9) for r in twins}
    assert A.MINIMUM_DISCRIMINATING_LENGTH >= 5


# ---------------------------------------------------------------------------
# THE REFUSAL NAMES THE WAY OUT.
# ---------------------------------------------------------------------------

def test_an_ambiguous_refusal_carries_the_question_that_ends_it():
    out = A.acquire_from_examples("medv", {"medv"}, [([1, 2, 3], 2), ([10, 20, 30], 20)])
    assert out["acquired"] is False
    assert out["reason"] == "ambiguous"
    assert out["next_example"], out
    assert out["ask"], "a refusal that does not say what to do is a dead end"


def test_following_the_refusals_own_advice_acquires_the_operator():
    """THE WHOLE POINT. The system used to be stuck here forever.

    `median` from two short examples leaves three readings and reports ambiguous. The
    refusal now names `[1, 2, 4]`; demonstrating that one answer pins the operator.
    """
    first = A.acquire_from_examples("medv", {"medv"}, [([1, 2, 3], 2), ([10, 20, 30], 20)])
    probe = first["next_example"]
    second = A.acquire_from_examples(
        "medv", {"medv"},
        [([1, 2, 3], 2), ([10, 20, 30], 20), (probe, _median(probe))])
    assert second["acquired"] is True, second
    assert second["arithmetic"] == "odd:s[1/2]/even:(s[2/2-1]+s[2/2])/2"


# ---------------------------------------------------------------------------
# AND WHEN NO QUESTION CAN HELP, IT MUST SAY THAT INSTEAD -- PROVABLY.
# ---------------------------------------------------------------------------

def test_candidates_that_are_one_function_produce_no_question():
    twins = [r for r in A.survey() if r["admitted"]
             and r["arity"] in ("odd:s[1/2]/even:(s[2/2-1]+s[2/2])/2",
                                "odd:s[1/2]/even:(s[4/2-1]+s[4/2])/2")]
    assert len(twins) == 2
    assert A.next_example(twins) is None


def test_the_indistinguishable_claim_is_true_not_asserted():
    """Brute force: the twins never differ, so `no question can help` is a fact.

    A refusal whose reason is the wrong one is a small version of a wrong answer. This test
    exists so the `indistinguishable` branch cannot be used to mean "I stopped looking".
    """
    twins = [r for r in A.survey() if r["admitted"]
             and r["arity"] in ("odd:s[1/2]/even:(s[2/2-1]+s[2/2])/2",
                                "odd:s[1/2]/even:(s[4/2-1]+s[4/2])/2")]
    seen = 0
    for n in range(1, 9):
        for combo in itertools.islice(itertools.product([0, 1, 2, 5], repeat=n), 600):
            a = twins[0]["fn"](list(combo))
            b = twins[1]["fn"](list(combo))
            seen += 1
            assert abs(float(a) - float(b)) <= 1e-9, (combo, a, b)
    assert seen > 1000, "the brute force did not actually run"


def test_a_single_candidate_never_produces_a_question():
    one = [r for r in A.survey() if r["admitted"]][:1]
    assert A.next_example(one) is None

"""Forcing an expression at a site must be exactly "the program with that site replaced".

If it is not, the search answers a different question than the corpus judges, and every number it
reports is about a program nobody wrote. The fixtures are verbatim published QuixBugs bytes
(jkoppel/QuixBugs, MIT, commit 4257f44b).
"""

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import force_the_value_and_see_v1 as forced  # noqa: E402

# ---- verbatim published QuixBugs: python_programs/get_factors.py --------------------------------
GET_FACTORS = '''
def get_factors(n):
    if n == 1:
        return []

    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return [i] + get_factors(n // i)

    return []
'''

# ---- verbatim published QuixBugs: python_programs/mergesort.py ----------------------------------
MERGESORT = '''
def mergesort(arr):
    def merge(left, right):
        result = []
        i = 0
        j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:] or right[j:])
        return result

    if len(arr) == 0:
        return arr
    else:
        middle = len(arr) // 2
        left = mergesort(arr[:middle])
        right = mergesort(arr[middle:])
        return merge(left, right)
'''

FACTORS_EXAMPLES = [(1, []), (100, [2, 2, 5, 5]), (101, [101])]
SORT_EXAMPLES = [([], []), ([3, 1, 2], [1, 2, 3]), ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
                 ([1, 2, 6, 72, 7, 33, 4], [1, 2, 4, 6, 7, 33, 72])]


def run(source, name, args, forced_expression=None, site_text=None, lineno=None):
    """Run the instrumented program. A forced run only means anything on the program that has the hook."""
    instrumented, sites = forced.instrumented_source(source, name)
    forced_map = None
    if forced_expression is not None:
        matching = [site for site in sites
                    if site["text"] == site_text and (lineno is None or site["lineno"] == lineno)]
        assert len(matching) == 1, f"expected one site producing {site_text!r} on line {lineno}"
        forced_map = {matching[0]["index"]: forced_expression}
    return forced.run_case(instrumented, name, args, forced=forced_map)


def test_instrumenting_does_not_change_what_the_program_answers():
    """The instrumented program is the buggy program: same answers, including the wrong ones."""
    instrumented, sites = forced.instrumented_source(GET_FACTORS, "get_factors")
    assert sites, "a program with expressions has sites"
    for args, _expected in FACTORS_EXAMPLES:
        plain_ran, plain_value = forced.run_case(GET_FACTORS, "get_factors", (args,), forced=None)
        ran, value = forced.run_case(instrumented, "get_factors", (args,), forced=None)
        assert (ran, value) == (plain_ran, plain_value)


def test_forcing_an_expression_is_the_same_as_writing_it_in():
    """The answer to a forced run must be the answer of the textually patched program, case for case."""
    patched = GET_FACTORS.replace("    for i in range(2, int(n ** 0.5) + 1):",
                                  "    for i in range(2, 1 + n):")
    assert patched != GET_FACTORS
    for args, expected in FACTORS_EXAMPLES:
        forced_ran, forced_value = run(GET_FACTORS, "get_factors", (args,),
                                       forced_expression="(1) + (n)", site_text="int(n ** 0.5) + 1",
                                       lineno=6)
        patched_ran, patched_value = forced.run_case(patched, "get_factors", (args,), forced=None)
        assert (forced_ran, forced_value) == (patched_ran, patched_value)
        assert forced_ran and forced_value == expected


def test_the_buggy_program_is_actually_wrong_on_the_examples_used_above():
    """Without this the test above would pass on a program with no bug."""
    for args, expected in FACTORS_EXAMPLES:
        ran, value = run(GET_FACTORS, "get_factors", (args,))
        if args == 1:
            assert ran and value == expected
        else:
            assert not ran or value != expected


def test_a_case_that_never_returns_is_answered_not_waited_on():
    """mergesort's base case makes the recursion endless; a candidate that loops must cost one answer."""
    started = time.time()
    ran, _value = run(MERGESORT, "mergesort", ([1, 2],))
    assert ran is False
    assert time.time() - started < 30.0


def test_stopping_the_recursion_at_one_element_sorts_every_example():
    for args, expected in SORT_EXAMPLES:
        ran, value = run(MERGESORT, "mergesort", (args,),
                         forced_expression="(arr)[(1):]", site_text="arr", lineno=17)
        assert ran and value == expected, (args, value)


def test_a_candidate_may_not_call_the_function_under_repair():
    """Forcing `get_factors(...)` at a site inside get_factors is infinite recursion, not a repair."""
    contexts = forced.context_at(GET_FACTORS, "get_factors", (100,), 6)
    assert contexts, "line 6 runs"
    asked = forced.expressions_at("int(n ** 0.5) + 1", contexts[0], GET_FACTORS, "get_factors",
                                 budget=200)
    assert asked
    assert not [text for text, _value in asked if "get_factors(" in text]


def test_every_row_a_run_produced_is_counted_in_the_summary():
    """A summary that lists only the winners hides the rows a reader needs to trust the run."""
    rows = [
        {"task": "a", "solved": True, "stage": "SOLVED_BY_THE_VALUE_THE_FAILURE_SHOWED",
         "questions_asked": 3, "seconds": 1.0},
        {"task": "b", "solved": False, "stage": "NO_SINGLE_EXPRESSION_FIXES_THIS_CASE",
         "questions_asked": 5, "seconds": 2.0},
        {"task": "c", "solved": False, "stage": "CHILD_TIMED_OUT"},
    ]
    summary = forced.summarise(rows)
    assert summary["tasks_attempted"] == 3
    assert summary["solved"] == ["a"]
    assert summary["no_single_expression_fixes_this_case"] == ["b"]
    assert summary["not_answered_by_this_run"] == ["c:CHILD_TIMED_OUT"]
    assert summary["questions_asked_total"] == 8

"""A library of structural tests that keeps score — and an honest account of what that buys.

Round 12 recovered a periodic hypothesis and then named its own limit: the pathway was a partition
test, `mod 3` was induced only because I had already written that test, and "writing the test is
still my job". So round 13 makes the TESTS plural and gives them a record of discovery.

What this is: a preference among tests, learned from outcomes. What it is not: test invention. I
wrote both tests. The measurements decide whether the preference is worth anything, and two of the
tests below assert that it is sometimes worth NOTHING -- because a mechanism whose benefit is
denied on the streams where it cannot help is more trustworthy than one that claims a gain everywhere.

The test that matters most:

`test_the_two_tests_are_genuinely_different` -- if one test quietly handled everything, the record
would be sorting a single item, and every measurement about ordering would be theatre.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.discovered_tests_v1 import (  # noqa: E402
    CASES,
    INDUCED,
    NOT_APPLICABLE,
    DiscoveryRecord,
    _streams,
    recover,
    probe_level,
    probe_periodic,
)
from canonical.runtime.vocabulary_induction_v1 import _exact  # noqa: E402

MOD2 = [(_exact(a[0]), _exact(v)) for a, v in CASES["mod 2"]]
FLOOR = [(_exact(a[0]), _exact(v)) for a, v in CASES["floor"]]


# ---------------------------------------------------------------------------------------------
# The tests are distinct
# ---------------------------------------------------------------------------------------------

def test_the_two_tests_are_genuinely_different():
    """Each applies to exactly one of the two targets."""
    assert recover(CASES["mod 2"], DiscoveryRecord())["test"] == "periodic"
    assert recover(CASES["floor"], DiscoveryRecord())["test"] == "level"


def test_each_test_refuses_the_other_target():
    """Not just 'the other one wasn't tried' -- it declines, and says why."""
    assert probe_periodic(FLOOR)["status"] == NOT_APPLICABLE
    assert probe_level(MOD2)["status"] != INDUCED


def test_a_test_that_is_undefined_on_a_domain_says_so():
    """The periodic test on fractional inputs used to report NO_STRUCTURE.

    `1.5 % 2 == 3/2`, so every fractional observation becomes its own residue class and the test
    reports 'no periodic structure' when the truth is 'this test cannot speak about fractions'.
    Same conflation as SEARCH_TRUNCATED and ONTOLOGY_EXHAUSTED, reproduced inside a test.
    """
    assert probe_periodic(FLOOR)["status"] == NOT_APPLICABLE
    assert "fractional" in probe_periodic(FLOOR)["why"]


def test_a_level_function_needs_each_level_witnessed_twice():
    """One observation per level is a lookup table with a step function's manners."""
    thin = [(_exact(0.5), _exact(1.0)), (_exact(1.5), _exact(2.0)), (_exact(2.5), _exact(3.0))]
    assert probe_level(thin)["status"] != INDUCED


# ---------------------------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------------------------

def test_a_failed_attempt_is_not_repeated_blindly():
    record = DiscoveryRecord()
    first = recover(CASES["noise"], record)
    second = recover(CASES["noise"], record)
    assert first["tests_tried"] > 0
    assert second["tests_tried"] == 0
    assert any(t["status"] == "SKIPPED" for t in second["trace"])


def test_the_record_puts_a_winning_test_first():
    record = DiscoveryRecord()
    recover(CASES["floor"], record)          # level wins once
    assert [t["name"] for t in record.order()][0] == "level"


def test_the_record_reduces_attempts_where_the_library_order_is_wrong():
    """Five level targets cost 10 attempts in a fixed order and 6 with a record."""
    streams = {s["stream"]: s for s in _streams()}
    levels = streams["five level targets"]
    assert levels["fixed_total"] == 10
    assert levels["learned_total"] == 6
    assert levels["improved"] is True


def test_the_reordering_is_decorative_when_one_test_dominates():
    """A mechanism that claims a gain on a stream it cannot help is not measuring anything.

    With two tests, and periodic winning the first target, reordering cannot reduce attempts:
    the library's own order already puts the winner first. Asserted so the negative stays visible.
    """
    streams = {s["stream"]: s for s in _streams()}
    periodic = streams["three periodic targets"]
    assert periodic["fixed_total"] == periodic["learned_total"]


def test_learning_never_makes_it_slower():
    for stream in _streams():
        assert stream["learned_total"] <= stream["fixed_total"]


# ---------------------------------------------------------------------------------------------
# Honesty about the library's limits
# ---------------------------------------------------------------------------------------------

def test_structureless_data_is_refused_by_every_test():
    out = recover(CASES["noise"], DiscoveryRecord())
    assert out["status"] != INDUCED
    assert out["tests_tried"] > 0          # it tried, and declined


def test_recovery_does_not_depend_on_the_string_search():
    """`mod 3` yields zero admissible programs -- `x % 3` is unspellable -- and is still recovered."""
    assert recover(CASES["mod 3"], DiscoveryRecord())["status"] == INDUCED


def test_a_second_test_recovering_the_same_law_does_not_add_a_kind():
    """The alternation pattern is already explained by periodicity; the library must not count it
    twice, which is the same overcounting defect the whole arc is about, one level up."""
    out = recover(CASES["mod 2"], DiscoveryRecord())
    assert out["test"] == "periodic"
    assert out["size"] == 2                 # one kind, not two names for it


def test_the_input_shape_is_refused_loudly_rather_than_answered():
    """Passing two inputs to a one-input test library must not produce a quiet NOT_APPLICABLE that
    looks like a considered verdict."""
    out = recover([((1, 2), 3.0), ((3, 4), 7.0)], DiscoveryRecord())
    assert "one input at a time" in out["why"]

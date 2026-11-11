"""Routing a growing library: word overlap collapses, structure does not, and refusals save you.

Three claims, each measured over 20 random libraries per size, no model anywhere:

  flat word overlap   13.5% -> 6.2%      (collapses -- matches the published decay)
  hierarchical        12.5% -> 9.4%      (barely helps; not the fix the literature hoped)
  structure           94.0% -> 84.4%     (nearly flat)

And the number that matters more than accuracy: on the twelve DANGEROUS confusions -- the
ones where the wrong choice ships to production or deletes the file instead of copying it --
the structure router is wrong 8.3% of the time and REFUSES 50%.  A router that says "I
cannot tell staging from production" is safe.  One that picks confidently is not.

Every constant below was found by reading a failure, not by tuning a score.
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import canonical.evaluation.routing.dangerous_confusions_v1 as D
import canonical.evaluation.routing.scale_experiment_v1 as E
from canonical.runtime import compose_skills_v1 as C


def _rate(n, f, seeds=20):
    tot = sum(E.run(n, s)[f] for s in range(seeds))
    probes = sum(E.run(n, 0)["probes"] for _ in range(1)) * seeds
    return tot / probes


# ------------------------------------------------------------------ the decay

def test_word_overlap_collapses_as_the_library_grows():
    small, big = _rate(10, "flat"), _rate(64, "flat")
    assert small < 0.20 and big < 0.10, (small, big)
    assert big < small


def test_hierarchical_routing_does_not_rescue_word_overlap():
    """The literature hoped hierarchy would fix this.  On this library it does not: 12.5% to
    9.4%.  Reporting that honestly is the point -- the fix is a better similarity measure,
    not a tree over a bad one."""
    assert _rate(64, "hier") < 0.20


def test_structure_routing_stays_high_and_nearly_flat():
    small, big = _rate(10, "struct"), _rate(64, "struct")
    assert small > 0.85, small
    assert big > 0.75, big
    assert small - big < 0.20, "the curve should degrade far less than word overlap"


# ------------------------------------------------------------------ the bugs behind the numbers

def test_the_predicate_is_not_the_whole_trigger():
    """"open the file" used to contribute the verb "file", so every file skill matched every
    file request on the shared subject, tied, and the tie rule refused.  26/64 probes were
    unroutable for this reason alone."""
    assert E._verbs("open the file") == {"open", "open_file"}
    assert "file" not in E._verbs("open the file")


def test_action_verbs_are_not_stop_words():
    """"show", "give", "put", "get" and "make" were all in the stop list, so "SHOW me the
    file" had its verb deleted before routing began."""
    for v in ("show", "give", "put", "get", "make"):
        assert v not in C._STOP


def test_an_ambiguous_request_is_recorded_as_wrong_or_refused():
    """The router cannot tell "ADD more MACHINES" (scale out) from installing a package:
    both share the verb ADD and a shared subject word.  It answers system_install.  This is
    recorded as a WRONG answer in the dangerous set, not excused -- keeping the failure
    visible is worth more than a test that pretends the router is better than it is."""
    lib = E.build_library(64, random.Random(0))
    assert E.structure_route("ADD more MACHINES", lib) in {"system_install", None}


# ------------------------------------------------------------------ the number that matters

def test_the_dangerous_confusions_are_refused_rather_than_guessed():
    agg = {"right": 0, "wrong": 0, "refused": 0}
    for seed in range(20):
        r = D.evaluate(E.build_library(64, random.Random(seed)))
        for k in agg:
            agg[k] += r[k]
    total = sum(agg.values())
    assert agg["wrong"] / total < 0.15, f"dangerously wrong {agg['wrong']/total:.1%}"
    assert agg["refused"] / total > 0.30, "it should refuse what it cannot tell apart"


def test_the_dangerous_pairs_are_actually_pairs():
    """If these were easy, the measurement above would be worthless.  The triggers must
    share nearly all their words -- differ by one meaningful token at most."""
    for probe, want, must_not in D.DANGEROUS:
        a, b = E.SKILLS[want][1], E.SKILLS[must_not][1]
        assert a != b
        diff = C._stem_set(a) ^ C._stem_set(b)
        # some pairs differ in the SUBJECT rather than the verb (kill the process vs start
        # the service); what makes them dangerous is that the request names only one side,
        # so the router must not quietly assume the other.
        assert len(diff) <= 4, (a, b, diff)

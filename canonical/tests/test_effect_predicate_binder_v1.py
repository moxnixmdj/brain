"""Pins the binder: an effect is chosen by execution, and only the effect may be stored.

These tests exist because the first build of this instrument was wrong in four
specific, repeatable ways, and each one is a trap any successor will fall into:

1. It bound `SortedList.add` to "sorted and unique", because a sorted *list* keeps the
   duplicate.  Caught by requiring the goal's predicate, not a plausible-looking output.
2. It bound a hash set to "sorted", because for small integers Python's hash order and
   sort order coincide.  Caught by a battery member where they disagree.
3. It accepted the first constructor that merely *constructed*.  `PSet([3,1,2])`
   builds an object that stores the list unbuilt; only calling the operation reveals it.
4. It called two bindings "ambiguous" when one merely worked on fewer inputs.  Caught
   by dominance over the battery instead of equality of verdict.

The tests below are written against a fixture package generated here, so they do not
touch the network and cannot be satisfied by a lucky download.
"""
from __future__ import annotations

import json
import pathlib
import sys
import textwrap

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import effect_predicate_binder_v1 as epb  # noqa: E402


# --- a fixture artifact with the exact traps the instrument must survive ------------

FIXTURE = {
    "__init__.py": textwrap.dedent('''
        from .impl import SortedBag, InsertOrderedSet, HashSet, BrokenBuilder
        __all__ = ["SortedBag", "InsertOrderedSet", "HashSet", "BrokenBuilder"]
    '''),
    "impl.py": textwrap.dedent('''
        class SortedBag:
            """A sorted multiset that keeps duplicates."""
            def __init__(self, values=()):
                self._v = sorted(values)
            def add(self, value):
                self._v = sorted(self._v + [value])
            def __iter__(self):
                return iter(self._v)

        class InsertOrderedSet:
            """A set ordered by insertion, not by value."""
            def __init__(self, values=()):
                seen, out = set(), []
                for v in values:
                    if v not in seen:
                        seen.add(v); out.append(v)
                self._v = out
            def add(self, value):
                if value not in self._v:
                    self._v.append(value)
            def __iter__(self):
                return iter(self._v)

        class HashSet:
            """A plain hash set: order is whatever the hash table says."""
            def __init__(self, values=()):
                self._v = set(values)
            def add(self, value):
                self._v.add(value)
            def __iter__(self):
                return iter(self._v)

        class BrokenBuilder:
            """Accepts a seed at construction and stores it unbuilt; only .add fails."""
            def __init__(self, values=()):
                self._v = values
            def add(self, value):
                raise AttributeError("'list' object has no attribute 'evolver'")
            def __iter__(self):
                return iter(self._v)
    '''),
}


@pytest.fixture(scope="module")
def libdir(tmp_path_factory):
    root = tmp_path_factory.mktemp("fixturelib")
    for name, src in FIXTURE.items():
        (root / name).write_text(src, encoding="utf-8")
    return str(root)


# --- 1. the surface is read, never imported or trusted ------------------------------

def test_surface_is_pure_text_and_carries_declared_arity(libdir):
    surf = epb.surface(libdir)
    names = set(surf["classes"])
    assert {"SortedBag", "InsertOrderedSet", "HashSet", "BrokenBuilder"} <= names
    bag = next(e for e in surf["entries"] if e["name"] == "SortedBag")
    # values=() has a default, so the class declares zero required slots
    assert bag["ctor"]["required"] == 0
    assert "add" in [m["name"] for m in bag["methods"]]


def test_surface_reports_doctest_census_rather_than_depending_on_it(libdir):
    surf = epb.surface(libdir)
    # the fixture states no examples at all: the instrument must still work
    assert surf["doctests"]["with_examples"] == 0


# --- 2. the battery must be able to tell a hash set from a sorted set --------------

def test_battery_contains_a_member_where_hash_order_differs_from_sort_order():
    spec = epb.compile_goal("sorted_unique")
    battery = epb.build_battery(spec)
    assert battery["can_tell_hash_set_from_sorted_set"] is True
    assert battery["hash_separating_count"] >= 1
    # at least one member must separate the goal from its confusable twin; a battery
    # in which none does cannot decide the goal and must say so
    assert battery["separating_count"] >= 1
    labels = {m["kills"] for m in battery["members"]}
    assert "LIST_VS_SET" in labels


def test_goal_and_its_confusable_are_actually_different_predicates():
    a = epb.compile_goal("sorted_unique")
    b = epb.compile_goal("sorted_unique_with_duplicates")
    seed, insert = [3, 1, 2], 2
    assert a["predicate"](sorted({3, 1, 2, 2}), seed, insert) is True
    assert b["predicate"](sorted({3, 1, 2, 2}), seed, insert) is False


# --- 3. binding is decided by execution against the goal ---------------------------

def test_sorted_unique_binds_the_set_and_rejects_the_bag(libdir):
    report = epb.bind(libdir, "sorted_unique", libname="fixture")
    verdicts = {a["class"] + "." + a["method"]: a["verdict"] for a in report["attempts"]}
    assert verdicts["HashSet.add"] == "NO_EFFECT"       # hash order is not sorted
    assert verdicts["SortedBag.add"] == "NO_EFFECT"     # duplicates survive
    assert verdicts["InsertOrderedSet.add"] == "NO_EFFECT"  # insertion order is not sorted
    # no sorted set exists in this fixture, so the honest answer is a refusal
    assert report["record"] is None


def test_sorted_with_duplicates_binds_the_bag(libdir):
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    verdicts = {a["class"] + "." + a["method"]: a["verdict"] for a in report["attempts"]}
    assert verdicts["SortedBag.add"] == "BOUND"
    assert verdicts["HashSet.add"] == "NO_EFFECT"
    assert report["record"]["binding"] == {
        "module": "impl", "class": "SortedBag", "method": "add",
    }


def test_a_constructor_that_only_constructs_is_not_accepted(libdir):
    report = epb.bind(libdir, "sorted_unique", libname="fixture")
    broken = [a for a in report["attempts"] if a["class"] == "BrokenBuilder"]
    assert broken, "the broken builder must at least be attempted"
    for a in broken:
        assert a["verdict"] == "ERROR"
        assert "evolver" in a["teaches"] or "construct_or_call" in a["teaches"]


def test_an_uncompilable_goal_is_refused_by_name(libdir):
    with pytest.raises(KeyError) as err:
        epb.bind(libdir, "make_the_program_faster")
    assert "UNCOMPILABLE_GOAL" in str(err.value)


# --- 4. the record is an effect, and replay is falsifiable -------------------------

def test_record_carries_the_effect_not_the_action_trace(libdir):
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    rec = report["record"]
    assert rec["effect"]["battery"]["count"] >= 4
    assert rec["effect"]["observations_digest"]
    assert rec["scope"].startswith("this effect on this artifact identity")
    # the record names one call, not a log of everything that was tried
    assert set(rec["binding"]) == {"module", "class", "method"}


def test_store_is_external_addable_and_removable(tmp_path, libdir):
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    rec = report["record"]
    store = epb.Store(tmp_path / "store")
    store.put(rec)
    assert store.keys() == [rec["reuse_key"]]
    assert store.get(rec["reuse_key"])["binding"] == rec["binding"]
    assert store.remove(rec["reuse_key"]) is True
    assert store.keys() == []
    store.put(rec)
    assert len(store.keys()) == 1


def test_replay_succeeds_from_the_record_alone(tmp_path, libdir):
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    store = epb.Store(tmp_path / "store")
    store.put(report["record"])
    replayed = epb.replay(store.get(report["record"]["reuse_key"]), libdir)
    assert replayed["ok"] is True
    assert replayed["derived"] is False
    assert replayed["source"] == "store"


def test_replay_fails_when_the_record_is_tampered(libdir):
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    tampered = json.loads(json.dumps(report["record"]))
    tampered["binding"]["class"] = "HashSet"
    result = epb.replay(tampered, libdir)
    assert result["ok"] is False


# --- 5. ties are resolved by dominance, not by guessing ---------------------------

def test_dominance_prefers_the_binding_that_works_on_the_whole_battery(libdir):
    # SortedBag.add works for every battery member under the duplicates goal; a
    # narrower binding must never displace it.
    report = epb.bind(libdir, "sorted_unique_with_duplicates", libname="fixture")
    assert report["distinct_effects"] == 1
    assert report["ambiguous"] is False
    bound = report["record"]["binding"]["class"]
    assert bound == "SortedBag"

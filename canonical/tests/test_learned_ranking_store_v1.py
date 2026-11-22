#!/usr/bin/env python3
"""Tests for the learned ranking store.

The properties worth pinning are the ones that make this legal and honest:

  * the features are pure functions of text -- nothing is stored, no world facts;
  * the store survives a save/load round trip in a fresh process;
  * deletion really removes the behaviour (fails closed, never silently re-learns);
  * a corrupted store degrades to "no weights" rather than raising in the middle of a run;
  * ranking is deterministic.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))

import learned_ranking_store_v1 as L  # noqa: E402

CORPUS = {
    "sympy.functions.totient": "Calculate the Euler totient function phi(n).",
    "sympy.functions.primepi": "Represents the prime counting function pi(n).",
    "sympy.functions.mobius": "Mobius function maps natural number to {-1, 0, 1}.",
    "sympy.core.symbol.Symbol": "A symbol in a symbolic expression.",
}

WEIGHTS = {"coverage": 1.0, "doc_overlap": 1.0, "stub_hit": 0.0, "depth": 1.0}


def test_features_are_pure_and_deterministic():
    a = L.features("sympy.functions.totient", "compute the euler totient",
                   CORPUS["sympy.functions.totient"], "custom_totient")
    b = L.features("sympy.functions.totient", "compute the euler totient",
                   CORPUS["sympy.functions.totient"], "custom_totient")
    assert a == b
    assert set(a) == set(L.FEATURES)
    assert 0.0 <= a["coverage"] <= 1.0
    assert a["depth"] <= 0.0


def test_name_words_splits_snake_and_camel():
    assert "totient" in L.name_words("sympy.functions.totient")
    assert {"jacobi", "symbol"} <= L.name_words("sympy.functions.jacobi_symbol")
    assert {"rigid", "body"} <= L.name_words("sympy.physics.mechanics.RigidBody")


def test_rank_prefers_the_name_the_problem_speaks_of():
    ranked = L.rank(CORPUS, "compute the euler totient of n", "custom_totient", WEIGHTS)
    assert ranked[0]["name"] == "sympy.functions.totient"


def test_rank_is_deterministic_across_calls():
    first = [r["name"] for r in L.rank(CORPUS, "prime counting function", "custom_x", WEIGHTS)]
    second = [r["name"] for r in L.rank(CORPUS, "prime counting function", "custom_x", WEIGHTS)]
    assert first == second


def test_store_round_trip_in_a_fresh_process(tmp_path):
    path = tmp_path / "store.json"
    store = L.load(path)
    L.put_weights(store, WEIGHTS, learned_from=["a", "b"], note="test")
    L.save(store, path)
    assert path.exists()

    code = (
        "import sys, json, pathlib;"
        f"sys.path.insert(0, {str(pathlib.Path(__file__).resolve().parent.parent / 'tools')!r});"
        "import learned_ranking_store_v1 as L;"
        f"print(json.dumps(L.get_weights(L.load({str(path)!r}))))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == pytest.approx(WEIGHTS)


def test_deletion_removes_the_behaviour(tmp_path):
    path = tmp_path / "store.json"
    store = L.load(path)
    L.put_weights(store, WEIGHTS)
    L.save(store, path)

    reloaded = L.load(path)
    assert L.get_weights(reloaded)["coverage"] == 1.0
    assert L.delete(reloaded) is True
    L.save(reloaded, path)

    emptied = L.load(path)
    assert L.get_weights(emptied) == {k: 0.0 for k in L.FEATURES}
    # a store with no weights ranks nothing: it fails closed rather than guessing
    assert L.rank(CORPUS, "compute the euler totient", "custom_totient", L.get_weights(emptied)) == []


def test_corrupted_store_degrades_to_no_weights(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    store = L.load(path)
    assert L.get_weights(store) == {k: 0.0 for k in L.FEATURES}


def test_missing_store_is_empty_not_an_error(tmp_path):
    store = L.load(tmp_path / "absent.json")
    assert (store.get("entries") or {}) == {}
    assert L.get_weights(store) == {k: 0.0 for k in L.FEATURES}


def test_no_world_facts_are_stored():
    """The store may hold weights and provenance. It may not hold names or facts."""
    store = L.load("/nonexistent/path/store.json")
    L.put_weights(store, WEIGHTS, learned_from=["176"])
    blob = json.dumps(store).lower()
    for forbidden in ("isprime", "totient(", "sympy.", "mobius("):
        assert forbidden not in blob
    assert set((store["entries"]["weights"])["weights"]) == set(L.FEATURES)

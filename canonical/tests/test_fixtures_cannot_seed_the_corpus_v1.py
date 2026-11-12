"""The corpus cannot be seeded from artifacts; it can only be seeded from work.

Round 19 gave receipts their inputs and left the corpus at zero. The obvious seed is the tree's own
fixtures: run each capability that takes a file input against a document already in the repository.
`fixtures_cannot_seed_the_corpus_probe_20261112` does that and counts zero successes.

Pinned:

* 126 of the 145 curated capabilities declare inputs, and 56 of those take a file input — the input
  space is real and broad;
* with every fixture document the tree ships, **zero** capabilities execute to a success status,
  because a document is not an environment: the capability also needs its own packages, roots and
  contracts;
* the probe writes nothing into the tree and does not touch the registry;
* the conclusion is stated, not implied: the corpus comes from real invocations, which is what
  `input_digests` now preserves.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fixtures_cannot_seed_the_corpus_probe_20261112 as probe  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = probe.run()
    return _CACHE["r"]


def test_the_input_space_is_real_and_broad():
    report = _report()
    assert report["registry_capabilities"] == 145
    assert report["declare_inputs"] >= 120
    assert report["take_a_file_input"] >= 50


def test_no_capability_runs_on_a_document_that_happens_to_be_in_the_tree():
    report = _report()
    assert report["executed_to_success_with_an_in_tree_document"] == 0, report["examples_that_ran"]
    assert report["no_valid_instance"] + report["no_adapter"] == report["take_a_file_input"]
    assert report["examples_that_ran"] == []


def test_the_fixture_supply_is_tiny_next_to_the_capability_set():
    report = _report()
    assert 0 < report["fixture_documents_in_tree"] < 50
    assert report["documents_tried_per_capability"] <= report["fixture_documents_in_tree"]


def test_the_probe_writes_nothing_into_the_tree():
    report = _report()
    assert report["writes_into_tree"] is False
    assert report["model_dependency_count"] == 0
    assert report["incremental_spend_usd"] == 0


def test_the_conclusion_is_stated_rather_than_implied():
    report = _report()
    assert "a document is not an instance" in report["why_zero"]
    assert "seeded from work" in report["what_that_leaves"]
    assert any("NO_TRUTH_ACHIEVED" in item for item in report["hard_nonclaims"])

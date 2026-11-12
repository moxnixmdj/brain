"""A generalization set is declared before it is collected, and collected exactly once.

The `fresh` set is the engine's first pre-registered, final-test-once generalization measurement:
sixteen kinds were written into KINDS and pushed before `collect fresh` ran, the collection walked
GitHub's answers mechanically, and the measurement ran once.  These tests pin the protocol, not the
numbers: the declaration exists in code, the collected set exists in the tracked commits file with
a collection timestamp, re-collection refuses, and every measurable kind's teacher is its first
commit with person files following.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"


def _harness():
    spec = importlib.util.spec_from_file_location("harness", TOOLS / "edits_repeated_across_projects_v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_fresh_kinds_are_declared_in_code():
    harness = _harness()
    assert "fresh" in harness.KINDS
    assert len(harness.KINDS["fresh"]) == 16
    names = [kind[0] for kind in harness.KINDS["fresh"]]
    assert len(set(names)) == 16
    already = {kind[0] for which in ("seen", "held_out") for kind in harness.KINDS[which]}
    assert not already & set(names), "a fresh kind repeats an old one"


def test_the_fresh_set_is_collected_with_a_timestamp():
    harness = _harness()
    held = json.loads(harness.COMMITS.read_text())
    assert "fresh" in held["sets"]
    assert held["sets"]["fresh"]["collected"].startswith("2026-11-12")
    kinds = held["sets"]["fresh"]["kinds"]
    assert [k["kind"] for k in kinds] == [kind[0] for kind in harness.KINDS["fresh"]]


def test_a_collected_set_is_never_collected_twice():
    harness = _harness()
    with pytest.raises(SystemExit, match="not collected a second time"):
        harness.collect("fresh")


def test_every_kept_commit_names_its_files_and_parent():
    harness = _harness()
    held = json.loads(harness.COMMITS.read_text())
    for kind in held["sets"]["fresh"]["kinds"]:
        for commit in kind["commits"]:
            assert commit["project"] and commit["commit"] != commit["parent"]
            assert commit["files"], "a kept commit without files"

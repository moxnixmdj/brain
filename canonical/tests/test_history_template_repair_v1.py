#!/usr/bin/env python3
"""Tests for history-template repair: mining, anti-unification, and the leakage bound.

The bugs guarded here each produced a clean zero, which is the failure mode this project keeps
re-discovering: a key that matches nothing looks exactly like a population with no answer in it.

  1. A single line's shape as the key: `"<S>",` matches dozens of unrelated lines, and insertion
     then produced unparsable Python on 60% of attempts.
  2. `unified=0` hunks carry no context line, so treating the FIRST ADDED line as the anchor keys
     every template on the added text itself -- an index that matches nothing real.
  3. Qualified vs bare scope names (`Marker.__init__` vs `__init__`) drove eligibility to 0 of 8
     tasks while looking like a result.
  4. An addition naming a name the target file cannot resolve raises NameError; it can never be
     the fix, and filtering it BEFORE the budget is what makes history mining usable.

The leakage test is the most important one: the index must be built from the parent's ancestry
only, so the fix commit is unreachable by construction rather than by care.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import history_template_repair_v1 as H  # noqa: E402


# ---------------------------------------------------------------- shape and holes

def test_shape_replaces_identifiers_but_keeps_hole_order():
    shape, holes = H.shape_and_holes('raise InvalidMarker(f"bad {value!r}")')
    assert shape == "raise <I>(<S>)"
    assert holes == ["InvalidMarker"]


def test_keywords_and_self_are_not_holes():
    _, holes = H.shape_and_holes("if not self.enabled:")
    assert holes == ["enabled"]


def test_two_lines_differing_only_in_names_share_a_shape():
    a, ha = H.shape_and_holes("if not ref.isascii():")
    b, hb = H.shape_and_holes("if not name.isascii():")
    assert a == b
    assert ha == ["ref", "isascii"] and hb == ["name", "isascii"]


# ---------------------------------------------------------------- anti-unification

def test_instantiate_maps_historical_names_onto_site_names():
    template = {"anchor_holes": ["ref", "isascii"], "added": ["if not ref.isascii():"], "from": "x"}
    body = H.instantiate(template, ["name", "isascii"])
    assert body is not None
    assert "name.isascii()" in body


def test_instantiate_refuses_an_inconsistent_correspondence():
    """`a` mapping to two different names is not a substitution; guessing would be fabrication."""
    template = {"anchor_holes": ["a", "a"], "added": ["f(a, a)"], "from": "x"}
    assert H.instantiate(template, ["x", "y"]) is None


def test_instantiate_requires_equal_hole_arity():
    template = {"anchor_holes": ["a"], "added": ["return a"], "from": "x"}
    assert H.instantiate(template, ["a", "b"]) is None


# ---------------------------------------------------------------- habituation filter

def test_names_introduced_flags_a_name_the_file_cannot_resolve():
    known = H.habituated("value = 1\n")
    assert H.names_introduced("raise Err(value)", known) == ["Err"]


def test_names_introduced_accepts_a_name_the_file_already_has():
    known = H.habituated("def helper():\n    pass\n")
    assert H.names_introduced("helper()", known) == []


def test_names_introduced_ignores_builtins_and_self():
    known = H.habituated("x = 1\n")
    assert H.names_introduced("if not isinstance(self, int):", known) == []


# ---------------------------------------------------------------- insert points

def test_insert_points_are_complete_simple_statements_only():
    source = "def f():\n    x = 1\n    if x:\n        y = 2\n"
    points = H.insert_points(source)
    lines = {p[0] for p in points}
    assert 2 in lines, "a plain assignment is a valid insert point"
    assert 1 not in lines, "a compound header is not a place to insert a statement after"


def test_insert_after_rejects_unparsable_text():
    assert H.insert_after("def f():\n    x = 1\n", 2, "    for (\n") == ""


def test_insert_after_accepts_a_well_formed_statement():
    out = H.insert_after("def f():\n    x = 1\n", 2, "    return x\n")
    assert out != "" and "return x" in out


# ---------------------------------------------------------------- leakage

def test_the_history_index_cannot_reach_the_fix_commit():
    """The bound is `git log <parent>`, so the fix commit is unreachable by construction."""
    source = pathlib.Path(H.__file__).read_text()
    assert "mine_history(co, task[\"parent\"]" in source
    assert "--all" not in source, "mining from --all would reach the fix commit"


@pytest.mark.skipif(not pathlib.Path("/tmp/pkg").exists(), reason="packaging checkout unavailable")
def test_mining_from_a_parent_never_yields_the_fix_commits_own_text():
    import json

    corpus = json.loads((REPO_ROOT / "canonical/corpus/fail_to_pass_tasks_20261124_V1.json").read_text())
    task = next(t for t in corpus["tasks"] if t["sha"].startswith("8c37b047"))
    co = pathlib.Path("/tmp/pkg")
    H.git(co, "checkout", "-q", "--force", task["parent"])
    H.git(co, "clean", "-qfd")
    index = H.mine_history(co, task["parent"], limit=120)
    fix_line = "if not ref.isascii():"
    landed = [tpl for templates in index.values() for tpl in templates
              if any(fix_line in a for a in tpl["added"])]
    assert landed == [], "the index must not contain the answer it is being asked to find"

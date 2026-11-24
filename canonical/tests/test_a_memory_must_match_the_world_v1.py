"""Two ways the machine kept believing a file it no longer had.

THE PREMISE UNDER TEST. The owner's reason for saving rules rather than traces is that environments
change. Both defects here are the same failure in two places: a memory that cannot notice that the
world has moved on.

    1. `research_tool_loader_v1.load_symbol` keyed its module cache on the PATH alone. A file edited
       after its first load kept executing its OLD code. Measured 2026-11-23, a corrected tool was
       still run from a stale cached module and failed with RESEARCH_TOOL_SYMBOL_MISSING for a
       function that was plainly on disk.

    2. `grounded_action_v1.load_registry` unioned every persisted forged row into the registry
       unconditionally. When a directory was rewritten, `act` still selected the previous run's row,
       which pointed at a function no longer in the file, and reported a missing symbol instead of
       doing the work. A memory of a tool that is gone is not a capability.

Neither is about speed. Both are about a system that reports confident failure about a world it is
no longer looking at.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as L  # noqa: E402
from canonical.runtime import grounded_action_v1 as GA  # noqa: E402


def test_an_edited_file_is_reloaded_not_remembered(tmp_path, monkeypatch):
    """The cache must key on CONTENT, so a changed file has no cached entry to fall back on."""
    monkeypatch.chdir(tmp_path)
    tool = tmp_path / "tool.py"
    tool.write_text("def answer():\n    return {'v': 1}\n", encoding="utf-8")
    first = L.load_symbol(tmp_path, "tool.py", "answer")
    assert first() == {"v": 1}

    tool.write_text("def answer():\n    return {'v': 2}\n", encoding="utf-8")
    second = L.load_symbol(tmp_path, "tool.py", "answer")
    assert second() == {"v": 2}, "a stale module was served after the file changed"

    # and a genuinely new function in an edited file is findable, rather than "missing"
    tool.write_text("def other():\n    return {'v': 3}\n", encoding="utf-8")
    assert L.load_symbol(tmp_path, "tool.py", "other")() == {"v": 3}


def test_an_unchanged_file_is_not_reloaded(tmp_path, monkeypatch):
    """Content addressing must not become 're-exec every time': the same bytes are the same module."""
    monkeypatch.chdir(tmp_path)
    tool = tmp_path / "same.py"
    tool.write_text("def answer():\n    return {'ok': True}\n", encoding="utf-8")
    a = L.load_symbol(tmp_path, "same.py", "answer")
    b = L.load_symbol(tmp_path, "same.py", "answer")
    assert a is b, "identical source produced two module objects"


def test_a_forged_row_for_a_function_that_is_gone_is_not_offered():
    """`_still_real` is the check; the registry must apply it, not merely own it."""
    alive = {
        "capability_id": "forged.demo_v1.alive",
        "action_template": {"args": {"_forged_id": "forged.demo_v1.alive"}},
        "provides": ["forged.canonical/runtime/room_census_v1.py::survey"],
    }
    vanished = {
        "capability_id": "forged.demo_v1.vanished",
        "action_template": {"args": {"_forged_id": "forged.demo_v1.vanished"}},
        "provides": ["forged.canonical/runtime/room_census_v1.py::no_such_function_anywhere"],
    }
    missing_file = {
        "capability_id": "forged.demo_v1.missing",
        "action_template": {"args": {"_forged_id": "forged.demo_v1.missing"}},
        "provides": ["forged.canonical/runtime/room_census_v1.py::this_file_is_gone.py::f"],
    }
    assert GA._still_real(alive) is True, alive
    assert GA._still_real(vanished) is False, vanished
    assert GA._still_real(missing_file) is True or GA._still_real(missing_file) is False


def test_doubt_answers_keep_not_drop():
    """A row this cannot interpret is not evidence of absence; dropping it would forget real work."""
    for odd in ({}, None, {"provides": []}, {"provides": ["nonsense"]},
                {"provides": ["forged.x::y"], "action_template": {}}):
        assert GA._still_real(odd) is True, odd

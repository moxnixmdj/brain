# PROJECT_BRAIN
"""A cached symbol index must describe the Python bytes currently on disk."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as choreograph
from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer


def _fixture(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "tests").mkdir()
    (root / "pkg" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "tests" / "test_calc.py").write_text(
        "from pkg.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    # Unparseable modules have hashes too and must not disappear from freshness.
    (root / "pkg" / "broken.py").write_text("def bad(:\n")
    indexer.run({"source_root": ".", "output_path": "cache.json"}, root)


def _impact(root: Path, cached: bool, name: str) -> dict:
    args = {"source_root": ".", "changed_paths": ["pkg/calc.py"],
            "test_roots": ["tests"], "output_path": name}
    if cached:
        args["index_path"] = "cache.json"
    return impact.run(args, root)


def _plan(root: Path, cached: bool, name: str) -> dict:
    args = {"source_root": ".", "output_path": name,
            "edits": [{"op": "rename_symbol", "module": "pkg/calc.py",
                       "name": "add", "new_name": "sum_values"}]}
    if cached:
        args["index_path"] = "cache.json"
    return choreograph.run(args, root)


@pytest.mark.parametrize("consumer", ["impact", "plan"])
@pytest.mark.parametrize("mutation", ["added_test", "removed_test", "changed_test", "unparseable_changed"])
def test_stale_cache_is_refused_before_selection_or_planning(
        tmp_path: Path, consumer: str, mutation: str, capsys):
    _fixture(tmp_path)
    test = tmp_path / "tests" / "test_calc.py"
    if mutation == "added_test":
        (tmp_path / "tests" / "test_added.py").write_text(
            "from pkg.calc import add\ndef test_added(): assert add(2, 3) == 5\n")
    elif mutation == "removed_test":
        test.unlink()
    elif mutation == "changed_test":
        test.write_text(test.read_text() + "\ndef test_new(): assert add(4, 5) == 9\n")
    else:
        (tmp_path / "pkg" / "broken.py").write_text("def bad(:\n# changed\n")

    if consumer == "impact":
        with pytest.raises(RuntimeError, match="INDEX_CACHE_STALE"):
            _impact(tmp_path, True, "selection.json")
    else:
        with pytest.raises(SystemExit):
            _plan(tmp_path, True, "plan.json")
        assert "INDEX_CACHE_STALE" in capsys.readouterr().out
    assert not (tmp_path / ("selection.json" if consumer == "impact" else "plan.json")).exists()


@pytest.mark.parametrize("consumer", ["impact", "plan"])
def test_fresh_cache_is_still_reused_and_matches_a_fresh_index(tmp_path: Path, consumer: str):
    _fixture(tmp_path)
    run = _impact if consumer == "impact" else _plan
    fresh = run(tmp_path, False, "fresh.json")
    cached = run(tmp_path, True, "cached.json")
    assert (tmp_path / "fresh.json").read_bytes() == (tmp_path / "cached.json").read_bytes()
    if consumer == "plan":
        assert fresh["cache_used"] == 0
        assert cached["cache_used"] == 1
    else:
        assert cached["selected_test_count"] == fresh["selected_test_count"] == 1


def test_duplicate_cached_file_ledger_is_rejected(tmp_path: Path):
    _fixture(tmp_path)
    cache = json.loads((tmp_path / "cache.json").read_text())
    cache["modules"].append(cache["modules"][0])
    (tmp_path / "cache.json").write_text(json.dumps(cache))
    with pytest.raises(RuntimeError, match="INDEX_CACHE_INVALID_FILE_LEDGER"):
        _impact(tmp_path, True, "selection.json")

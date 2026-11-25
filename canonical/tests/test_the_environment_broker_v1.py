import json
import pathlib
import subprocess
import sys

import pytest

from canonical.swe_kernel import the_environment_broker_v1 as B


def make_tree(tmp_path: pathlib.Path, *, requires_python=">=3.8", with_pytest=True):
    (tmp_path / "src" / "toypkg").mkdir(parents=True)
    (tmp_path / "src" / "toypkg" / "__init__.py").write_text("X = 1\n")
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_toy.py").write_text("def test_ok():\n    assert __import__('toypkg').X == 1\n")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\n"
        f"requires-python = \"{requires_python}\"\n"
        "dependencies = [\"tomli>=2\"]\n\n[build-system]\nrequires = [\"flit_core\"]\n"
        "build-backend = \"flit_core.buildapi\"\n")
    return tmp_path


def test_a_non_python_environment_is_refused_by_name(tmp_path):
    (tmp_path / "notes.txt").write_text("hello\n")
    got = B.broker(tmp_path, "run-tests", tmp_path / "memory.json")
    assert got["verdict"] == "REFUSE__NOT_A_PYTHON_ENVIRONMENT"


def test_a_goal_outside_the_closed_contracts_is_refused_by_name(tmp_path):
    tree = make_tree(tmp_path)
    got = B.broker(tree, "translate-this-codebase", tmp_path / "memory.json")
    assert got["verdict"] == "REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS"


def test_layout_requires_python_and_declared_deps_are_derived_then_the_suite_is_executed(tmp_path):
    tree = make_tree(tmp_path)
    got = B.broker(tree, "run-tests", tmp_path / "memory.json")
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert got["layout"]["kind"] == "src-layout"
    assert got["layout"]["packages"] == ["toypkg"]
    assert got["requirements"]["requires_python"] == ">=3.8"
    assert got["requirements"]["declared_deps"] == ["tomli>=2"]
    assert got["runner"]["exit_code"] == 0
    assert got["from_memory"] is False


def test_a_passing_run_is_cached_and_a_warm_run_reuses_it(tmp_path):
    tree = make_tree(tmp_path)
    memory = tmp_path / "memory.json"
    cold = B.broker(tree, "run-tests", memory)
    warm = B.broker(tree, "run-tests", memory)
    assert cold["verdict"] == "ENVIRONMENT_BROKERED" and cold["from_memory"] is False
    assert warm["verdict"] == "ENVIRONMENT_BROKERED_FROM_MEMORY" and warm["from_memory"] is True


def test_a_corrupted_cache_entry_is_rederived_not_believed(tmp_path):
    tree = make_tree(tmp_path)
    memory = tmp_path / "memory.json"
    B.broker(tree, "run-tests", memory)
    data = json.loads(memory.read_text())
    digest = next(iter(data["entries"]))
    bad = dict(data["entries"][digest])
    bad["runner"] = {**bad["runner"],
                     "command": [sys.executable, "-c", "import sys; sys.exit(3)"]}
    data["entries"][digest] = bad
    memory.write_text(json.dumps(data))
    got = B.broker(tree, "run-tests", memory)
    assert got["from_memory"] is False
    assert got["verdict"] == "ENVIRONMENT_BROKERED"       # re-derived, correct answer restored
    assert got["runner"]["exit_code"] == 0
    assert got["recheck"]["ok"] is False                  # the stale record was caught by execution


def test_a_garbage_cache_file_is_ignored(tmp_path):
    tree = make_tree(tmp_path)
    memory = tmp_path / "memory.json"
    memory.write_text("{not valid json")
    got = B.broker(tree, "run-tests", memory)
    assert got["verdict"] == "ENVIRONMENT_BROKERED" and got["from_memory"] is False


def test_a_failed_suite_is_refused_and_nothing_is_cached(tmp_path):
    tree = make_tree(tmp_path)
    (tree / "tests" / "test_toy.py").write_text("def test_broken():\n    assert 1 == 2\n")
    memory = tmp_path / "memory.json"
    got = B.broker(tree, "run-tests", memory)
    assert got["verdict"] == "REFUSE__NO_RUNNER_EXECUTED_CLEANLY"
    assert not memory.exists() or not json.loads(memory.read_text()).get("entries")


def test_a_requires_python_floor_above_this_interpreter_is_refused(tmp_path):
    tree = make_tree(tmp_path, requires_python=">=99.0")
    got = B.broker(tree, "run-tests", tmp_path / "memory.json")
    assert got["verdict"] == "REFUSE__REQUIRES_PYTHON_NOT_MET_LOCALLY"


def test_editing_the_evidence_invalidates_the_cache(tmp_path):
    tree = make_tree(tmp_path)
    memory = tmp_path / "memory.json"
    B.broker(tree, "run-tests", memory)
    text = (tree / "pyproject.toml").read_text()
    (tree / "pyproject.toml").write_text(text.replace(">=3.8", ">=3.9"))
    got = B.broker(tree, "run-tests", memory)
    assert got["from_memory"] is False

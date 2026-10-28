# PROJECT_BRAIN
"""Safety and truth regressions for the hardcore-SWE lane, each measured first.

  * python_tests_generate_scaffold rmtree'd a generated root that CONTAINED
    the source tree (one-way overlap check) and rmtree'd any pre-existing
    directory at generated_tests_root.
  * python_issue_to_pr_orchestrate rmtree'd whatever sat at worktree_path.
  * three symbol-index consumers accepted a cache describing bytes no longer
    on disk (NL intent, scaffold, symbol resolve).
  * execute_v1 compared size+mtime, so a forged mtime hid a content change,
    and a program could write beside the project unobserved.
  * evidence_oracle_hypothesis_v1 hard-coded ``result >= 0`` whatever the
    docstring said, exec'd the source in-process, and verified a contract
    violation as clean.
  * software_repair_loop_cegis_hypothesis_v1 verified zero iterations.

Every fixture is created fresh under a temporary directory.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import confine_v1  # noqa: E402
from canonical.runtime import execute_v1  # noqa: E402
from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as hyp  # noqa: E402
from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as nl  # noqa: E402
from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as pr  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer  # noqa: E402
from canonical.runtime.bound_capabilities import python_symbol_resolve as resolve  # noqa: E402
from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as scaffold  # noqa: E402
from canonical.runtime.bound_capabilities import software_repair_loop_cegis_hypothesis_v1 as loop  # noqa: E402

CALC = "def add(a: int, b: int) -> int:\n    return a + b\n"


def _tree(root: Path, src: str = "src") -> Path:
    source = root / src
    (source / "pkg").mkdir(parents=True)
    (source / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (source / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    return source


def _scaffold(root: Path, **extra) -> dict:
    args = {"source_root": "src", "generated_tests_root": "gen",
            "output_path": "out/summary.json", "python_executable": sys.executable,
            "timeout_s": 60}
    args.update(extra)
    return scaffold.run(args, root)


# --------------------------------------------------------------------------
# deletion
# --------------------------------------------------------------------------

def test_scaffold_refuses_a_generated_root_that_contains_the_source(tmp_path: Path):
    _tree(tmp_path, "group/src")
    sentinel = tmp_path / "group" / "notes.txt"
    sentinel.write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        _scaffold(tmp_path, source_root="group/src", generated_tests_root="group")
    assert "PATH_OVERLAPS_SOURCE_ROOT:generated_tests_root" in str(caught.value)
    assert sentinel.read_text(encoding="utf-8") == "mine"
    assert (tmp_path / "group" / "src" / "pkg" / "calc.py").read_text(encoding="utf-8") == CALC


def test_scaffold_refuses_to_delete_a_directory_it_did_not_create(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "gen").mkdir()
    (tmp_path / "gen" / "precious.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        _scaffold(tmp_path)
    assert "OUTPUT_DIR_NOT_OWNED_BY_BRAIN:generated_tests_root" in str(caught.value)
    assert (tmp_path / "gen" / "precious.txt").read_text(encoding="utf-8") == "keep"


def test_scaffold_still_recreates_its_own_generated_root(tmp_path: Path):
    _tree(tmp_path)
    first = _scaffold(tmp_path)
    assert (tmp_path / "gen" / scaffold.OWNED_DIR_MARKER).is_file()
    second = _scaffold(tmp_path)
    assert first["generated_count"] == second["generated_count"] == 1
    assert first["output_sha256"] == second["output_sha256"]


def _pr_args(**extra) -> dict:
    args = {"task_path": "task.json", "source_root": "src", "worktree_path": "wt",
            "output_path": "out/summary.json", "diff_path": "out/change.diff",
            "pr_intent_path": "out/pr.json", "python_executable": sys.executable,
            "timeout_s": 120}
    args.update(extra)
    return args


def _pr_task(root: Path) -> None:
    (root / "task.json").write_text(json.dumps({
        "issue_id": "I-1", "title": "rename add",
        "edits": [{"op": "rename_symbol", "module": "pkg/calc.py",
                   "name": "add", "new_name": "plus"}]}), encoding="utf-8")


def test_issue_to_pr_refuses_to_delete_a_worktree_path_it_does_not_own(tmp_path: Path):
    _tree(tmp_path)
    _pr_task(tmp_path)
    (tmp_path / "wt").mkdir()
    (tmp_path / "wt" / "precious.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        pr.run(_pr_args(), tmp_path)
    assert "WORKTREE_DIR_NOT_OWNED_BY_BRAIN" in str(caught.value)
    assert (tmp_path / "wt" / "precious.txt").read_text(encoding="utf-8") == "keep"


def test_issue_to_pr_recreates_its_own_worktree_and_adopts_an_empty_one(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "src" / "pkg" / "test_calc.py").write_text(
        "from pkg.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
    _pr_task(tmp_path)
    (tmp_path / "wt").mkdir()  # empty: adopted, not refused
    first = pr.run(_pr_args(), tmp_path)
    assert (tmp_path / "wt" / pr.OWNED_DIR_MARKER).is_file()
    second = pr.run(_pr_args(), tmp_path)
    assert first["applied_op_count"] == second["applied_op_count"] == 1
    assert first["diff_sha256"] == second["diff_sha256"]
    assert (tmp_path / "src" / "pkg" / "calc.py").read_text(encoding="utf-8") == CALC


# --------------------------------------------------------------------------
# stale caches
# --------------------------------------------------------------------------

def _cache_then_add_second_helper(root: Path) -> None:
    source = _tree(root)
    (source / "pkg" / "a.py").write_text("def helper(x):\n    return x + 1\n", encoding="utf-8")
    indexer.run({"source_root": ".", "output_path": "cache.json"}, source)
    cache = json.loads((source / "cache.json").read_text(encoding="utf-8"))
    (source / "cache.json").unlink()
    cache["source_root"] = "src"
    (root / "cache.json").write_text(json.dumps(cache), encoding="utf-8")
    (source / "pkg" / "b.py").write_text("def helper(x):\n    return x - 1\n", encoding="utf-8")


def test_nl_intent_refuses_a_cache_older_than_the_tree(tmp_path: Path):
    _cache_then_add_second_helper(tmp_path)
    (tmp_path / "issue.json").write_text(json.dumps(
        {"issue_id": "NL-STALE", "title": "Rename helper to assist"}), encoding="utf-8")
    args = {"issue_path": "issue.json", "source_root": "src",
            "output_path": "out/intent.json", "index_path": "cache.json"}
    with pytest.raises(SystemExit) as caught:
        nl.run(args, tmp_path)
    assert "INDEX_CACHE_STALE" in str(caught.value)
    assert not (tmp_path / "out" / "intent.json").exists()


def test_scaffold_refuses_a_cache_older_than_the_tree(tmp_path: Path):
    _cache_then_add_second_helper(tmp_path)
    with pytest.raises(SystemExit) as caught:
        _scaffold(tmp_path, index_path="cache.json")
    assert "INDEX_CACHE_STALE" in str(caught.value)


def test_symbol_resolve_refuses_a_cache_older_than_the_tree(tmp_path: Path, capsys):
    source = _tree(tmp_path)
    (source / "pkg" / "a.py").write_text("def helper(x):\n    return x + 1\n", encoding="utf-8")
    indexer.run({"source_root": "src", "output_path": "cache.json"}, tmp_path)
    (source / "pkg" / "b.py").write_text("def helper(x):\n    return x - 1\n", encoding="utf-8")
    args = {"source_root": "src", "output_path": "out/resolve.json", "index_path": "cache.json",
            "queries": [{"module": "src/pkg/a.py", "line": 1, "name": "helper"}]}
    with pytest.raises(SystemExit):
        resolve.run(args, tmp_path)
    assert "INDEX_CACHE_STALE" in capsys.readouterr().out
    assert not (tmp_path / "out" / "resolve.json").exists()


# --------------------------------------------------------------------------
# execution kernel
# --------------------------------------------------------------------------

def test_execute_sees_a_content_change_behind_a_restored_mtime(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    target = project / "a.txt"
    target.write_text("GOOD", encoding="utf-8")
    st = target.stat()
    program = ("import os\nfrom pathlib import Path\np = Path('a.txt')\n"
               "p.write_text('EVIL')\nos.utime(p, ns=(%d, %d))\n" % (st.st_atime_ns, st.st_mtime_ns))
    result = execute_v1.run(program, str(project), timeout=60)
    assert result["verdict"] == execute_v1.SUCCESS, result
    assert result["diff"]["modified"] == ["a.txt"]
    assert target.read_text(encoding="utf-8") == "EVIL"


@pytest.mark.skipif(not confine_v1.available(), reason="no user-namespace confinement on this machine")
def test_execute_confines_a_program_that_writes_beside_the_project(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    result = execute_v1.run("open('../escape.txt', 'w').write('x')\n", str(project), timeout=60)
    assert result["confined"] is True
    assert result["verdict"] != execute_v1.SUCCESS
    assert not (tmp_path / "escape.txt").exists()


# --------------------------------------------------------------------------
# property oracle
# --------------------------------------------------------------------------

def _oracle(root: Path, source: str, **extra) -> dict:
    args = {"source": source, "output_path": "out/oracle.json"}
    args.update(extra)
    return hyp.run(args, root)


@pytest.mark.skipif(not confine_v1.available(), reason="no user-namespace confinement on this machine")
def test_property_oracle_checks_the_postcondition_the_docstring_states(tmp_path: Path):
    wrong = _oracle(tmp_path, 'def f(x):\n    """post: _ == x + 1"""\n    return abs(x)\n')
    assert wrong["status"] == "CONTRACT_VIOLATION_FOUND", wrong
    assert wrong["verified"] is True and wrong["confined"] is True
    assert wrong["violations"][0]["post"] == "_ == x + 1"
    right = _oracle(tmp_path, 'def f(x):\n    """post: _ == x + 1"""\n    return x + 1\n')
    assert right["status"] in ("NO_COUNTEREXAMPLE_FOUND", "NO_COUNTEREXAMPLE_IN_SAMPLE"), right
    assert right["violations"] == [] and right["checked"] > 0
    assert right["proves_absence"] is False


@pytest.mark.skipif(not confine_v1.available(), reason="no user-namespace confinement on this machine")
def test_property_oracle_source_cannot_write_outside_its_scratch(tmp_path: Path):
    marker = tmp_path / "escaped.txt"
    source = ("from pathlib import Path\nPath(%r).write_text('bad')\n"
              "def f(x):\n    \"\"\"post: _ >= 0\"\"\"\n    return abs(x)\n" % str(marker))
    result = _oracle(tmp_path, source)
    assert not marker.exists()
    assert result["verified"] is False
    assert result["status"].startswith("SOURCE_DOES_NOT_EXECUTE")


def test_property_oracle_does_not_verify_without_confinement(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(hyp, "_confinement", lambda: None)
    result = _oracle(tmp_path, 'def f(x):\n    """post: _ >= 0"""\n    return abs(x)\n')
    assert result["verified"] is False
    assert result["status"] == "CONFINEMENT_UNAVAILABLE"
    # The caller may accept the risk explicitly, and the receipt says so.
    accepted = _oracle(tmp_path, 'def f(x):\n    """post: _ == x + 1"""\n    return abs(x)\n',
                       allow_unconfined=True)
    assert accepted["confined"] is False
    assert accepted["status"] == "CONTRACT_VIOLATION_FOUND"


def test_property_oracle_with_no_postcondition_is_not_verified(tmp_path: Path):
    result = _oracle(tmp_path, "def f(x):\n    return x\n", allow_unconfined=True)
    assert result["status"] == "NO_POSTCONDITION_PARSED"
    assert result["verified"] is False and result["checked"] == 0


# --------------------------------------------------------------------------
# repair loop
# --------------------------------------------------------------------------

def test_repair_loop_with_zero_budget_verifies_nothing(tmp_path: Path):
    result = loop.run({"budget": 0, "output_path": "out/loop.json"}, tmp_path)
    assert result["iterations"] == 0
    assert result["verified"] is False
    on_disk = json.loads((tmp_path / "out" / "loop.json").read_text(encoding="utf-8"))
    assert on_disk["verified"] is False

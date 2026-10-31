"""Move destinations must be confined before staging writes occur."""
import json
from pathlib import Path
import sys

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator


@pytest.mark.parametrize("target", ["../src/injected.py", "../injected.py",
                                    "../../injected.py", "ABSOLUTE", "pkg/../../injected.py"])
def test_move_escape_is_refused_before_creation(tmp_path, target):
    repo = tmp_path / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "src/pkg/core.py").write_text("def helper():\n    return 1\n")
    if target == "ABSOLUTE":
        target = str(tmp_path / "absolute.py")
    dest = (repo / "work" / target).resolve()
    assert tmp_path.resolve() in dest.parents and not dest.exists()
    (repo / "task.json").write_text(json.dumps({"issue_id": "path", "edits": [
        {"op": "move_symbol", "module": "pkg/core.py", "qualname": "helper", "to_module": target}]}))
    with pytest.raises(SystemExit):
        orchestrator.run({"task_path": "task.json", "source_root": "src", "worktree_path": "work",
                          "output_path": "out/summary.json", "diff_path": "out/change.diff",
                          "pr_intent_path": "out/pr.json", "python_executable": sys.executable}, repo)
    assert not dest.exists()
    assert (repo / "src/pkg/core.py").read_text() == "def helper():\n    return 1\n"


def test_all_move_paths_checked_before_any_destination_is_staged(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "src/pkg/core.py").write_text("def helper():\n    return 1\n")
    (repo / "task.json").write_text(json.dumps({"issue_id": "path", "edits": [
        {"op": "move_symbol", "module": "pkg/core.py", "qualname": "helper", "to_module": "pkg/valid.py"},
        {"op": "move_symbol", "module": "pkg/core.py", "qualname": "helper", "to_module": "../../escaped.py"}]}))
    with pytest.raises(SystemExit):
        orchestrator.run({"task_path": "task.json", "source_root": "src", "worktree_path": "work",
                          "output_path": "out/summary.json", "diff_path": "out/change.diff",
                          "pr_intent_path": "out/pr.json", "python_executable": sys.executable}, repo)
    assert not (repo / "work/pkg/valid.py").exists()
    assert not (tmp_path / "escaped.py").exists()

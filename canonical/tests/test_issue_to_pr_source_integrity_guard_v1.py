"""Detect persistent source changes after pytest; detection is not isolation."""
import json
import sys

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator


@pytest.mark.parametrize("relative", ["pkg/core.py", "pyproject.toml", "requirements.lock", ".github/workflows/check.yml"])
def test_test_process_source_mutation_cannot_verify(tmp_path, monkeypatch, relative):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    repo = tmp_path / "repo"
    src = repo / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg/__init__.py").write_text("")
    (src / "pkg/core.py").write_text("def helper(x):\n    return x + 1\n")
    target = src / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if relative != "pkg/core.py":
        target.write_text("initial = 1\n")
    before = target.read_bytes()
    (src / "tests").mkdir()
    (src / "tests/test_core.py").write_text(
        "from pathlib import Path\nfrom pkg.core import helper\ndef test_core():\n"
        "    p = Path(__file__).resolve().parents[2] / 'src' / " + repr(relative) + "\n"
        "    p.write_text('# changed original\\n')\n    assert helper(2) == 3\n")
    (repo / "task.json").write_text(json.dumps({"issue_id": "integrity", "edits": [
        {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}]}))
    with pytest.raises(SystemExit, match="SOURCE_TREE_MUTATED"):
        orchestrator.run({"task_path": "task.json", "source_root": "src", "worktree_path": "work",
                          "output_path": "out/summary.json", "diff_path": "out/change.diff",
                          "pr_intent_path": "out/pr.json", "python_executable": sys.executable}, repo)
    assert target.read_bytes() != before  # Detection does not undo or prevent the write.
    assert not (repo / "out/summary.json").exists()

"""Direct issue-to-PR forgery counterexample in a disposable project.

The project plugin deliberately falsifies both pytest exit status and JUnit.
This is not a security sandbox and does not establish front-door reachability.
Exit 1 while the orchestrator credits the forged report as verified.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator  # noqa: E402


def main() -> int:
    previous = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        with tempfile.TemporaryDirectory(prefix="brain-pytest-forgery-") as tmp:
            repo = Path(tmp)
            source = repo / "src"
            (source / "pkg").mkdir(parents=True)
            (source / "tests").mkdir()
            (source / "pkg/__init__.py").write_text("")
            (source / "pkg/core.py").write_text("def helper(x):\n    return x + 1\n")
            (source / "tests/test_core.py").write_text(
                "from pkg.core import helper\n"
                "def test_real_failure():\n    assert helper(2) == 999\n")
            (source / "conftest.py").write_text(
                "from pathlib import Path\n"
                "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n"
                "def pytest_unconfigure(config):\n"
                "    Path(config.option.xmlpath).write_text("
                "'<testsuite><testcase classname=\"invented\" name=\"pass\"/></testsuite>')\n")
            (repo / "task.json").write_text(json.dumps({"issue_id": "forged-junit", "edits": [
                {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}]}))
            result = orchestrator.run({"task_path": "task.json", "source_root": "src",
                                       "worktree_path": "work", "output_path": "out/summary.json",
                                       "diff_path": "out/change.diff", "pr_intent_path": "out/pr.json",
                                       "python_executable": sys.executable, "timeout_s": 30}, repo)
            artifact = json.loads((repo / "out/pr.json").read_text())
            output = {"schema": "BRAIN_ISSUE_TO_PR_JUNIT_FORGERY_PROBE_V1",
                      "verified": result["verified"],
                      "reported_tests_passed": result["test_passed_count"],
                      "reported_tests_failed": result["test_failed_count"],
                      "reported_pytest_rc": artifact["body"]["tests"]["pytest_rc"],
                      "actual_fixture_test": "assert helper(2) == 999; helper(2) returns 3",
                      "limitations": "One direct-adapter disposable project; the fixture intentionally forges its own pytest report. "
                                     "No front-door reachability, real repository rate, or independent authentication claim.",
                      "terminal_authority": False}
            print(json.dumps(output, indent=2, sort_keys=True))
            return int(result["verified"] is True)
    finally:
        if previous is None:
            os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        else:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = previous


if __name__ == "__main__":
    raise SystemExit(main())

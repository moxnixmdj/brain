"""Probe issue-to-PR path and source integrity in disposable projects.

This tests the direct structured-task adapter, not front-door reachability. The
pytest cases deliberately mutate only disposable fixtures; no isolation or
independent attestation is claimed. Exit 1 means a constructed unsafe case was
observed. No historical code, fake tools, or model calls are used.
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


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(case: Path) -> Path:
    repo = case / "repo"
    _write(repo, "src/pkg/__init__.py", "")
    _write(repo, "src/pkg/core.py", "def helper(x):\n    return x + 1\n")
    return repo


def _invoke(repo: Path, edit: dict) -> dict:
    _write(repo, "task.json", json.dumps({"issue_id": "integrity-probe", "edits": [edit]}))
    try:
        result = orchestrator.run({"task_path": "task.json", "source_root": "src",
                                   "worktree_path": "work", "output_path": "out/summary.json",
                                   "diff_path": "out/change.diff", "pr_intent_path": "out/pr.json",
                                   "python_executable": sys.executable, "timeout_s": 30}, repo)
        return {"refused": False, "verified": result.get("verified"),
                "test_passed_count": result.get("test_passed_count")}
    except SystemExit as exc:
        try:
            detail = json.loads(str(exc))
            reason = detail.get("reason", "UNKNOWN") if isinstance(detail, dict) else "UNKNOWN"
        except (json.JSONDecodeError, TypeError):
            reason = "UNPARSEABLE_REFUSAL"
        return {"refused": True, "reason": str(reason)[:120]}


def measure() -> dict:
    old = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        paths = []
        sources = []
        with tempfile.TemporaryDirectory(prefix="brain-issue-integrity-") as tmp:
            base = Path(tmp)
            for label in ("source_tree", "repo_outside_worktree", "outside_repo", "absolute_outside_repo"):
                case = base / ("path_" + label)
                repo = _repo(case)
                target = {"source_tree": "../src/injected.py",
                          "repo_outside_worktree": "../injected.py",
                          "outside_repo": "../../injected.py",
                          "absolute_outside_repo": str(case / "absolute.py")}[label]
                destination = (repo / "work" / target).resolve()
                if case.resolve() not in destination.parents or destination.exists():
                    raise RuntimeError("fixture target must be absent and inside disposable case")
                result = _invoke(repo, {"op": "move_symbol", "module": "pkg/core.py",
                                        "qualname": "helper", "to_module": target})
                paths.append({"case": label, "file_created_outside_worktree": destination.is_file(),
                              "outside_repo": repo.resolve() not in destination.parents,
                              "adapter_result": result})
            for label, target in (("python_source", "pkg/core.py"),
                                  ("build_config", "pyproject.toml"),
                                  ("dependency_lock", "requirements.lock"),
                                  ("ci_workflow", ".github/workflows/check.yml")):
                case = base / ("source_" + label)
                repo = _repo(case)
                original = repo / "src" / target
                if target != "pkg/core.py":
                    _write(repo / "src", target, "initial = 1\n")
                before = original.read_bytes()
                test = ("from pathlib import Path\nfrom pkg.core import helper\n"
                        "def test_core():\n"
                        "    original = Path(__file__).resolve().parents[2] / 'src' / " + repr(target) + "\n"
                        "    original.write_text('# changed by the disposable test\\n')\n"
                        "    assert helper(2) == 3\n")
                _write(repo, "src/tests/test_core.py", test)
                result = _invoke(repo, {"op": "rename_symbol", "module": "pkg/core.py",
                                        "name": "helper", "new_name": "compute"})
                sources.append({"case": label, "source_mutated": original.read_bytes() != before,
                                "adapter_result": result})
        return {
            "schema": "BRAIN_ISSUE_TO_PR_INTEGRITY_PROBE_V1",
            "path_cases": paths,
            "source_cases": sources,
            "path_unsafe": sum(row["file_created_outside_worktree"] for row in paths),
            "source_unsafe_verified": sum(row["source_mutated"] and row["adapter_result"].get("verified") is True
                                          for row in sources),
            "limitations": ("Direct adapter with constructed disposable projects; path cases only prove creation "
                            "of previously absent empty files. Source cases use intentionally mutating pytest code. "
                            "This does not establish front-door reachability or a rate on real repositories."),
            "terminal_authority": False,
        }
    finally:
        if old is None:
            os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        else:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = old


def main() -> int:
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["path_unsafe"] > 0 or result["source_unsafe_verified"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())

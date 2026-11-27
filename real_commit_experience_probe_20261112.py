#!/usr/bin/env python3
"""Compare one taught edit with controls on a historical real-project task.

This is one producer-run diagnostic, not a benchmark or an independent verification.
The source example and target preimages are SHA-256 pinned. The target suite is run on
isolated temporary copies, but this is NOT a security sandbox: only use trusted code.
No source repository, lesson store, or runtime registry is modified.

The raw-reference arm is a hand-authored literal adaptation of the demonstrated method
rename, not an autonomous agent or a general raw-trajectory retrieval implementation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner

TEACHER = {
    "before": "8bbfa737b77af98d08a4fe90f6145ade5bfa3aa78661f451cce2071413f0d480",
    "after": "85fde8ec984b4889e947c184f000035d79e8e5ad46f25562c62ccf560f93713f",
}
TARGETS = {
    "test/testOutputCSV.py": "03c695c697f05eb13603fa227851f39182e184bf5cce4f84987528c19bffdd61",
    "test/testOutputHTML.py": "0dd3c38f9c36f1d5f3e212c9408d98b36b0645c2e420f668bb1046d55a45abd3",
}
OLD = "assertRegexpMatches"
NEW = "assertRegex"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"missing or wrong pinned input: {path}")


def _self_old(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "self" and node.attr == OLD)


class ExpectedMigration(ast.NodeTransformer):
    """Independent structural oracle: only self's old method is renamed."""

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if _self_old(node):
            node.attr = NEW
        return node


def verify_candidate(before: str, candidate: str) -> dict[str, Any]:
    """Compare Python syntax trees, not formatting. Does not prove semantic equivalence."""
    try:
        old_tree = ast.parse(before)
        changed_sites = sum(1 for n in ast.walk(old_tree) if _self_old(n))
        expected = ExpectedMigration().visit(old_tree)
        actual = ast.parse(candidate)
        equal = ast.dump(expected, include_attributes=False) == ast.dump(actual, include_attributes=False)
        remaining = sum(1 for n in ast.walk(actual) if _self_old(n))
        return {"applicable_sites": changed_sites, "remaining_old_sites": remaining,
                "matches_expected_ast": bool(changed_sites and equal and remaining == 0)}
    except (SyntaxError, ValueError) as error:
        return {"applicable_sites": None, "remaining_old_sites": None,
                "matches_expected_ast": False, "error": str(error)}


def run_tests(project: Path, dependencies: Path, home: Path) -> dict[str, Any]:
    """Run the two existing upstream unittest modules in a separate interpreter."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home),
           "PYTHONPATH": str(dependencies), "PYTHONDONTWRITEBYTECODE": "1",
           "LANG": "C.UTF-8"}
    cmd = [sys.executable, "-B", "-W", "error:Please use assertRegex instead:DeprecationWarning",
           "-m", "unittest", "test.testOutputCSV", "test.testOutputHTML"]
    try:
        proc = subprocess.run(cmd, cwd=project, env=env, text=True, capture_output=True,
                              timeout=45, check=False)
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "tests_run": None, "timed_out": True, "output": ""}
    output = proc.stdout + proc.stderr
    match = re.search(r"Ran (\d+) tests? in", output)
    return {"exit_code": proc.returncode, "tests_run": int(match.group(1)) if match else None,
            "timed_out": False, "output": output}


def wrong_applicability(rules: Any) -> dict[str, Any]:
    """Synthetic near miss: self is not a unittest.TestCase and methods differ."""
    source = '''class Custom:
    def assertRegexpMatches(self, *args):
        return "legacy"
    def assertRegex(self, *args):
        return "different"

def target(self):
    return self.assertRegexpMatches("x", "y", "message")
'''
    result = {}
    for arm in ("no_memory", "hand_adapted_raw", "one_demo_strict"):
        candidate, refusal = source, None
        if arm == "hand_adapted_raw":
            candidate = source.replace("self." + OLD + "(", "self." + NEW + "(")
        elif arm == "one_demo_strict":
            try:
                candidate = learner.repeated(rules, source, "the demonstrated change")
            except learner.Refused as error:
                refusal = str(error)
        namespace: dict[str, Any] = {}
        exec(compile(candidate, "synthetic_near_miss.py", "exec"), namespace)
        actual = namespace["target"](namespace["Custom"]())
        result[arm] = {"changed": candidate != source, "refusal": refusal,
                       "actual": actual, "expected": "legacy", "preserves_behavior": actual == "legacy"}
    return result


def run_experiment(project: Path, teach_before: Path, teach_after: Path,
                   dependencies: Path) -> dict[str, Any]:
    for name, path in (("before", teach_before), ("after", teach_after)):
        require_hash(path, TEACHER[name])
    for path, expected in TARGETS.items():
        require_hash(project / path, expected)
    if not dependencies.is_dir():
        raise ValueError("dependency path is not a directory")

    example = (teach_before.read_text(encoding="utf-8"), teach_after.read_text(encoding="utf-8"))
    rules = learner.learn_all([example])
    original_hashes = {name: digest(project / name) for name in TARGETS}
    report: dict[str, Any] = {
        "authority": "NONE; producer-run, not independently verified",
        "task": "migrate deprecated unittest assertion in two historical lizard test files",
        "teacher": "coralnet/coralnet c3691cba7fa03a655c89cefdf6ec79268307e1d6",
        "target_base": "Nielsen642/lizard fc8a14e84acd8a4baa2d98bdec4e7ac18ed137a5",
        "target_human_commit": "f44f7969c592ecbc1752827cb27dd44e79e1e75e",
        "rule_descriptions": [str(rule) for rule in rules],
        "example_utf8_bytes": sum(len(part.encode("utf-8")) for part in example),
        "synthetic_wrong_applicability": wrong_applicability(rules),
        "arms": {},
    }
    with tempfile.TemporaryDirectory(prefix="brain-real-commit-") as temporary:
        root = Path(temporary)
        for arm in ("no_memory", "hand_adapted_raw", "one_demo_strict"):
            work = root / arm
            shutil.copytree(project, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
            files: dict[str, Any] = {}
            for name in TARGETS:
                path = work / name
                before = path.read_text(encoding="utf-8")
                candidate = before
                refusal = None
                if arm == "hand_adapted_raw":
                    # A manually authored, task-specific reference, not the learner or autonomous retrieval.
                    candidate = before.replace("self." + OLD + "(", "self." + NEW + "(")
                elif arm == "one_demo_strict":
                    try:
                        candidate = learner.repeated(rules, before, "the demonstrated change")
                    except learner.Refused as error:
                        refusal = str(error)
                path.write_text(candidate, encoding="utf-8")
                files[name] = {"changed": candidate != before, "refusal": refusal,
                               "oracle": verify_candidate(before, candidate)}
            tests = run_tests(work, dependencies, root)
            report["arms"][arm] = {
                "files": files, "tests": tests,
                "task_pass": (tests["exit_code"] == 0 and tests["tests_run"] == 7
                              and all(item["oracle"]["matches_expected_ast"] for item in files.values())),
            }
    if {name: digest(project / name) for name in TARGETS} != original_hashes:
        raise RuntimeError("original target changed during the experiment")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="trusted target checkout at pinned base")
    parser.add_argument("--teacher-before", type=Path, required=True)
    parser.add_argument("--teacher-after", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True, help="directory with mock and jinja2")
    parser.add_argument("--json", type=Path, help="optional output path")
    args = parser.parse_args()
    try:
        report = run_experiment(args.project.resolve(), args.teacher_before.resolve(),
                                args.teacher_after.resolve(), args.dependencies.resolve())
    except (ValueError, OSError, learner.Refused) as error:
        print(f"EXPERIMENT UNAVAILABLE: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json:
        args.json.write_text(rendered + "\n", encoding="utf-8")
    # Exit 0 means the measurement ran, not that any arm passed the task.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

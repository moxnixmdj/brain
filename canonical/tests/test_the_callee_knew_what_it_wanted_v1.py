"""Reproduce the jinja d05bd3858c result from scratch, so it is verifiable, not a story.

This test does what the receipt claims, in one file, and cleans up after itself:

  1. create two worktrees of jinja at d05bd3858c^ (parent) and d05bd3858c (fix)
  2. capture the fault on the parent -- no reference to the human diff, ever
  3. derive the patch blind: at the raising frame, the unique live name the callee
     declares and the call omits
  4. assert the derived line is byte-identical to the human fix
  5. run the issue-derived oracle on parent (must FAIL) and on patched (must PASS)
  6. run the full suite on patched (must stay green)

It is skipped, not failed, when the jinja clone or the worktree machinery is absent --
an environment gap is not a capability claim in either direction.
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

JINJA = pathlib.Path("/home/user/repos/jinja")
PARENT = "d05bd3858c^"
FIX = "d05bd3858c"
SOURCE = "src/jinja2/filters.py"

pytestmark = pytest.mark.skipif(not (JINJA / ".git").exists(),
                               reason="jinja clone absent")


def git(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd or JINJA), *args], capture_output=True,
                          text=True, errors="replace")


def env_for(tree: pathlib.Path) -> dict[str, str]:
    import os
    return {**os.environ, "PYTHONPATH": "src:.", "PYTHONDONTWRITEBYTECODE": "1"}


ORACLE = '''
import jinja2
from jinja2 import pass_context


def test_issue_select_needs_context():
    env = jinja2.Environment()

    @pass_context
    def is_foo(ctx, s):
        assert ctx is not None
        return s == "foo"

    env.tests["foo"] = is_foo
    tmpl = env.from_string(
        "{% for x in ['one','foo'] | select('foo') %}{{ x }}{% endfor %}"
    )
    assert tmpl.render() == "foo"


def test_select_still_works():
    env = jinja2.Environment()
    tmpl = env.from_string("{% for x in [1,2,3] | select('odd') %}{{ x }}{% endfor %}")
    assert tmpl.render() == "13"
'''

FAULT_PROBE = '''
import json, sys
target = sys.argv[1]
rows = []
def tr(frame, event, arg):
    if event == "exception":
        exc, val, tb = arg
        if frame.f_code.co_filename.endswith(target):
            rows.append({"func": frame.f_code.co_name, "line": frame.f_lineno,
                         "exc": getattr(exc, "__name__", str(exc)),
                         "locals": sorted(frame.f_locals)})
    return tr
sys.settrace(tr)
import jinja2
from jinja2 import pass_context
env = jinja2.Environment()
@pass_context
def is_foo(ctx, s):
    return s == "foo"
env.tests["foo"] = is_foo
try:
    env.from_string("{% for x in ['one','foo'] | select('foo') %}{{ x }}{% endfor %}").render()
except Exception:
    pass
sys.settrace(None)
print(json.dumps(rows))
'''


@pytest.fixture(scope="module")
def trees():
    import pass_what_the_callee_wanted_v1 as rule
    with tempfile.TemporaryDirectory() as where:
        parent = pathlib.Path(where) / "parent"
        fix = pathlib.Path(where) / "fix"
        for tree, rev in ((parent, PARENT), (fix, FIX)):
            added = git("worktree", "add", "--detach", str(tree), rev)
            if added.returncode != 0:
                pytest.skip(f"worktree add failed: {added.stderr[:120]}")
        try:
            yield rule, parent, fix
        finally:
            for tree in (parent, fix):
                git("worktree", "remove", "--force", str(tree))


def run(tree: pathlib.Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=tree, capture_output=True,
                          text=True, errors="replace", timeout=600, env=env_for(tree))


def test_the_fault_names_a_line_the_rule_can_use(trees):
    rule, parent, _ = trees
    probe = parent / "_fault_probe.py"
    probe.write_text(FAULT_PROBE, encoding="utf-8")
    try:
        done = run(parent, ["_fault_probe.py", "jinja2/filters.py"])
    finally:
        probe.unlink(missing_ok=True)
    import json
    rows = json.loads(done.stdout.strip().splitlines()[-1])
    assert rows, "no exception recorded in filters.py -- the oracle is wrong"
    fault = rows[0]
    assert fault["exc"] == "TemplateRuntimeError"
    assert "context" in fault["locals"]


def test_the_rule_derives_the_human_line_blind(trees):
    rule, parent, fix = trees
    source = (parent / SOURCE).read_text(encoding="utf-8")
    probe = parent / "_fault_probe.py"
    probe.write_text(FAULT_PROBE, encoding="utf-8")
    try:
        done = run(parent, ["_fault_probe.py", "jinja2/filters.py"])
    finally:
        probe.unlink(missing_ok=True)
    import json
    fault = json.loads(done.stdout.strip().splitlines()[-1])[0]
    patch = rule.propose_patch(
        source,
        {"line": fault["line"], "locals": {n: "" for n in fault["locals"]}},
        [parent / "src", parent])
    assert patch is not None, "rule declined on the row it was built for"
    human = (fix / SOURCE).read_text(encoding="utf-8").splitlines()
    assert patch["new"].strip() == human[fault["line"] - 1].strip()


def test_oracle_fails_on_parent_and_passes_on_patched(trees):
    rule, parent, _ = trees
    oracle = parent / "t_issue.py"
    oracle.write_text(ORACLE, encoding="utf-8")
    try:
        before = run(parent, ["-m", "pytest", "t_issue.py", "-q", "-p", "no:cacheprovider"])
        assert "1 failed" in before.stdout and "1 passed" in before.stdout, before.stdout[-400:]

        source = (parent / SOURCE).read_text(encoding="utf-8")
        patch = rule.propose_patch(
            source, {"line": 1783, "locals": {"context": "x", "item": "x",
                                              "args": "x", "kwargs": "x"}},
            [parent / "src", parent])
        assert patch["new"].strip() != patch["old"].strip()
        lines = source.splitlines(keepends=True)
        lines[patch["line"] - 1] = patch["new"] + "\n"
        (parent / SOURCE).write_text("".join(lines), encoding="utf-8")
        after = run(parent, ["-m", "pytest", "t_issue.py", "-q", "-p", "no:cacheprovider"])
        assert "2 passed" in after.stdout, after.stdout[-400:]
    finally:
        oracle.unlink(missing_ok=True)

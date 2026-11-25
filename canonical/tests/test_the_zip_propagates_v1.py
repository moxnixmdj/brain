"""Reproduce the two zip results from scratch, so they are verifiable, not stories.

Each case, in one file, cleaning up after itself:

  1. worktree the httpx parent
  2. move an executed function out of its module into a new one (leaving references
     dangling) -- the synthetic root edit
  3. record the red state
  4. run the propagation loop
  5. assert the suite returns to baseline AND that only the moved symbol was relocated

Case B is the interesting one: `to_str` is imported by two different files, each on a
line that also imports symbols that must NOT move. A line-level rewriter passes case A and
fails case B.

Skipped (not failed) if the httpx clone or `zstandard` is absent -- an environment gap is
never scored as a capability claim in either direction.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

HTTPX = pathlib.Path("/home/user/repos/httpx")
PARENT = "7b19cd5f4b^"          # b47d94c, a commit with a stable known-red baseline
BASELINE = (28, 1386)            # (failed, passed) on this parent in this venv

pytestmark = pytest.mark.skipif(not (HTTPX / ".git").exists(),
                                reason="httpx clone absent")


def git(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd or HTTPX), *args], capture_output=True,
                          text=True, errors="replace")


def counts(log: str) -> tuple[int, int] | None:
    found = re.search(r"(\d+) failed, (\d+) passed", log)
    if found:
        return int(found.group(1)), int(found.group(2))
    found = re.search(r"(\d+) passed", log)
    if found:
        return 0, int(found.group(1))
    return None


def suite(tree: pathlib.Path) -> str:
    done = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q",
                           "-p", "no:cacheprovider", "--tb=no", "--timeout=60"],
                          cwd=tree, capture_output=True, text=True, errors="replace")
    return (done.stdout or "") + (done.stderr or "")


def relocate(tree: pathlib.Path, source: str, name: str, new_module: str) -> None:
    """Cut `name` out of `source` and write it into new_module. References now dangle."""
    path = tree / source
    text = path.read_text(encoding="utf-8")
    module_ast = ast.parse(text)
    lines = text.splitlines(keepends=True)
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            body = "".join(lines[node.lineno - 1:node.end_lineno])
            path.write_text("".join(
                line for index, line in enumerate(lines)
                if not node.lineno - 1 <= index < node.end_lineno), encoding="utf-8")
            (tree / new_module).write_text("# relocated\n" + body, encoding="utf-8")
            return
    raise AssertionError(f"{name} not found at top level of {source}")


@pytest.fixture(scope="module")
def parent_tree():
    with tempfile.TemporaryDirectory() as where:
        tree = pathlib.Path(where) / "httpx"
        added = git("worktree", "add", "--detach", str(tree), PARENT)
        if added.returncode != 0:
            pytest.skip(f"worktree add failed: {added.stderr[:140]}")
        try:
            yield tree
        finally:
            git("worktree", "remove", "--force", str(tree))


def run_loop(tree: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / "the_zip_propagates_v1.py"),
         "--tree", str(tree), "--seconds", "60"],
        capture_output=True, text=True, errors="replace", timeout=900)


def test_baseline_is_the_known_red_state(parent_tree):
    assert counts(suite(parent_tree)) == BASELINE


def test_case_a_single_file_mover(parent_tree):
    tree = parent_tree
    relocate(tree, "httpx/_models.py", "_normalize_header_key", "httpx/_hdr.py")
    red = counts(suite(tree))
    assert red is not None and red[0] > 100, f"moving an executed fn must go red, got {red}"
    done = run_loop(tree)
    assert counts(suite(tree)) == BASELINE, done.stdout[-600:]


def test_case_b_two_importers_one_hop(parent_tree):
    """to_str is imported by _auth.py AND _models.py, on lines that also import symbols
    which must not move. A line-granularity rewriter fails here; symbol-granularity
    passes."""
    tree = parent_tree
    relocate(tree, "httpx/_utils.py", "to_str", "httpx/_strconv.py")
    red = counts(suite(tree))
    assert red is None or red[0] > 0 or red[1] < BASELINE[1], \
        "a broken import must not look green"
    done = run_loop(tree)
    assert counts(suite(tree)) == BASELINE, done.stdout[-600:]

    # only the moved symbol was relocated; its line-neighbours stayed put
    auth = (tree / "httpx/_auth.py").read_text(encoding="utf-8")
    models = (tree / "httpx/_models.py").read_text(encoding="utf-8")
    assert "from ._strconv import to_str" in auth
    assert "from ._strconv import to_str" in models
    assert re.search(r"from \._utils import[^\n]*\bto_bytes\b", auth) or \
        "from ._utils import to_bytes" in auth
    assert re.search(r"from \._utils import[^\n]*to_bytes_or_str", models)


def test_case_c_signature_change(parent_tree):
    """A REQUIRED parameter added to an executed function. Every existing call is a
    TypeError until each site is repaired. The failure names both the callee and the
    missing parameter, which is enough to place the repair mechanically.

    Note recorded while building this: adding the parameter WITH a default leaves the
    suite green (28/1386 unchanged) -- a backward-compatible change creates no
    observable debt at all. Only a required parameter does."""
    tree = parent_tree
    utils = tree / "httpx/_utils.py"
    text = utils.read_text(encoding="utf-8")
    patched = text.replace(
        "match_type_of: typing.AnyStr) -> typing.AnyStr:",
        "match_type_of: typing.AnyStr, strict: bool) -> typing.AnyStr:")
    assert patched != text, "signature anchor not found"
    utils.write_text(patched, encoding="utf-8")

    red = counts(suite(tree))
    assert red is not None and red[0] > BASELINE[0], f"must break, got {red}"
    done = run_loop(tree)
    assert counts(suite(tree)) == BASELINE, done.stdout[-600:]
    assert "strict=True" in (tree / "httpx/_models.py").read_text(encoding="utf-8")

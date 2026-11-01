"""The repair search must be able to see the fault, and the suite must be able to import the package.

Two defects stood between this repository and its first correct edit on code it did not author.
Both were found by running a real project (pluggy at 3fc9e561, an injected `and`->`or` at
`src/pluggy/_manager.py:247`, 7 of 226 tests failing) rather than by reading the code, and both are
pure ranking/environment arithmetic, so both can be pinned without a network:

1. **The search could not see the fault.** The failing stack names line 251, which is INSIDE the
   branch the faulty condition sent control into:

       247:  elif not verified or hook.has_spec():      <- the fault
       251:      self._verify_hook(hook, hookimpl)       <- the raise the stack names

   The evidence rule was a binary +/-2-line window around stack lines, so the one site that mattered
   scored zero while the per-file budget of 24 candidates filled with unrelated constant guesses.
   Graded proximity alone was not enough either: the true site scored 9600 and eight constants
   three lines from another frame scored 9700 and crowded it out. The rule that works is the one the
   language already states -- control entered that branch BECAUSE its test was true -- so the
   condition guarding a stack line is the prime suspect.

2. **The suite could not import the package.** `_import_root_dirs` walked only parents, so a `src/`
   layout was invisible; the baseline then failed for its import, every candidate scored the same as
   the baseline, and the search reported no verified repair. Rooted at `src/` the same search found
   the repair in 12 seconds.

These tests use small synthetic files: they pin the arithmetic that decides what gets tried, which is
the part that silently returns "no repair exists".
"""
from __future__ import annotations

import ast
import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as coupled  # noqa: E402
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as search  # noqa: E402


# ------------------------------------------------------------------ 1. the branch that raised

PLUGGY_SHAPE = textwrap.dedent('''
    def register(self, plugin):
        for hook_name in ("a", "b", "c"):
            hook = getattr(self.hook, hook_name, None)
            if hook is None:
                hook = make(hook_name)
            elif not verified or hook.has_spec():
                # An earlier impl's replay added this spec after the first pass.
                # Failing here leaves the plugin partially registered, but only
                # user code during replay can get here.
                self._verify_hook(hook, hookimpl)
            hook._add_hookimpl(hookimpl)
        return hook_name
''').strip("\n")


def _lines_of(source: str) -> dict[str, int]:
    return {ln.split("#")[-1].strip() if "#" in ln else ln.strip(): i + 1
            for i, ln in enumerate(source.splitlines())}


def test_the_condition_guarding_a_stack_line_is_named() -> None:
    """The rule: a frame inside an `if` body implicates that `if`'s own line."""
    tree = ast.parse(PLUGGY_SHAPE)
    lines = _lines_of(PLUGGY_SHAPE)
    raise_line = lines["self._verify_hook(hook, hookimpl)"]
    condition_line = lines["elif not verified or hook.has_spec():"]
    assert coupled._branch_condition_lines(tree, {raise_line}) == {condition_line}


def test_a_frame_outside_any_branch_implicates_nothing() -> None:
    """No guessed bonus when the stack is not inside a guarded body."""
    tree = ast.parse(PLUGGY_SHAPE)
    assert coupled._branch_condition_lines(tree, {1}) == set()
    assert coupled._branch_condition_lines(tree, set()) == set()


def test_the_condition_outranks_a_merely_nearby_site() -> None:
    """The measured crowding-out: proximity 4 must beat eight constants at proximity 3.

    This is the exact ordering that failed: 9600 for the true site against 9700 for trivia that
    happened to sit closer to a different frame.
    """
    tree = ast.parse(PLUGGY_SHAPE)
    lines = _lines_of(PLUGGY_SHAPE)
    raise_line = lines["self._verify_hook(hook, hookimpl)"]
    condition_line = lines["elif not verified or hook.has_spec():"]
    assert condition_line == raise_line - 4

    cond = coupled._focus_bonus(condition_line, {raise_line})
    trivia = coupled._focus_bonus(condition_line + 2, {raise_line})
    assert trivia > cond, "the premise of the bug: proximity alone prefers the wrong site"
    # ...and the branch rule is what fixes it.
    assert condition_line in coupled._branch_condition_lines(tree, {raise_line})
    assert coupled.FOCUS_CONDITION_BONUS > coupled.FOCUS_BONUS_MAX


def test_the_focus_bonus_decays_and_never_goes_negative() -> None:
    assert coupled._focus_bonus(100, {100}) == coupled.FOCUS_BONUS_MAX
    assert coupled._focus_bonus(105, {100}) < coupled._focus_bonus(101, {100})
    assert coupled._focus_bonus(100 + coupled.FOCUS_WINDOW_LINES + 1, {100}) == 0
    assert coupled._focus_bonus(100, set()) == 0
    # Clamped, so distance can never reorder two sites behind an unfocused one.
    assert coupled._focus_bonus(10_000, {100}) >= 0


# ------------------------------------------------------------------ 2. the package must import

def _layout(tmp_path: pathlib.Path, *, src: bool) -> tuple[pathlib.Path, pathlib.Path]:
    """A repository with a package called `pkg` and one test that imports it by name."""
    repo = tmp_path / "repo"
    pkg_dir = repo / "src" / "pkg" if src else repo / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "core.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    test_file = tests / "test_core.py"
    test_file.write_text(
        "from pkg.core import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
    return repo, test_file


def test_a_src_layout_is_on_the_import_path(tmp_path: pathlib.Path) -> None:
    """The defect: rooted at the repository, `src/pkg` was invisible and nothing could import."""
    repo, test_file = _layout(tmp_path, src=True)
    env = search._source_env(repo, test_file)
    parts = [p for p in env.get("PYTHONPATH", "").split(":") if p]
    assert str(repo / "src") in parts, parts


def test_a_flat_layout_still_works(tmp_path: pathlib.Path) -> None:
    """The fix must not break the layout that already worked."""
    repo, test_file = _layout(tmp_path, src=False)
    env = search._source_env(repo, test_file)
    parts = [p for p in env.get("PYTHONPATH", "").split(":") if p]
    assert str(repo) in parts, parts


def test_only_a_package_the_tests_name_is_added(tmp_path: pathlib.Path) -> None:
    """`src/` is added because `pkg` lives there, never merely because it exists.

    The safety property inherited from the parent walk: a directory is put on sys.path only when it
    CONTAINS a package the suite imports, so an unrelated `src/` can never shadow a module.
    """
    repo, test_file = _layout(tmp_path, src=True)
    (repo / "src" / "unrelated").mkdir()
    (repo / "src" / "unrelated" / "__init__.py").write_text("", encoding="utf-8")
    dirs = search._import_root_dirs([str(repo)], [str(test_file)])
    assert str(repo / "src") in dirs

    empty = tmp_path / "other"
    (empty / "src").mkdir(parents=True)
    assert search._import_root_dirs([str(empty)], [str(test_file)]) == []

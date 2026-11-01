"""A closed-loop solve must not leave its scratch copy installed in the caller's imports.

History (measured 2026-11-01). `whitebox_introspector_and_trace_synthesizer_v1.harvest_live_io_examples`
executes the project's own test files in the *calling* interpreter to capture live I/O examples. Those
test files really import their project (`from pkg.service import frame_length`), so `sys.modules["pkg"]`
was permanently bound to `/tmp/brain_closed_loop_repo_*/worktree/pkg` -- a directory deleted as soon as
the solve returned. The harvest code restored `sys.path` and `sys.bytecode` flags but never `sys.modules`.

The user-visible consequence was found as an unexplained cross-file test failure: after
`test_three_pillar_swe_breakthroughs_v1` ran one two-file repair, an unrelated acquisition test that
imported its *own* top-level package named `pkg` got the dead module instead, its repair verification
returned `OBSERVED=False`, and the live-runtime task reported `FAIL_CLOSED__CAPABILITY_RETURNED_A_VERDICT`.
It was a real defect in production code, not test interference: any process that solved one repository
and later imported a package of the same name was reading code from a removed directory.

These tests assert behaviour, not internals: after a solve, the name must still belong to whoever it
belonged to before, and a subsequent import of a different package with the same name must resolve to
that different package.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as closed_loop

_PKG_PROJ = (
    'def pack_uint(n: int) -> bytes:\n'
    '    return n.to_bytes(4, "big").strip(b"\\x00")\n'
)
_PKG_SVC = (
    'from pkg.encoder import pack_uint\n\n'
    'def frame_length(n: int, header: int) -> int:\n'
    '    return len(pack_uint(n)) - header\n'
)
_PKG_TEST = (
    'import unittest\n'
    'from pkg.service import frame_length\n\n'
    'class FrameTests(unittest.TestCase):\n'
    '    def test_coupled_protocol(self):\n'
    '        assert frame_length(256, 3) == 5 and frame_length(1, 3) == 4\n'
)


def _build_coupled_repo(root: pathlib.Path) -> pathlib.Path:
    """The two-file coupled bug used elsewhere: neither file alone turns the single test green."""
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "encoder.py").write_text(_PKG_PROJ, encoding="utf-8")
    (root / "pkg" / "service.py").write_text(_PKG_SVC, encoding="utf-8")
    (root / "tests" / "test_frame.py").write_text(_PKG_TEST, encoding="utf-8")
    return root


def _solve(root: pathlib.Path) -> dict:
    return closed_loop.solve_repository_closed_loop(
        root,
        goal="Fix frame_length and pack_uint protocol framing bug",
        apply_to_source=True,
        timeout_s=30.0,
    )


def _scratch_modules() -> list[str]:
    """Any module still bound to a closed-loop scratch worktree (deleted by now)."""
    leaked = []
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if isinstance(f, str) and "brain_closed_loop_repo_" in f:
            leaked.append(name)
    return sorted(leaked)


def test_solve_does_not_install_its_scratch_package_into_sys_modules(tmp_path: pathlib.Path) -> None:
    """Outbound leak: the project's own modules must not survive the solve."""
    for name in ("pkg", "pkg.encoder", "pkg.service", "tests"):
        sys.modules.pop(name, None)
    sys.path[:] = [p for p in sys.path if "brain_closed_loop_repo_" not in p]

    res = _solve(_build_coupled_repo(tmp_path / "repo1"))
    assert res["ok"] is True and res["verified"] is True, res
    assert "pkg" not in sys.modules, f"scratch package left behind: {sys.modules['pkg']!r}"
    assert _scratch_modules() == [], _scratch_modules()
    assert not [p for p in sys.path if "brain_closed_loop_repo_" in p]


def test_a_later_import_of_the_same_package_name_resolves_to_the_new_package(
    tmp_path: pathlib.Path,
) -> None:
    """The reported failure, end to end: solve repo A, then import repo B's own `pkg`.

    Before the fix this raised or returned a module whose `__file__` was inside a deleted /tmp
    worktree, so the second task's verification could not pass. The assertion is that the name
    resolves to the code the second caller actually wrote.
    """
    for name in ("pkg", "pkg.encoder", "pkg.service", "pkg.quota"):
        sys.modules.pop(name, None)
    importlib.invalidate_caches()

    _solve(_build_coupled_repo(tmp_path / "repo_a"))

    repo_b = tmp_path / "repo_b"
    (repo_b / "pkg").mkdir(parents=True)
    (repo_b / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo_b / "pkg" / "quota.py").write_text(
        "def calc_quota(n: int) -> int:\n    return (n << 1) + 5\n", encoding="utf-8"
    )
    sys.path.insert(0, str(repo_b))
    try:
        importlib.invalidate_caches()
        mod = importlib.import_module("pkg.quota")
        assert pathlib.Path(mod.__file__).resolve() == (repo_b / "pkg" / "quota.py").resolve(), mod.__file__
        assert mod.calc_quota(9) == 23
    finally:
        for name in ("pkg", "pkg.quota"):
            sys.modules.pop(name, None)
        if str(repo_b) in sys.path:
            sys.path.remove(str(repo_b))
    assert _scratch_modules() == [], _scratch_modules()


def test_a_package_the_caller_already_holds_is_given_back_untouched(tmp_path: pathlib.Path) -> None:
    """No-regression guard: setting the name aside must not cost the caller its module.

    Honest scope: this one passes with and without the fix. Measured 2026-11-01, a foreign `pkg`
    in `sys.modules` did not change the solve outcome, because the solver has other candidate
    sources -- so the inbound half of `_stash_project_modules` is a precaution, not a measured
    repair. What it guards is that the *fix itself* cannot silently break a caller that already
    imported the name, and that the repair still verifies while the name is set aside.
    """
    caller = tmp_path / "caller_pkg_home"
    (caller / "pkg").mkdir(parents=True)
    (caller / "pkg" / "__init__.py").write_text("MARKER = 'caller'\n", encoding="utf-8")
    sys.path.insert(0, str(caller))
    try:
        importlib.invalidate_caches()
        for name in ("pkg", "pkg.encoder", "pkg.service"):
            sys.modules.pop(name, None)
        caller_pkg = importlib.import_module("pkg")
        assert caller_pkg.MARKER == "caller"

        res = _solve(_build_coupled_repo(tmp_path / "repo2"))

        assert res["ok"] is True and res["verified"] is True, res
        assert sys.modules["pkg"] is caller_pkg, "caller's module was replaced by the scratch copy"
        assert caller_pkg.MARKER == "caller"
        assert pathlib.Path(caller_pkg.__file__).resolve() == (caller / "pkg" / "__init__.py").resolve()
    finally:
        for name in ("pkg", "pkg.encoder", "pkg.service"):
            sys.modules.pop(name, None)
        if str(caller) in sys.path:
            sys.path.remove(str(caller))
    assert _scratch_modules() == [], _scratch_modules()

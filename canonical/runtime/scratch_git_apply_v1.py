#!/usr/bin/env python3
"""Apply a unified diff to a scratch copy, without letting git escape to an enclosing repo.

Why this module exists
----------------------
Four gates -- `python.repo.diff_apply_full_testgate`, `python.review.diff_coverage_gate`,
`python.review.diff_mutation_gate`, `python.review.diff_perf_gate` -- materialise a scratch
copy of the tree under review and then run `git apply` inside it. All four copies live
inside the repository being reviewed, and all four are made with
``copytree(..., ignore=shutil.ignore_patterns(".git", ...))``, so the copy is *not* a git
repository.

`git apply` then walks UP the directory tree, finds the enclosing repository, and resolves
every path in the diff against THAT root instead of against the scratch copy. Measured on
`35265c5`, a one-line fixture diff against `canonical/astra_runtime/tmp/gate`:

    $ git -C <scratch> rev-parse --show-toplevel
    /home/user/brain                       # the enclosing repository, not the scratch copy
    $ git -C <scratch> apply -v fix.diff
    rc=0                                   # success
    err: Skipped patch 'calc.py'.
    $ cat <scratch>/calc.py
    return a - b                           # unchanged

Exit code 0, patch skipped, working tree untouched. Every one of those gates then ran the
suite against an unpatched tree, which is why `python.repo.diff_apply_full_testgate`
"never applies" -- it reported `gate: FAIL` with a named failing test that the diff was
supposed to fix, and it would have reported a false PASS on a suite that was already green.

The two mechanisms here
-----------------------
1. ``GIT_CEILING_DIRECTORIES`` is set to the scratch copy's parent, so git discovery stops
   before the enclosing repository and `apply` runs against the copy it was given.
2. The result is PROVEN, not trusted: the tree is fingerprinted before and after, and a
   patch that reports success while changing no byte is refused with
   ``DIFF_APPLIED_BUT_TREE_UNCHANGED``. `git apply` treating a skip as success is exactly
   the silent downgrade this repository forbids everywhere else.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess

#: Suffixes that are never part of a patch's effect and would make the fingerprint noisy.
_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

#: Refusals this module can return, in the vocabulary the gates already use.
CHECK_FAILED = "DIFF_DOES_NOT_APPLY"
APPLY_FAILED = "DIFF_APPLY_FAILED_AFTER_CHECK"
UNCHANGED = "DIFF_APPLIED_BUT_TREE_UNCHANGED"


def isolated_env(scratch: pathlib.Path) -> dict:
    """An environment in which git cannot see past the scratch copy.

    ``GIT_CEILING_DIRECTORIES`` must name a directory that git may not ascend above; the
    scratch copy's parent is that directory, so discovery stops there and the copy is
    treated as a plain tree (which is what `git apply` needs).
    """
    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = str(pathlib.Path(scratch).resolve().parent)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"
    # Keep the caller's identity out of it: `git apply` must never need one.
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def tree_fingerprint(root: pathlib.Path) -> dict:
    """sha256 per relative path, so "the patch was applied" is a fact and not a return code."""
    root = pathlib.Path(root)
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        out[str(rel).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def apply_to_scratch(diff_path, scratch, timeout_s: int = 60) -> tuple[str, str]:
    """Apply ``diff_path`` inside ``scratch`` and PROVE the tree changed.

    Returns ``("OK", "")`` or ``(refusal, detail)`` where refusal is one of the three
    constants above. Never raises for a patch problem; the caller owns its own error type.
    """
    diff_path = pathlib.Path(diff_path).resolve()
    scratch = pathlib.Path(scratch).resolve()
    if not diff_path.is_file():
        return CHECK_FAILED, "DIFF_PATH_MISSING:" + str(diff_path)
    env = isolated_env(scratch)
    before = tree_fingerprint(scratch)

    check = subprocess.run(["git", "apply", "--check", str(diff_path)],
                           cwd=str(scratch), capture_output=True, text=True,
                           timeout=timeout_s, env=env)
    if check.returncode != 0:
        line = (check.stderr.strip().splitlines() or ["<empty>"])[0][:200]
        return CHECK_FAILED, line

    applied = subprocess.run(["git", "apply", str(diff_path)],
                             cwd=str(scratch), capture_output=True, text=True,
                             timeout=timeout_s, env=env)
    if applied.returncode != 0:
        line = (applied.stderr.strip().splitlines() or ["<empty>"])[0][:200]
        return APPLY_FAILED, line

    after = tree_fingerprint(scratch)
    if after == before:
        # The measured silent-skip: rc 0, nothing written. This is the shape that made four
        # gates run their suites against an unpatched tree and call the result a verdict.
        return UNCHANGED, (applied.stderr.strip() or "git apply reported success and changed no byte")[:200]
    return "OK", ""

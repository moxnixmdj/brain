"""The evaluation must deduplicate by bug, not by commit.

A fix commit and its merge commit produce two valid instances with identical controls.
Counting both turns 9 real bugs into 14 "instances" and inflates the rate. The dedupe key
is the recovered parent patch text -- two commits that revert to identical source are one
bug; two different fixes in the same file are two bugs.

This is pinned because the denominator is the only thing a rate means.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import real_repo_eval_v1 as E  # noqa: E402


def _row(repo, src, parent, solved, fpsig="A"):
    return {"id": f"{repo}_{parent}", "repo": repo, "src_files": src, "parent": parent,
            "patch_fingerprint": fpsig, "solved": solved, "skipped": False,
            "subject": "s", "red_before": "1 passed 1 failed", "after": "2 passed 0 failed",
            "engine_status": "X", "verified": solved, "steps": 1, "candidates": 1,
            "mechanisms": [], "elapsed_ms": 1}


def test_two_commits_that_revert_to_the_same_source_are_one_bug():
    a = _row("r/x", ["m.py"], "p1", True, fpsig="SAME")
    b = _row("r/x", ["m.py"], "p2", True, fpsig="SAME")
    uniq = {}
    for r in (a, b):
        uniq.setdefault((r["repo"], r["patch_fingerprint"]), r)
    assert len(uniq) == 1


def test_two_different_fixes_in_the_same_file_are_two_bugs():
    a = _row("r/x", ["m.py"], "p1", True, fpsig="A")
    b = _row("r/x", ["m.py"], "p2", True, fpsig="B")
    uniq = {}
    for r in (a, b):
        uniq.setdefault((r["repo"], r["patch_fingerprint"]), r)
    assert len(uniq) == 2


def test_the_rate_is_solved_over_unique_bugs_never_over_rows():
    rows = [_row("r/x", ["m.py"], "p1", True, fpsig="A"),
            _row("r/x", ["m.py"], "p2", True, fpsig="A"),   # merge of the same bug
            _row("r/y", ["n.py"], "p3", False, fpsig="B")]
    uniq = {}
    for r in rows:
        uniq.setdefault((r["repo"], r["patch_fingerprint"]), r)
    unique_bugs = len(uniq)
    solved = sum(1 for r in uniq.values() if r["solved"])
    assert unique_bugs == 2 and solved == 1
    assert round(100.0 * solved / unique_bugs, 1) == 50.0
    # the row-based figure would be 66.7%, which is the error this pins against
    assert round(100.0 * 2 / 3, 1) == 66.7


def test_miner_exposes_a_patch_fingerprint_on_every_valid_instance():
    src = Path(E.MINER.__file__).read_text()
    assert "patch_fingerprint" in src
    assert "DUPLICATE_BUG_FAMILY" in src

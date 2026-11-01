"""Two cases must never share a fixture directory.

``build()`` names its directory after the case and **rmtree**s it before writing the fixture, so two
cases that share a label shared a directory and destroyed each other's tree mid-run.  The matrix did
exactly that: ``measure_coverage`` is registered twice -- once in the toolchain lane over ``pkg``,
once in the analysis lane over ``cov/calc.py`` -- so the aggregate count and the distinct-name count
disagreed by one (44 cases, 43 names) and the REAL list printed a name twice.

The directory is now keyed on registration index.  These tests pin that, and pin the reason it is
needed, so a future duplicate label cannot quietly merge two fixtures again.
"""
from __future__ import annotations

import re

from execution_guard.swe_capability_matrix_v1 import CASES, build


def test_every_case_has_its_own_directory():
    """The invariant: one registration, one directory."""
    dirs = [c["dir"] for c in CASES]
    assert len(dirs) == len(set(dirs)) == len(CASES)
    assert all(re.fullmatch(r"\d{3}_.+", d) for d in dirs)
    assert dirs == sorted(dirs), "registration order must be the order the matrix runs in"


def test_the_duplicate_label_that_caused_this_is_still_a_duplicate_and_still_isolated():
    """``measure_coverage`` is registered twice on purpose -- different lane, different fixture.

    This is the nearest world in which the fix matters: if the two are ever merged into one case the
    test should be updated, but while there are two, they must not share a directory.  Without the
    index keying the two ``dir`` values would be identical and this fails.
    """
    same = [c for c in CASES if c["name"] == "measure_coverage"]
    assert len({c["dir"] for c in same}) == len(same) == 2
    assert {c["lane"] for c in same} == {"toolchain", "analysis"}


def test_building_one_of_two_same_named_cases_leaves_the_other_alone():
    """The behavioural consequence, exercised on the real filesystem.

    The two directories are distinct paths, so writing one cannot rmtree the other.  This asserts the
    property that was actually broken rather than only the naming convention that fixes it.
    """
    same = [c for c in CASES if c["name"] == "measure_coverage"]
    a = build(same[0]["dir"])
    b = build(same[1]["dir"])
    try:
        assert a != b
        assert a.is_dir() and b.is_dir()
        # Re-building the first must delete only its own tree.
        build(same[0]["dir"])
        assert b.is_dir(), "rebuilding one case deleted the other case's fixture"
        assert (b / "cov" / "calc.py").is_file() or (b / "pkg" / "calc.py").is_file()
    finally:
        import shutil

        for p in (a, b):
            shutil.rmtree(p, ignore_errors=True)

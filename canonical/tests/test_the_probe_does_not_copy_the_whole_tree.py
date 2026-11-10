#!/usr/bin/env python3
"""The referent probe must not copy a tree to change one column.

MEASURED, this machine:
    small tree (1 file):        answer p50 10.1 ms -> 3.58 ms
    real tree (50 MB, 512 files): answer p50   97 ms -> 28 ms

The probe re-runs the door on a perturbed tree -- that is the strongest check in the
system and it is unchanged. What was wrong was HOW the perturbed tree was built:
`shutil.copyfile` on every file, i.e. `sendfile` of the entire tree (7.2 ms of 14 ms on
one file), to change one column of one table.

Only the perturbed file's CONTENT differs. Every other file is the same bytes, and a
hardlink IS the same bytes. Safe here for a specific reason: nothing in the probe writes
-- the copy is read by `ask`, the perturbed file is written fresh at the destination, and
every other link is only ever read.
"""
from __future__ import annotations

import os
import pathlib

import pytest

from canonical.runtime import autonomous_v1 as A
from canonical.runtime import referent_dependence_v1 as R

SALES = "region,amount\nnorth,100\nsouth,150\nwest,250\n"


@pytest.fixture()
def tree(tmp_path):
    (tmp_path / "sales.csv").write_text(SALES)
    (tmp_path / "other.csv").write_text("a,b\n1,2\n")
    return tmp_path


def test_the_probe_tree_links_instead_of_copying(tree):
    base = tree
    changed = base / "sales.csv"
    dest = R._build_probe_tree(base, changed, "region,amount\nnorth,1\n")
    assert dest
    try:
        d = pathlib.Path(dest)
        # the untouched file must be the SAME INODE, not a copy
        assert os.stat(base / "other.csv").st_ino == os.stat(d / "other.csv").st_ino, \
            "an unperturbed file was copied rather than linked"
        # the changed file must be a distinct inode with the new content
        assert os.stat(base / "sales.csv").st_ino != os.stat(d / "sales.csv").st_ino
        assert "north,1" in (d / "sales.csv").read_text()
    finally:
        R._cleanup(dest)


def test_the_original_tree_is_never_mutated(tree):
    before = (tree / "sales.csv").read_text()
    dest = R._build_probe_tree(tree, tree / "sales.csv", "region,amount\nnorth,999999\n")
    try:
        assert (tree / "sales.csv").read_text() == before, "the live tree was modified"
    finally:
        R._cleanup(dest)


def test_a_perturbed_probe_still_changes_the_answer(tree):
    """The probe's PURPOSE is unchanged: a different column value must move the answer."""
    dest = R._build_probe_tree(tree, tree / "sales.csv", "region,amount\nnorth,1\nsouth,1\nwest,1\n")
    try:
        original = A.run(goal="what is the total of the amounts in sales.csv",
                         root=str(tree), iterations=8)
        moved = A.run(goal="what is the total of the amounts in sales.csv",
                      root=dest, iterations=8)
        assert original["verification"]["verified"] is True
        assert "500" in str(original.get("rendered"))
        assert "3" in str(moved.get("rendered")) and "500" not in str(moved.get("rendered"))
    finally:
        R._cleanup(dest)


def test_the_answer_is_still_verified_after_the_change(tree):
    out = A.run(goal="what is the total of the amounts in sales.csv",
                root=str(tree), iterations=8)
    assert out["verification"]["verified"] is True
    assert out["verification"]["reason"] == "ANSWER_GROUNDED"

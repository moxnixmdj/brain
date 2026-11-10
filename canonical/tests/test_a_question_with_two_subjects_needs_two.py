#!/usr/bin/env python3
"""A question naming two subjects and answered from one is a different question.

MEASURED FALSE PASS, this machine, this round:

    question: what is the total of the amounts in a.csv and b.csv
    a.csv = x:10,20   b.csv = x:30,40
    returned: 30      <- the total of a.csv alone
    verdict:  verified: true, reason: ANSWER_GROUNDED, grounded: 2/2

Every check that existed passed, and each asked the same question: is this EXPRESSION
sound against the file it chose to read? None asked whether the expression read every
subject the SENTENCE named. The single-file answer is bit-identical to a correct one --
a caller could not tell -- which is what makes this the dangerous class.

The fix is a fourth condition in `_answer_stands`: subject coverage. It reads the named
files out of the question itself, so the expression cannot satisfy it by agreeing with
itself.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.runtime import autonomous_v1 as A
from canonical.runtime import inspect_v1 as I

A_CSV = "x\n10\n20\n"
B_CSV = "x\n30\n40\n"


@pytest.fixture()
def tree(tmp_path):
    (tmp_path / "a.csv").write_text(A_CSV)
    (tmp_path / "b.csv").write_text(B_CSV)
    return str(tmp_path)


def test_two_named_subjects_answered_from_one_is_not_a_pass(tree):
    out = A.run(goal="what is the total of the amounts in a.csv and b.csv",
                root=tree, iterations=8)
    v = out.get("verification") or {}
    assert v.get("verified") is False, (
        "a single-file total was reported verified for a two-file question: " + repr(v))
    assert v.get("reason") == "PARTIAL_ANSWER"


def test_one_named_subject_is_unchanged(tree):
    out = A.run(goal="what is the total of the amounts in a.csv", root=tree, iterations=8)
    v = out.get("verification") or {}
    assert v.get("verified") is True
    assert v.get("reason") == "ANSWER_GROUNDED"
    assert "30" in str(out.get("rendered"))


def test_the_conjunction_is_what_makes_coverage_matter(tree):
    """`and` joining two PATHS is not prose; two paths without `and` is not this case."""
    two_with_and = I._subject_coverage(
        "what is the total of the amounts in a.csv and b.csv", {"node": None}, tree)
    assert two_with_and["complete"] is False
    one = I._subject_coverage(
        "what is the total of the amounts in a.csv", {"node": None}, tree)
    assert one["complete"] is True


def test_coverage_never_breaks_a_question_it_cannot_read(tree):
    """An unparseable or absent subject must not turn a good answer into a refusal."""
    r = I._subject_coverage("what is the total in gone.csv and also_gone.csv",
                            {"node": None}, tree)
    assert r["complete"] is True
    r2 = I._subject_coverage("", {"node": None}, tree)
    assert r2["complete"] is True

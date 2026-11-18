"""The two organs of round 11, tested where they can be tested without cloning anything.

Round 11 measured, on seven real fix commits, that the failing run never produces a frame in the defective
file -- 7 of 7 -- so the traceback cannot localise and the experience is silent about its own site. What is
left is the failing test's own parameter partition. These tests pin the pieces of that claim: that the
negative set excludes every failing case (a sibling failure inside the negatives makes every predicate look
non-separating), that a separating predicate is found by real introspection of the target's own imports,
that the seat's own loop variable is what the term is bound to, and that the adjoined condition is the only
change made to the module.
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import operand_invention_v1 as O  # noqa: E402
from canonical.swe_kernel import real_commit_repair_v1 as R  # noqa: E402

TEST_SOURCE = '''
import pytest

@pytest.mark.parametrize("license_files", ["LICENSE", "C:LICENSE", "d:secrets/key.txt", "licenses/*"])
def test_invalid_license_files(license_files):
    with pytest.raises(ValueError):
        check_license_files(license_files)

@pytest.mark.parametrize("left,right", [(1, 2), (3, 4)])
def test_pair(left, right):
    assert left < right
'''

GUARDED = '''import pathlib


def check_license_files(value):
    for path in value:
        if ".." in path:
            raise ValueError(path)
    return value
'''


def test_failed_index_reads_the_case_number():
    assert O.failed_index("tests/t.py::test_x[license_files4]") == 4
    assert O.failed_index("tests/t.py::test_x[case-7]") == 7
    assert O.failed_index("tests/t.py::test_x") is None


def test_parametrized_values_keeps_one_table_per_function():
    tables = O.parametrized_values(TEST_SOURCE)
    assert tables["test_invalid_license_files"]["license_files"][1] == "C:LICENSE"
    assert tables["test_pair"]["left"] == [1, 3]
    assert tables["test_pair"]["right"] == [2, 4]


def test_differential_excludes_every_failing_case_from_the_negatives():
    # Both failing cases are excluded. Were only the current case excluded, the other failing value would
    # sit in the negatives and no predicate could separate -- which is exactly how this bug looked before.
    found = O.differential(TEST_SOURCE, ["tests/t.py::test_invalid_license_files[license_files1]",
                                         "tests/t.py::test_invalid_license_files[license_files2]"], GUARDED)
    assert found["failing"] == ["C:LICENSE", "d:secrets/key.txt"]
    assert "pathlib.PureWindowsPath(x).drive" in found["terms"]
    assert all(term.startswith("pathlib.") for term in found["terms"])


def test_separating_terms_are_read_from_the_targets_own_imports():
    terms = O.separating_terms(["C:LICENSE"], ["LICENSE", "licenses/*"], GUARDED)
    assert "pathlib.PureWindowsPath(x).drive" in terms
    assert all("pathlib." in term for term in terms)   # every term speaks the module the target imports


def test_separating_terms_is_empty_when_nothing_separates():
    assert O.separating_terms(["a"], ["b"], GUARDED) == []


def test_sites_from_parameter_finds_the_guards_of_the_function_that_handles_it():
    seats = O.sites_from_parameter(GUARDED, ["test_invalid_license_files.license_files"])
    assert [text for _, text in seats] == ["'..' in path"]


def test_bind_speaks_the_seats_own_name():
    seat = O.sites_from_parameter(GUARDED, ["license_files"])[0][0]
    assert O.bind("pathlib.PureWindowsPath(x).drive", seat, GUARDED) == "pathlib.PureWindowsPath(path).drive"


def test_rewritten_changes_one_condition_and_still_compiles():
    seats = O.sites_from_parameter(GUARDED, ["license_files"])
    line_of, condition = seats[0]
    out = O.rewritten(GUARDED, line_of, condition, "pathlib.PureWindowsPath(path).drive", "or")
    assert out is not None
    compile(out, "<candidate>", "exec")
    assert "or pathlib.PureWindowsPath(path).drive" in out
    assert out.count("raise ValueError") == GUARDED.count("raise ValueError")


def test_headline_names_the_solved_commit_and_its_operand():
    report = {"rows": [{"repo": "pypa/packaging", "state": O.SOLVED, "at_line": 766,
                        "operand": "pathlib.PureWindowsPath(path).drive", "operator": "or"}],
              "totals": {"tasks": 1, "solved": 1, "solved_fraction": 1.0, "trials": 1, "states": {O.SOLVED: 1}}}
    text = O.headline(report)
    assert "1 solved" in text and "PureWindowsPath(path).drive or" in text


def test_entries_named_by_test_prefers_public_functions_the_test_names():
    source = "def helper():\n    pass\n\ndef parse_email(x):\n    return x\n"
    assert R.entries_named_by_test(source, "parse_email('a')") == ["parse_email"]
    assert R.entries_named_by_test(source, "nothing here") == []


def test_changed_span_and_touches_agree_about_the_rewritten_line():
    before = "a = 1\nb = 2\nc = 3\n"
    after = "a = 1\nb = 20\nc = 3\n"
    spans = R.changed_span(before, after)
    assert spans == [(1, 2)]
    assert R.touches(spans, [(1, 2)]) and not R.touches(spans, [(0, 1), (2, 3)])


def test_real_commit_repair_names_its_refusals():
    assert R.REFUSED_NO_ENTRY.startswith("REFUSED__")
    assert R.REFUSED_NO_PROPOSAL.startswith("REFUSED__")
    assert R.MODEL_CALLS == 0 and O.MODEL_CALLS == 0

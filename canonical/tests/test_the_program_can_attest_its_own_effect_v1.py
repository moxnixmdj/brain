"""A third kind of evidence: the program checks the property it was asked to produce.

Two mechanisms already verify a result honestly.

* `_ROUND_TRIP` opens the file with the library that owns the format -- a table, and therefore a
  format the author never met is unverifiable rather than merely unknown.
* `verify_by_inverse` runs the tool's own stated inverse and compares bytes -- no table, but it
  answers only "was this the same bytes", which is a question about TRANSFORMS.

Neither can verify a PROPERTY of a text file. "sort input.txt into out.txt" produces a `.txt`, and
`.txt` is in `_FORMAT_ONLY` precisely because opening it as text proves nothing about whether it is
sorted. So the goal was refused with FORMAT_CARRIES_NO_EVIDENCE no matter what the machine could
prove -- while `sort` was sitting on PATH printing `-c, --check  check for sorted input` and able to
attest the very thing asked for.

This file pins the mechanism, and the two ways it must refuse:

* a flag that accepts EVERYTHING is not a check, so a control the flag rejects is required;
* if the control (the input) is also accepted, the property was already there and the action cannot
  be credited with producing it.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

from canonical.runtime import program_synthesis_v1 as ps

SORTED = "apple\nbanana\nmango\nzebra\n"
UNSORTED = "zebra\napple\nmango\nbanana\n"


def _files(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    good = tmp_path / "sorted.txt"
    bad = tmp_path / "unsorted.txt"
    good.write_text(SORTED, encoding="utf-8")
    bad.write_text(UNSORTED, encoding="utf-8")
    return good, bad


def test_the_check_flag_is_read_from_the_program_not_a_table():
    if shutil.which("sort") is None:
        pytest.skip("no sort on this host")
    assert ps._tools_check_flag("sort") == "-c"


def test_a_program_with_no_checker_says_so():
    if shutil.which("cat") is None:
        pytest.skip("no cat on this host")
    assert ps._tools_check_flag("cat") is None


def test_the_program_attests_its_own_output(tmp_path):
    if shutil.which("sort") is None:
        pytest.skip("no sort on this host")
    good, bad = _files(tmp_path)
    ok, why = ps.verify_by_self_check(good, {"program": "sort"}, must_fail=bad)
    assert ok is True, why
    assert why == "THE_PROGRAM_ATTESTED_ITS_OWN_OUTPUT"


def test_an_output_the_program_rejects_is_not_verified(tmp_path):
    if shutil.which("sort") is None:
        pytest.skip("no sort on this host")
    good, bad = _files(tmp_path)
    ok, why = ps.verify_by_self_check(bad, {"program": "sort"}, must_fail=good)
    assert ok is False
    assert why == "THE_PROGRAM_REJECTED_ITS_OWN_OUTPUT"


def test_an_input_that_already_has_the_property_cannot_be_credited(tmp_path):
    """The subtle one, and the reason the control must be the INPUT.

    If the check accepts the input as well as the output, then the property was there before the
    action ran. Crediting the action would be claiming it produced something it did not.
    """
    if shutil.which("sort") is None:
        pytest.skip("no sort on this host")
    good, _ = _files(tmp_path)
    ok, why = ps.verify_by_self_check(good, {"program": "sort"}, must_fail=good)
    assert ok is False
    assert why == "SELF_CHECK_ACCEPTED_THE_INPUT_SO_NOTHING_WAS_PRODUCED"


def test_no_control_means_no_pass(tmp_path):
    """A flag that returns 0 for everything is not a check. Refuse rather than believe it."""
    if shutil.which("sort") is None:
        pytest.skip("no sort on this host")
    good, _ = _files(tmp_path)
    ok, why = ps.verify_by_self_check(good, {"program": "sort"}, must_fail=None)
    assert ok is False
    assert why == "SELF_CHECK_NOT_SHOWN_TO_DISCRIMINATE"


def test_the_verifier_version_depends_on_the_self_check_rule(monkeypatch):
    """The trap this mechanism fell into, pinned so it cannot be fallen into again.

    `remember_miss` keys a learned refusal on the verifier's version, on the stated grounds that
    "a better verifier can make a shape solvable that was not". Adding the self-check changed what
    is provable, so the version must move with it -- otherwise a goal refused before the checker
    existed stays refused forever and the fix can never reach the machine that learned the wrong
    answer. Measured: `sort input.txt into out.txt` refused in a directory whose memory predated
    this rule, and passed in a fresh one.

    This asserts the version really does depend on the rule, by changing the rule and requiring
    the version to move. A test that merely read the constant back would pass whatever the code did.
    """
    before = ps.verifier_version()
    monkeypatch.setattr(ps, "_CHECK_WORDS", tuple(ps._CHECK_WORDS) + ("__probe__",))
    after = ps.verifier_version()
    assert before != after, "the verifier version ignores the self-check rule, so stale refusals survive"

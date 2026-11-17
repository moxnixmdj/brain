"""Tests for THE_REFUSE_SHARE_V1.

These tests are mostly about the INSTRUMENT, not the world, because the instrument is what this
module had to get right. Three bugs were found and fixed while building it, and each has a test:

  1. the NAIVE experiment (git revert; run tests) removes the tests along with the fix, so it
     scores a pass for a commit the repository actually does guard;
  2. a blob-filtered clone of a historical commit produced a `tests/` tree with no sources, so a
     harness failure looked like an unguarded commit;
  3. requiring a GREEN baseline discarded every repository with a pre-existing failure, which is an
     instrument rule masquerading as a finding.

The last one matters most: GUARDED is judged RELATIVE to the baseline, which is what makes a
repository that already has one failing test as usable as one that has none.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/brain")

from canonical.swe_kernel import the_refuse_share_v1 as R  # noqa: E402


# -- the test/source split is a declared rule, not a judgement -------------------- #


def test_test_path_rule_is_blunt_and_declared():
    assert R.is_test_path("tests/test_version.py")
    assert R.is_test_path("src/pkg/tests/test_x.py")
    assert R.is_test_path("conftest.py")
    assert not R.is_test_path("packaging/version.py")
    assert not R.is_test_path("docs/index.md")


def test_the_rule_is_reported_so_a_reader_can_disagree_with_it():
    receipt = json.loads(Path("canonical/verification/THE_REFUSE_SHARE_20261116_V1.json").read_text())
    assert receipt["method"]["test_path_rule"] == list(R.TEST_MARKERS)


# -- the naive experiment, and why it is rejected -------------------------------- #


def test_the_naive_experiment_is_named_as_wrong_in_the_method(report):
    """`git revert` also reverts the tests, which is why the honest experiment holds them fixed."""
    assert "WRONG" in report["method"]["naive"]
    assert "hold tests at the post-commit state" in report["method"]["honest"]


def test_the_naive_experiment_is_shown_to_have_missed_real_cases(report):
    """If it never missed anything, the honest experiment would not have been worth building."""
    assert report["totals"]["naive_experiment_would_have_missed"] >= 1


# -- the control: an instrument failure is never a finding ----------------------- #


def test_every_excluded_repository_is_recorded_as_an_instrument_limit(report):
    for limit in report["instrument_limits"]:
        assert ":" in limit
        assert any(word in limit for word in
                   ("BASELINE", "EDITABLE", "NO_GUARDED", "CLONE", "TIMEOUT"))


def test_excluded_repositories_contribute_no_rows(report):
    """A repo that never produced a GUARDED verdict is excluded, not counted as unguarded."""
    excluded = {limit.split(":")[0] for limit in report["instrument_limits"]
                if "NO_GUARDED_RESULT" in limit}
    for row in report["rows"]:
        # a repository excluded for an unproven harness contributes NO graded verdicts
        if row["repo"] in excluded:
            assert row["status"] not in ("GUARDED", "UNGUARDED")
        assert row["status"] in ("GUARDED", "UNGUARDED", "NO_NON_TEST_FILES",
                                 "HARNESS_DID_NOT_RUN")


def test_a_repository_with_a_pre_existing_failure_is_still_usable(report):
    """click carries 1 pre-existing failure at baseline; it must still yield verdicts.

    This is the bug that mattered: judging 'is the suite green' discards real repositories. Judging
    'did the revert make it WORSE than baseline' does not.
    """
    click_rows = [r for r in report["rows"] if r["repo"] == "pallets/click"]
    assert click_rows, "click must be measured, not excluded as a broken harness"
    assert any(r["status"] == "GUARDED" for r in click_rows)


# -- the result ------------------------------------------------------------------ #


def test_the_totals_are_internally_consistent(report):
    totals = report["totals"]
    assert totals["guarded"] + totals["unguarded"] == totals["commits_measured"] == len(report["rows"])
    if totals["commits_measured"]:
        assert totals["refuse_share"] == totals["unguarded"] / totals["commits_measured"]


def test_the_verdict_is_relative_to_the_baseline_not_to_zero(report):
    """GUARDED means the revert made the suite WORSE than baseline, not that the suite is green.

    click carries one pre-existing failure at baseline, so an UNGUARDED row on click can legitimately
    report honest_failed == 1: the revert changed nothing, because that failure was already there.
    A test asserting "UNGUARDED => zero failures" would be asserting the wrong rule, and would have
    forced the harness back to the green-baseline requirement this module deliberately removed.
    """
    for row in report["rows"]:
        if row["status"] == "GUARDED":
            assert row["honest_failed"] > 0 or row["honest_errors"] > 0
        elif row["status"] == "UNGUARDED":
            # never worse than baseline; a pre-existing failure may still be present
            assert row["honest_failed"] <= row.get("baseline_failed", row["honest_failed"])
    # The concrete case that proves the relative rule is actually exercised: at least one UNGUARDED
    # row carries a pre-existing failure. If this ever stops holding, the green-baseline bug has
    # crept back in and the test says so.
    assert any(r["status"] == "UNGUARDED" and r["honest_failed"] > 0
               for r in report["rows"]), "no UNGUARDED row carries a baseline failure"


def test_every_guarded_commit_is_a_behaviour_change_not_a_docs_or_release_change(report):
    """The measured split has a clean shape: behaviour is guarded, documentation is not."""
    guarded = [r for r in report["rows"] if r["status"] == "GUARDED"]
    for row in guarded:
        subject = row.get("subject", "").lower()
        assert "changelog" not in subject
        assert "docs" not in subject


def test_the_receipt_states_what_it_is_not(report):
    caveats = " ".join(report["caveats"])
    assert "can be correct and still unguarded" in caveats
    assert "pytest only" in caveats


def test_authority_is_none_and_no_model_was_used(report):
    assert report["authority"].startswith("NONE")
    assert report["model_calls"] == 0
    assert report["producer_cognition_model_dependency_count"] == 0


# -- fixture --------------------------------------------------------------------- #


import pytest  # noqa: E402


@pytest.fixture(scope="module")
def report():
    path = Path("canonical/verification/THE_REFUSE_SHARE_20261116_V1.json")
    return json.loads(path.read_text())

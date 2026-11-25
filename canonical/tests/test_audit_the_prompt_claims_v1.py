#!/usr/bin/env python3
"""The prompt's claims, audited against the tree rather than argued about.

Read from the artifact:

    repo commits                      25
    identifiers claimed               19
      exist as CODE files              4   (same_identity_supervisor, consistency_vs_equivalence,
                                            zygote_worker_pool_v1, witness_inversion_v1)
      mentioned in code, no module    15
    commit hashes claimed              9   all 9 FAILED -- none resolves to a commit here
    numeric figures claimed            6   all unverified outside my own reports

Two of the four that exist had to be found, and one of the audit's own early versions counted report
filenames as modules -- the audit committed the error it exists to catch, which is why the suffix filter
and this test are both here.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import audit_the_prompt_claims_v1 as audit  # noqa: E402

ARTIFACT = REPO / "canonical" / "verification" / "AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json"


def test_no_claimed_commit_hash_resolves():
    """Every hash the prompt calls a commit of ours -- 209bbc6c, 92b6db85, d6c1661a, the five "logged
    unsolved" commits -- fails to resolve in this repository."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["no_claimed_commit_hash_resolves"] is True
    assert summary["tallies"]["commits_verified"] == 0
    assert summary["tallies"]["commits_failed"] == len(audit.COMMITS)


def test_the_audit_counts_only_executable_files_as_modules():
    """The self-caught defect: a `.md` report or a `.yml` workflow named after an engine is not the
    engine. Probe it directly rather than trusting the tally."""
    assert audit.files_named("typed_invention_v1") == [], (
        "only a report mentions this; it must not count as a module")
    assert audit.files_named("zygote_worker_pool_v1"), "this one genuinely exists as code"


def test_the_four_that_exist_are_named():
    """Being wrong in the other direction is equally dishonest: four claimed components are real."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert set(summary["components_that_do_exist"]) == {
        "same_identity_supervisor", "consistency_vs_equivalence",
        "zygote_worker_pool_v1", "witness_inversion_v1"}
    assert summary["verdicts"]["some_claimed_components_do_exist_as_code"] is True


def test_the_repo_is_far_smaller_than_the_prompt_implies():
    """244 verified commits, Iteration 83/84, a 75.2% measurement and a 344-case suite are all claims
    about a project this checkout is not."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["repo_commits"] < 30
    assert summary["verdicts"]["the_repo_cannot_have_244_commits_if_it_has_fewer"] is True
    assert summary["tallies"]["figures_unverified"] == len(audit.FIGURES)

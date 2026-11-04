"""The oracle must judge from the artifact, never from the adapter's own word.

Every test here exists because the instrument was already wrong in that exact way, or because a
plausible version of it would be and nobody would notice:

  * `archive.tar_gz.create_from_manifest` reported `output_verified: true` over a bundle that
    contained none of the files the caller asked for. It was found by reading the tarball
    instead of the adapter's return value, on 2026-11-04. A test that trusted `output_verified`
    would have called that a pass for two years.
  * a refusal (`ARCHIVE_MEMBER_SOURCE_MISSING`) is a *good* outcome. An oracle that scored
    refusals as failures would push the system toward pretending.
  * `distrust` is evidence-weighted. Permanent penance is a grudge, not a belief; and one
    confirming pass is not enough, because the pass could be the input that already failed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import executed_effect_oracle_v1 as oracle  # noqa: E402


# --------------------------------------------------------------------------- the verdict
def test_a_silent_drop_is_caught_by_the_artifact_not_by_the_return_value():
    """The defect this module exists for, re-created from the adapter as it was before the fix.

    The pre-fix adapter silently dropped every manifest path that did not start with
    `canonical/` and still reported `output_verified: true`. If this test ever passes with
    EFFECT_HELD against the old source, the oracle has started believing the adapter.
    """
    old = oracle.git_show("ec230a32e4", "canonical/runtime/bound_capabilities/archive_tarfile.py")
    if old is None:
        pytest.skip("the pre-fix adapter is not reachable in this clone")
    situation = oracle.situation_plain_relative_archive()
    row = oracle.run_situation(situation, adapter_source=old, adapter_label="prefix_filtering")
    assert row["verdict"] == "INPUTS_IGNORED_SILENTLY", row
    assert row["self_report"].get("output_verified") is True, (
        "the fixture must reproduce a success claim, or the test proves nothing")
    assert "m.json" in row["independent_check"]["members"]
    assert "notes.txt" not in row["independent_check"]["members"]


def test_the_same_situation_passes_against_the_current_adapter():
    """Before/after on the same world. The repair is only a repair if this changed."""
    situation = oracle.situation_plain_relative_archive()
    row = oracle.run_situation(situation)
    assert row["verdict"] == "EFFECT_HELD", row
    assert {"notes.txt", "report.md"} <= set(row["independent_check"]["members"])


def test_a_named_refusal_is_not_scored_as_a_failure():
    """The system saying no to a world that does not fit its contract is the outcome we want."""
    row = oracle.run_situation(oracle.situation_missing_input_archive())
    assert row["verdict"] == "REFUSED_AS_DECLARED"
    assert "ARCHIVE_MEMBER_SOURCE_MISSING" in row["refusal"]


def test_a_claimed_effect_with_no_artifact_is_a_contradiction(tmp_path):
    """Nothing written, but a success reported: the clearest possible lie."""

    class Fake:
        capability_id = "archive.tar_gz.create_from_manifest"

        def run(self, args, root):
            return {"output_verified": True}

    situation = oracle.Situation(
        name="claims_without_writing",
        capability_id="archive.tar_gz.create_from_manifest",
        build=lambda root: {"output_path": "never.tar.gz"},
        supplied=lambda root: ["x.txt"],
        artifact=lambda args, root: [root / args["output_path"]],
    )
    real = oracle.load_adapter
    oracle.load_adapter = lambda name: Fake()
    try:
        row = oracle.run_situation(situation)
    finally:
        oracle.load_adapter = real
    assert row["verdict"] == "SELF_REPORT_CONTRADICTS_ARTIFACT", row


def test_the_oracle_says_what_it_could_not_check():
    """A verdict with no record of its check kind is an opinion."""
    row = oracle.run_situation(oracle.situation_prefixed_archive())
    assert row["independent_check"]["kind"] == oracle.INDEPENDENT_CHECK_KIND
    report = oracle.measure()
    assert report["what_this_cannot_see"]
    assert any("semantic" in line for line in report["what_this_cannot_see"])


# --------------------------------------------------------------------------- learning
def _row(capability, verdict, situation="s"):
    return {"situation": situation, "capability": capability, "verdict": verdict,
            "supplied": [], "self_report": {}, "refusal": None, "elapsed_s": 0.0}


def test_a_contradiction_demotes_the_self_report():
    experience = {"executions": [], "distrust": {}, "consequences": []}
    oracle.record(experience, _row("cap.a", "INPUTS_IGNORED_SILENTLY"))
    assert oracle.may_trust_self_report(experience, "cap.a") is False
    assert experience["distrust"]["cap.a"]["strikes"] == 1


def test_one_confirmation_does_not_restore_a_demoted_capability():
    """The confirming pass could be the very input that already failed."""
    experience = {"executions": [], "distrust": {}, "consequences": []}
    oracle.record(experience, _row("cap.a", "INPUTS_IGNORED_SILENTLY"))
    oracle.record(experience, _row("cap.a", "EFFECT_HELD"))
    assert oracle.may_trust_self_report(experience, "cap.a") is False
    oracle.record(experience, _row("cap.a", "EFFECT_HELD"))
    assert oracle.may_trust_self_report(experience, "cap.a") is True, (
        "distrust is evidence-weighted; enough confirmations must earn the word back")


def test_an_undemoted_capability_is_unaffected():
    experience = {"executions": [], "distrust": {}, "consequences": []}
    assert oracle.may_trust_self_report(experience, "cap.b") is True
    oracle.record(experience, _row("cap.b", "EFFECT_HELD"))
    assert oracle.may_trust_self_report(experience, "cap.b") is True


# --------------------------------------------------------------------------- honesty
def test_the_denominator_is_the_capabilities_it_could_actually_situate():
    """2 of 141 is the honest figure. Reporting 141 would be the oldest lie in benchmarking."""
    report = oracle.measure()
    c = report["corpus"]
    assert c["capabilities_in_registry"] == 141
    assert c["situated_capabilities"] == len({r["capability"] for r in report["rows"]})
    assert c["situated_capabilities"] < c["capabilities_in_registry"]
    assert c["cannot_situate"] == c["capabilities_in_registry"] - c["situated_capabilities"]
    assert "no fixture builder" in c["why_not"]


def test_the_regression_replay_records_who_authored_the_repair():
    got = oracle.regress(rev="ec230a32e4")
    assert got["changed"] == 1, got
    assert "authored by the agent" in got["note"], (
        "crediting the system with a repair it did not make is the failure this repo "
        "punishes hardest")


def test_the_report_claims_no_capability():
    report = oracle.measure()
    assert report["authority"] == "NO_CAPABILITY_CREDIT_EXECUTION_MEASUREMENT_ONLY"
    assert "RUNNING_ONE_CAPABILITY_IS_NOT_CAPABILITY" in " ".join(report["non_claims"])
    assert "A_REFUSAL_IS_A_GOOD_OUTCOME" in " ".join(report["non_claims"])

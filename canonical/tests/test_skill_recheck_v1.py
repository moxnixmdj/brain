#!/usr/bin/env python3
"""A rule that has been taught is not a rule that has been shown to hold.

These tests exist to prove the recheck can FAIL. If every stored rule returns ABSENT or PASS
and nothing can contradict it, the check is decoration -- the same defect it was written to
catch, one level up.

The three verdicts are held apart deliberately:
    PASS    the rule re-applied now still produces the stored rewrite
    FAIL    it does not -- the rule is stale, or the world moved under it
    ABSENT  the rule carries no source, so it can never be re-checked
ABSENT must never be counted as a pass.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from canonical.swe_kernel import skill_recheck_v1 as R
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

BEFORE = "def f(x):\n    return x <= 0\n"
AFTER = "def f(x):\n    return x < 0\n"


def _taught_rule(tmp_path: pathlib.Path) -> dict:
    """A rule taught the normal way, read back out of the store as JSON."""
    db = tmp_path / "store.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    result = store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    )
    assert result.get("crystallized") is True, result
    row = sqlite3.connect(str(db)).execute(
        "SELECT pattern_json FROM crystallized_skills").fetchone()
    return json.loads(row[0])


# ---------------------------------------------------------------------------
# the demo is stored, so a rule can be re-executed at all
# ---------------------------------------------------------------------------
def test_a_newly_taught_rule_stores_the_text_it_was_taught_on(tmp_path):
    rule = _taught_rule(tmp_path)
    sources = rule["provenance"]["taught_sources"]
    assert sources == [{"before": BEFORE, "after": AFTER}]
    # the hash is kept beside the text, so the two can be compared
    assert rule["provenance"]["before_sha256"]
    assert rule["provenance"]["after_sha256"]


def test_a_newly_taught_rule_rechecks_PASS(tmp_path):
    assert R.recheck(_taught_rule(tmp_path))["verdict"] == R.PASS


# ---------------------------------------------------------------------------
# the check can fail -- the whole reason this module exists
# ---------------------------------------------------------------------------
def test_a_rule_whose_stored_rewrite_no_longer_matches_FAILS(tmp_path):
    """A stale rule must be caught, not silently trusted."""
    rule = _taught_rule(tmp_path)
    rule["provenance"]["taught_sources"][0]["after"] = "def f(x):\n    return x != 0\n"
    outcome = R.recheck(rule)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "REWRITE_DIFFERS_FROM_TAUGHT"


def test_a_rule_that_no_longer_applies_to_its_source_FAILS(tmp_path):
    """The taught source changed under the rule: pattern does not match any more."""
    rule = _taught_rule(tmp_path)
    rule["provenance"]["taught_sources"][0]["before"] = "def g(y):\n    return y + 1\n"
    outcome = R.recheck(rule)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "RULE_NO_LONGER_APPLIES"


def test_a_rule_whose_applier_raises_FAILS_and_reports_why():
    rule = {"pattern_tokens": [], "replacement_tokens": [],
            "provenance": {"taught_sources": [{"before": "x", "after": "y"}]}}

    def exploding(_source, _rule):
        raise RuntimeError("boom")

    outcome = R.recheck(rule, apply=exploding)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "APPLY_RAISED:RuntimeError"


# ---------------------------------------------------------------------------
# ABSENT is a missing measurement, never a pass
# ---------------------------------------------------------------------------
def test_a_rule_without_a_taught_source_is_ABSENT_not_PASS():
    outcome = R.recheck({"pattern_tokens": [["ident", "x"]], "replacement_tokens": []})
    assert outcome["verdict"] == R.ABSENT
    assert outcome["reason"] == "NO_TAUGHT_SOURCE"


def test_the_review_wording_is_kept_out_of_the_verdict():
    """ABSENT must not be reported as recheckable in the store summary either."""
    report = {"counts": {R.PASS: 0, R.FAIL: 0, R.ABSENT: 5}}
    assert report["counts"][R.PASS] + report["counts"][R.FAIL] == 0


# ---------------------------------------------------------------------------
# the store-level report
# ---------------------------------------------------------------------------
def test_store_report_counts_each_verdict_separately(tmp_path):
    db = tmp_path / "store.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    assert store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    ).get("crystallized") is True

    # a second row with no teachable source, inserted directly: the pre-2026-11-12 shape
    conn = sqlite3.connect(str(db))
    with conn:
        conn.execute(
            "INSERT INTO crystallized_skills (skill_id, domain, language, error_class,"
            " skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("legacy_row", "code_edit", "python", "BOUNDARY", "fp",
             json.dumps({"pattern_tokens": [], "replacement_tokens": []}), 0, 1, "[]"))
    conn.close()

    report = R.recheck_store(db)
    assert report["total"] == 2
    assert report["counts"][R.PASS] == 1
    assert report["counts"][R.ABSENT] == 1
    assert report["recheckable"] == 1
    assert R.main(["--db", str(db)]) == 0


def test_store_report_is_red_when_a_stored_rule_has_gone_stale(tmp_path):
    db = tmp_path / "store.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    )
    conn = sqlite3.connect(str(db))
    with conn:
        row = conn.execute("SELECT skill_id, pattern_json FROM crystallized_skills").fetchone()
        rule = json.loads(row[1])
        rule["provenance"]["taught_sources"][0]["after"] = "def f(x):\n    return False\n"
        conn.execute("UPDATE crystallized_skills SET pattern_json=? WHERE skill_id=?",
                     (json.dumps(rule), row[0]))
    conn.close()

    report = R.recheck_store(db)
    assert report["counts"][R.FAIL] == 1
    assert R.main(["--db", str(db)]) == 1


def test_a_missing_store_is_reported_as_unmeasurable_not_as_zero_rules(tmp_path):
    """0 rules and 'could not open the store' must not look the same."""
    report = R.recheck_store(tmp_path / "nope.sqlite")
    assert report["error"] == "DB_ABSENT"
    assert R.main(["--db", str(tmp_path / "nope.sqlite")]) == 2

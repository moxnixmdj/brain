#!/usr/bin/env python3
"""A sequence of verified skills is not a verified sequence.

The tests below are built around the measured case: two rules, each accepted by
`crystallize_code_fix`, that apply cleanly in order and leave the text exactly where it
started. Every per-step check passes. The sequence is a no-op.

If this file ever goes green while `test_two_verified_skills_that_revert_are_FAIL` passes
trivially, the check is decoration. So that test is written first and asserts the revert is
named, not merely detected.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from canonical.swe_kernel import skill_sequence_verify_v1 as S
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

FORWARD_BEFORE = "def f(x):\n    return x <= 10\n"
FORWARD_AFTER = "def f(x):\n    return x < 10\n"
BACKWARD_BEFORE = "def f(x):\n    return x < 10\n"
BACKWARD_AFTER = "def f(x):\n    return x <= 10\n"


def _store_with_two_opposing_rules(tmp_path: pathlib.Path) -> list[dict]:
    db = tmp_path / "s.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    for before, after, ec in (
        (FORWARD_BEFORE, FORWARD_AFTER, "A"),
        (BACKWARD_BEFORE, BACKWARD_AFTER, "B"),
    ):
        result = store.crystallize_code_fix(before_snippet=before, after_snippet=after,
                                            language="python", error_class=ec)
        assert result.get("crystallized") is True, result
    conn = sqlite3.connect(str(db))
    try:
        return [json.loads(row[0]) for row in
                conn.execute("SELECT pattern_json FROM crystallized_skills")]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# the measured defect
# ---------------------------------------------------------------------------
def test_two_verified_skills_that_revert_are_FAIL(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    outcome = S.verify_sequence(FORWARD_BEFORE, rules)

    assert outcome["verdict"] == S.FAIL
    assert outcome["reason"] == "STEP_REVERTED_EARLIER_STATE:step2"
    # the trace must name WHICH state it went back to, or the report is useless
    assert outcome["reverted_to_step"] == 0
    assert outcome["steps"][0]["outcome"] == "CHANGED"
    assert outcome["steps"][1]["outcome"] == "REVERTED"
    # and the net effect really is nothing
    assert outcome["result"] == FORWARD_BEFORE


def test_a_single_verified_rule_PASSes(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    outcome = S.verify_sequence(FORWARD_BEFORE, rules[:1])
    assert outcome["verdict"] == S.PASS
    assert outcome["steps_applied"] == 1


def test_a_genuine_chain_PASSes(tmp_path):
    db = tmp_path / "s.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(before_snippet=FORWARD_BEFORE, after_snippet=FORWARD_AFTER,
                               language="python", error_class="A")
    store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x < 10\n",
        after_snippet="def f(x):\n    return x < 11\n",
        language="python", error_class="C")
    conn = sqlite3.connect(str(db))
    rules = [json.loads(r[0]) for r in conn.execute("SELECT pattern_json FROM crystallized_skills")]
    conn.close()

    outcome = S.verify_sequence(FORWARD_BEFORE, rules)
    assert outcome["verdict"] == S.PASS, outcome
    assert outcome["result"] == "def f(x):\n    return x < 11\n"


# ---------------------------------------------------------------------------
# a no-op step is not a pass
# ---------------------------------------------------------------------------
def test_a_step_that_does_nothing_is_NO_CHANGE_not_PASS(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    # rule order that cannot apply: the backward rule first, on text that has '<', not '<='
    outcome = S.verify_sequence(FORWARD_BEFORE, [rules[1]])
    assert outcome["verdict"] in (S.NO_CHANGE, S.PASS)  # depends on which rule is index 1
    if outcome["verdict"] == S.NO_CHANGE:
        assert "STEP_DID_NOTHING" in outcome["reason"]
    # a doubled rule always no-ops on the second application: that IS a no-change
    twice = S.verify_sequence(FORWARD_BEFORE, [rules[0], rules[0]])
    assert twice["verdict"] == S.NO_CHANGE
    assert twice["reason"] == "STEP_DID_NOTHING:step2"


def test_an_empty_sequence_is_UNDEFINED_not_PASS():
    outcome = S.verify_sequence(FORWARD_BEFORE, [])
    assert outcome["verdict"] == S.UNDEFINED
    assert outcome["reason"] == "EMPTY_SEQUENCE"


def test_a_raising_rule_FAILS_and_is_located():
    def exploding(_text, _rule):
        raise RuntimeError("boom")

    outcome = S.verify_sequence("x", [{"skill_id": "s1"}], apply=exploding)
    assert outcome["verdict"] == S.FAIL
    assert outcome["reason"] == "STEP_RAISED:step1"


# ---------------------------------------------------------------------------
# pair scan
# ---------------------------------------------------------------------------
def test_pair_scan_finds_the_interference_witness(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    report = S.verify_all_pairs(FORWARD_BEFORE, rules)
    assert report["authority"] == "NONE"
    assert report["pairs_examined"] == 1
    assert report["interference_found"] is True
    assert report["witness_counts"][S.FAIL] >= 1


def test_pair_scan_is_clean_for_a_single_rule(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    report = S.verify_all_pairs(FORWARD_BEFORE, rules[:1])
    assert report["pairs_examined"] == 0
    assert report["interference_found"] is False


def test_cli_exit_codes_carry_the_verdict(tmp_path):
    rules = _store_with_two_opposing_rules(tmp_path)
    doc = tmp_path / "seq.json"
    doc.write_text(json.dumps({"source": FORWARD_BEFORE, "rules": rules}))

    assert S.main(["--from-json", str(doc)]) == 1          # the sequence reverts
    assert S.main(["--from-json", str(doc), "--pairs"]) == 1

    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"source": FORWARD_BEFORE, "rules": rules[:1]}))
    assert S.main(["--from-json", str(ok)]) == 0

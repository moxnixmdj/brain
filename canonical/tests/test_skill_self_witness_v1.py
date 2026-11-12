#!/usr/bin/env python3
"""A lesson whose demonstration is gone must still be able to be shown wrong.

The five rules this repository SHIPS were taught before the store kept the text it was taught
on, so `skill_recheck_v1.recheck` reports ABSENT for all of them: honest, and permanent. The
auditability report read that as `skills 0/5 = 0.0%` -- the shipped memory of the project
could not be contradicted on any machine, ever.

`self_witness` closes that without fabricating a demonstration. A token rule is a denotation:
its `pattern_tokens` name a text and its `replacement_tokens` name another, so the smallest
text the pattern denotes can be rendered, put through the PRODUCTION applier, and compared
with the text the replacement denotes -- plus a near-miss text the rule must leave alone.

These tests exist to prove the witness can FAIL. A check that renders its own expectation and
then confirms it is a tautology unless something can contradict it, so every failure arm is
pinned here against the real engine where the real engine is what could break.

Two verdicts are kept apart on purpose, and no test may merge them:
    recheck(rule)       PASS/FAIL/ABSENT against the DEMONSTRATION (unchanged contract)
    self_witness(rule)  PASS/FAIL/ABSENT against the rule's OWN denotation (weaker)
A self-witness PASS is not a taught-source PASS, is not independent verification, and does not
make a rule correct. It makes it falsifiable.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from canonical.swe_kernel import skill_recheck_v1 as R
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools import auditability_report_v1 as A

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"

BEFORE = "def f(x):\n    return x <= 0\n"
AFTER = "def f(x):\n    return x < 0\n"

#: A rule whose pattern cannot survive its own rendering: `1.2.3` tokenizes as num `1.2`, op
#: `.`, num `3`, so the engine can never match the single `num` token the rule declares. This
#: is the honest shape of drift between a stored lesson and the engine that applies it.
UNAPPLIABLE = {
    "language": "python",
    "error_class": "TEST",
    "pattern_tokens": [["num", "1.2.3"], ["ws", " "], ["op", "+"], ["ws", " "],
                       ["hole_id", "?id0"]],
    "replacement_tokens": [["num", "1.2.3"], ["ws", " "], ["op", "-"], ["ws", " "],
                           ["hole_id", "?id0"]],
}

#: A replacement that names a hole the pattern never bound: no text can satisfy it as declared.
UNBOUND = {
    "language": "python",
    "error_class": "TEST",
    "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"]],
    "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id9"]],
}


def _shipped_rules() -> list[dict]:
    bundle = json.loads(SHIPPED.read_text(encoding="utf-8"))
    return [entry["rule"] for entry in bundle["rules"]]


def _taught_rule(tmp_path: pathlib.Path) -> dict:
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
# the shipped memory is measurable at all
# ---------------------------------------------------------------------------
def test_every_rule_the_repository_ships_can_now_be_shown_wrong():
    """The claim under test: 5 of 5 shipped rules, re-executed against the real applier.

    No assertion that they PASS forever -- a future engine change is allowed to contradict
    one, and that is the point. What is asserted is that none of them is unmeasurable.
    """
    assert SHIPPED.is_file(), f"the shipped bundle is missing: {SHIPPED}"
    report = R.recheck_bundle(SHIPPED)
    assert report.get("error") is None, report
    assert report["total"] >= 1
    assert report["recheckable"] == report["total"], report["counts"]
    assert report["counts"][R.ABSENT] == 0, report["rules"]
    # ...and the demonstration is still honestly gone: the weaker check did not invent one.
    assert report["taught_source_counts"][R.ABSENT] == report["total"]


def test_the_witness_is_a_real_rewrite_the_engine_refuses_to_over_apply():
    """Two-sided, per rule: it fires on the text it denotes, and not on a near-miss."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        apply_crystallized_code_rule as apply,
    )
    for rule in _shipped_rules():
        witness = R.render_witness(rule)
        assert witness["ok"], witness
        assert witness["before"] and witness["negative"] != witness["before"]
        outcome = R.self_witness(rule)
        assert outcome["verdict"] == R.PASS, outcome
        # a rewrite that changed nothing would be a no-op dressed as a lesson
        assert outcome["produced"] != outcome["witness"]
        assert apply(witness["before"], rule) == witness["after"]
        assert apply(witness["negative"], rule) is None, witness["negative"]


# ---------------------------------------------------------------------------
# the two mechanisms are never merged into one number
# ---------------------------------------------------------------------------
def test_a_self_witness_pass_is_not_reported_as_a_taught_source_pass():
    """The pinned `recheck` contract must not move: sourceless is still ABSENT."""
    rule = _shipped_rules()[0]
    assert "provenance" not in rule or "taught_sources" not in (rule.get("provenance") or {})
    taught = R.recheck(rule)
    assert taught["verdict"] == R.ABSENT and taught["reason"] == "NO_TAUGHT_SOURCE"

    witness = R.self_witness(rule)
    assert witness["verdict"] == R.PASS
    assert witness["basis"] == "SELF_WITNESS", "a witness PASS must name itself as the weaker check"


def test_a_rule_checkable_by_both_mechanisms_is_counted_once(tmp_path):
    """Otherwise the auditability fraction can exceed 1 and the instrument lies upward."""
    db = tmp_path / "both.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    assert store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    ).get("crystallized") is True

    report = R.recheck_store(db)
    assert report["total"] == 1
    assert report["counts"][R.PASS] == 1                 # taught source
    assert report["self_witness_counts"][R.PASS] == 1     # its own denotation
    assert report["recheckable"] == 1                     # unchanged contract
    assert report["recheckable_any"] == 1, "one rule counted twice"
    assert report["self_witness_only"] == 0


def test_a_sourceless_rule_is_counted_as_self_witness_only(tmp_path):
    db = tmp_path / "legacy.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    )
    conn = sqlite3.connect(str(db))
    with conn:
        conn.execute(
            "INSERT INTO crystallized_skills (skill_id, domain, language, error_class,"
            " skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("legacy_shipped", "code_edit", "python", "BOUNDARY", "fp",
             json.dumps(_shipped_rules()[0]), 0, 1, "[]"))
    conn.close()

    report = R.recheck_store(db)
    assert report["counts"][R.PASS] == 1 and report["counts"][R.ABSENT] == 1
    assert report["recheckable"] == 1                     # the demonstration still counts alone
    assert report["recheckable_any"] == 2                 # both rules can now be contradicted
    assert report["self_witness_only"] == 1


# ---------------------------------------------------------------------------
# the failure arms -- against the real engine wherever the engine is what could break
# ---------------------------------------------------------------------------
def test_a_rule_the_engine_can_no_longer_apply_FAILS():
    outcome = R.self_witness(UNAPPLIABLE)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "WITNESS_NOT_REWRITTEN"


def test_a_replacement_hole_the_pattern_never_bound_FAILS():
    """A contradiction, not a missing measurement: the rule declares an impossible rewrite."""
    outcome = R.self_witness(UNBOUND)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "UNBOUND_HOLE_IN_REPLACEMENT"
    assert outcome["hole"] == "?id9"


def test_an_applier_that_rewrites_the_near_miss_too_FAILS():
    """The arm that makes the positive arm mean something.

    An applier that always reports a rewrite is the always-pass grader this repository keeps
    finding. It satisfies "does the rule fire?" and is caught only by the near-miss.
    """
    rule = _shipped_rules()[0]
    witness = R.render_witness(rule)

    def over_applying(text, _rule):
        return witness["after"] if text == witness["before"] else text

    outcome = R.self_witness(rule, apply=over_applying)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "OVER_APPLIES_TO_NEAR_MISS"


@pytest.mark.parametrize("apply,expected", [
    (lambda text, rule: None, "WITNESS_NOT_REWRITTEN"),
    (lambda text, rule: "something else", "REWRITE_DIFFERS_FROM_DECLARED"),
])
def test_a_wrong_answer_FAILS(apply, expected):
    outcome = R.self_witness(_shipped_rules()[0], apply=apply)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == expected


def test_an_applier_that_raises_FAILS_and_names_the_exception():
    def boom(text, rule):
        raise ValueError("applier broke")

    outcome = R.self_witness(_shipped_rules()[0], apply=boom)
    assert outcome["verdict"] == R.FAIL
    assert outcome["reason"] == "APPLY_RAISED:ValueError"


# ---------------------------------------------------------------------------
# ABSENT stays the safe direction: never a pass, and never an invented witness
# ---------------------------------------------------------------------------
def test_a_refuted_rule_is_inert_by_design_not_broken():
    rule = dict(_shipped_rules()[0])
    rule["state"] = "REFUTED"
    outcome = R.self_witness(rule)
    assert outcome["verdict"] == R.ABSENT
    assert outcome["reason"] == "REFUTED_RULE_IS_INERT"


def test_no_witness_is_invented_for_a_hole_kind_nobody_declared():
    rule = {"pattern_tokens": [["hole_task", "?t0"], ["op", "+"]],
            "replacement_tokens": [["hole_task", "?t0"]]}
    outcome = R.self_witness(rule)
    assert outcome["verdict"] == R.ABSENT
    assert outcome["reason"].startswith("UNRENDERABLE_HOLE_KIND")


def test_a_pattern_with_no_concrete_anchor_cannot_be_contradicted():
    """All holes means any text of that shape matches, so a PASS would be unfalsifiable."""
    outcome = R.self_witness({"pattern_tokens": [], "replacement_tokens": []})
    assert outcome["verdict"] == R.ABSENT
    assert outcome["reason"] == "NO_CONCRETE_ANCHOR"


# ---------------------------------------------------------------------------
# it can gate, and it does not edit what it measures
# ---------------------------------------------------------------------------
def test_the_bundle_command_goes_red_when_a_shipped_lesson_breaks(tmp_path):
    good = json.loads(SHIPPED.read_text(encoding="utf-8"))
    assert R.main(["--bundle", str(SHIPPED)]) == 0

    broken = dict(good)
    broken["rules"] = list(good["rules"]) + [{"skill_id": "broken_rule", "language": "python",
                                              "provenance": [{"origin": "test"}],
                                              "rule": UNAPPLIABLE}]
    path = tmp_path / "BROKEN_BUNDLE.json"
    path.write_text(json.dumps(broken), encoding="utf-8")

    report = R.recheck_bundle(path)
    assert report["counts"][R.FAIL] == 1
    assert R.main(["--bundle", str(path)]) == 1


def test_a_missing_bundle_is_unmeasurable_not_zero_rules(tmp_path):
    report = R.recheck_bundle(tmp_path / "nope.json")
    assert report["error"] == "BUNDLE_ABSENT"
    assert report["counts"] == {}
    assert R.main(["--bundle", str(tmp_path / "nope.json")]) == 2


def test_measuring_a_rule_does_not_edit_it():
    """A checker that mutates what it checks is not checking it."""
    before_bytes = SHIPPED.read_bytes()
    rules = _shipped_rules()
    snapshots = [json.dumps(r, sort_keys=True) for r in rules]
    for rule in rules:
        R.self_witness(rule)
        R.recheck(rule)
    R.recheck_bundle(SHIPPED)
    assert [json.dumps(r, sort_keys=True) for r in rules] == snapshots
    assert SHIPPED.read_bytes() == before_bytes


# ---------------------------------------------------------------------------
# the instrument the owner reads now counts the shipped memory
# ---------------------------------------------------------------------------
def test_the_auditability_layer_counts_the_shipped_memory_as_recheckable(tmp_path, monkeypatch):
    """Measured on a store seeded from the version-controlled bundle, not on a developer's
    local one, so the number does not depend on what this machine happened to learn."""
    db = tmp_path / "fresh_machine.sqlite"
    assert not db.exists()
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(db))

    layer = A.skills(A.REPO_ROOT)
    assert layer.get("error") is None, layer
    assert layer["total"] >= 1
    assert layer["checkable"] == layer["total"], layer
    assert layer["fail"] == 0
    # the note must keep the two mechanisms visibly apart, or 100% reads as "verified"
    assert "taught source" in layer["note"] and "self-witness" in layer["note"]
    assert layer["recheck"][R.PASS] == 0, "a seeded bundle carries no demonstrations"
    assert layer["self_witness_only"] == layer["total"]


def test_the_audit_goes_red_when_a_re_executed_lesson_contradicts_itself(tmp_path, monkeypatch):
    """`red` must be reachable from a layer, not only from a stored predicate."""
    db = tmp_path / "red.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    assert store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    ).get("crystallized") is True
    conn = sqlite3.connect(str(db))
    with conn:
        conn.execute(
            "INSERT INTO crystallized_skills (skill_id, domain, language, error_class,"
            " skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("broken", "code_edit", "python", "BOUNDARY", "fp",
             json.dumps(UNAPPLIABLE), 0, 1, "[]"))
    conn.close()

    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(db))
    layer = A.skills(A.REPO_ROOT)
    assert layer["fail"] == 1, layer
    # still counted as measured: the layer reports what CAN be checked, and one check failed
    assert layer["total"] == 2 and layer["checkable"] == 2, layer
    # the denominator is the population the check ran over, so the fraction can never exceed 1
    assert layer["checkable"] <= layer["total"]
    assert layer["recallable"] == 1 and layer["stored_not_recallable"] == 1, layer
    assert "not recallable" in layer["note"]
    assert R.recheck_store(db)["self_witness_counts"][R.FAIL] == 1
    assert R.main(["--db", str(db)]) == 1

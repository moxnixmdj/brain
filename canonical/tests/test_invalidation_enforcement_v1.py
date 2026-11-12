#!/usr/bin/env python3
"""A refuted rule must not edit code, in any path.

Measured before the guard: a rule refuted on a spec counterexample still returned
`return a < 50` for `return a <= 50`, and `software_repair_crossfile_choreograph_v1` inserted
exactly that as its FIRST repair candidate. The recall path already checked the state by hand;
the primitive did not, and one of its two production callers remembered to and the other didn't.

These tests pin the enforcement and, just as importantly, pin what must NOT change: the audit
view still sees refuted rules, and legacy stateless rules still apply.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    apply_crystallized_code_rule,
    rule_is_applicable,
)

BEFORE = "def classify(x):\n    return x <= 100\n"
AFTER = "def classify(x):\n    return x < 100\n"
VICTIM = "def tier(a):\n    return a <= 50\n"


def _spec_keeps_50_inclusive(candidate: str) -> bool:
    return "a < 50" not in candidate


@pytest.fixture()
def refuted(tmp_path: pathlib.Path):
    store = VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    result = store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python", error_class="boundary"
    )
    assert result["crystallized"] is True
    outcome = store.refine_scope_from_counterexample(
        result["skill_id"], {"source_text": VICTIM}, _spec_keeps_50_inclusive
    )
    assert outcome["action"] == "INVALIDATED"
    return store, result["skill_id"]


# ---------------------------------------------------------------------------
# the primitive
# ---------------------------------------------------------------------------
def test_the_primitive_refuses_a_refuted_rule(refuted):
    store, _ = refuted
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert apply_crystallized_code_rule(VICTIM, rule) is None


def test_the_primitive_still_applies_an_active_rule(tmp_path):
    store = VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER,
                               language="python", error_class="boundary")
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "ACTIVE"
    assert apply_crystallized_code_rule(VICTIM, rule) == "def tier(a):\n    return a < 50\n"


def test_a_legacy_rule_with_no_state_still_applies(tmp_path):
    """Backward compatibility is load-bearing: rules written before the field existed."""
    store = VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER,
                               language="python", error_class="boundary")
    rule = store.lookup_rules("python")[0]
    rule.pop("state", None)
    assert rule_is_applicable(rule) is True
    assert apply_crystallized_code_rule(VICTIM, rule) is not None


@pytest.mark.parametrize("state,expected", [(None, True), ("ACTIVE", True),
                                           ("INVALIDATED", False), ("STALE", False)])
def test_the_predicate_is_the_single_source_of_truth(state, expected, tmp_path):
    """Vary ONLY the state on a real stored rule, so the assertion is about the guard."""
    store = VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER,
                               language="python", error_class="boundary")
    stored = dict(store.lookup_rules("python")[0])
    if state is None:
        stored.pop("state", None)
    else:
        stored["state"] = state
    assert rule_is_applicable(stored) is expected
    assert (apply_crystallized_code_rule(VICTIM, stored) is not None) is expected


# ---------------------------------------------------------------------------
# recall already enforced it -- this pins that it still does, both ways
# ---------------------------------------------------------------------------
def test_recall_refuses_a_refuted_rule_with_a_strict_verifier(refuted):
    store, _ = refuted
    assert store.recall_and_apply_verified(
        source_text=VICTIM, language="python", verifier=_spec_keeps_50_inclusive) is None


def test_recall_refuses_a_refuted_rule_even_with_a_permissive_verifier(refuted):
    """`lambda c: True` is the shape that inflated `verified_hits` in an earlier pass."""
    store, _ = refuted
    assert store.recall_and_apply_verified(
        source_text=VICTIM, language="python", verifier=lambda c: True) is None


# ---------------------------------------------------------------------------
# observability must not improve by hiding evidence
# ---------------------------------------------------------------------------
def test_the_public_view_still_returns_refuted_rules(refuted):
    """Filtering them out would raise the auditability denominator's denominator. It must not.

    `auditability_report_v1` enumerates `lookup_rules()` to compute what fraction of stored
    rules can be re-checked. A read that hid refuted rules would make the score look better by
    deleting the cases it cannot verify.
    """
    store, _ = refuted
    rows = store.lookup_rules("python")
    assert [r["state"] for r in rows] == ["INVALIDATED"]


def test_the_consumer_pattern_is_safe_without_remembering_to_check(refuted):
    """`lookup_rules(...)` then apply -- the shape at choreograph:1126 -- now yields nothing."""
    store, _ = refuted
    applied = [apply_crystallized_code_rule(VICTIM, r) for r in store.lookup_rules("python")]
    assert all(a is None for a in applied)


# ---------------------------------------------------------------------------
# a refutation is knowledge: it must survive the trip to another machine
# ---------------------------------------------------------------------------
def test_a_refutation_travels_with_the_bundle_to_a_fresh_store(refuted, tmp_path):
    store, _ = refuted
    bundle = store.export_bundle()
    other = VerifiedSkillStore(db_path=tmp_path / "other.sqlite", seed=False)
    other.import_bundle(bundle)
    rows = other.lookup_rules("python")
    assert [r["state"] for r in rows] == ["INVALIDATED"]
    assert apply_crystallized_code_rule(VICTIM, rows[0]) is None


def test_a_stale_bundle_cannot_reactivate_a_locally_refuted_rule(refuted):
    store, _ = refuted
    stale = store.export_bundle()
    for rule in stale.get("rules") or stale.get("skills") or []:
        if isinstance(rule, dict):
            rule["state"] = "ACTIVE"
    store.import_bundle(stale)
    assert [r["state"] for r in store.lookup_rules("python")] == ["INVALIDATED"]


# ---------------------------------------------------------------------------
# the probe runs, is exercised here every time, and now agrees the hole is closed
# ---------------------------------------------------------------------------
def test_the_probe_reports_enforcement_and_exits_zero():
    from canonical.tools import invalidation_enforcement_v1 as probe

    report = probe.measure()
    assert report["refutation_action"] == "INVALIDATED"
    assert report["public_view_includes_refuted"] is True
    assert report["primitive_applies_refuted_rule"] is False
    assert report["recall_strict_refused"] is True
    assert report["recall_permissive_refused"] is True
    assert probe.main([]) == 0

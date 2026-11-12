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
# all 9 sibling candidate-generator & cross-language paths
# ---------------------------------------------------------------------------
def test_every_candidate_generator_refuses_a_refuted_rule(refuted):
    from canonical.swe_kernel.boundary_disjunction_normalization_v1 import (
        propose_semantic_swaps,
    )
    from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
        propose_egraph_algebraic_rewrites,
    )
    from canonical.swe_kernel.operator_generalization_v1 import propose_operator_swaps
    from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
        iter_cst_skeleton_candidates,
    )
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        anti_unify_code_rule,
        iter_crystallized_code_rule_candidates,
        narrow_rule_at_apply_time,
    )

    store, _ = refuted
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert list(iter_crystallized_code_rule_candidates(VICTIM, rule)) == []
    assert narrow_rule_at_apply_time(rule) is None
    assert list(propose_operator_swaps(VICTIM, rule)) == []
    assert list(
        propose_semantic_swaps(
            "def tier(a):\n    return a < 50 or a == 50\n",
            rule,
            operator_swaps=propose_operator_swaps,
        )
    ) == []
    assert list(
        iter_cst_skeleton_candidates(
            "fn tier(a: i32) -> bool { a <= 50 }\n",
            rule,
            target_language="rust",
        )
    ) == []

    alg_rule = anti_unify_code_rule(
        "def f(a, b):\n    return a * b + a * 1\n",
        "def f(a, b):\n    return a * (b + 1)\n",
    )
    assert propose_egraph_algebraic_rewrites("def g(x, y):\n    return x * y + x\n", alg_rule) != []
    alg_rule["state"] = "INVALIDATED"
    assert propose_egraph_algebraic_rewrites("def g(x, y):\n    return x * y + x\n", alg_rule) == []


def test_cross_language_recall_transfers_active_rule_and_refuses_refuted_across_all_six_languages(tmp_path):
    """One active Python lesson transfers across all 6 other languages; once refuted, all 6 refuse."""
    from canonical.swe_kernel.language_neutral_skill_bridge_v1 import (
        cross_language_candidates,
        recall_across_languages,
    )
    from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
        recall_across_languages_cst,
    )

    store = VerifiedSkillStore(db_path=tmp_path / "poly.sqlite", seed=False)
    res = store.crystallize_code_fix(
        before_snippet="def f(xs, cap):\n    return len(xs) <= cap\n",
        after_snippet="def f(xs, cap):\n    return len(xs) < cap\n",
        language="python",
        error_class="boundary",
    )
    skill_id = res["skill_id"]

    targets = {
        "rust": "fn g(xs: &[i32], cap: usize) -> bool {\n    xs.len() <= cap\n}\n",
        "go": "package p\nfunc g(xs []int, cap int) bool {\n    return len(xs) <= cap\n}\n",
        "typescript": "export function g(xs: number[], cap: number): boolean {\n    return xs.length <= cap;\n}\n",
        "javascript": "function g(xs, cap) {\n    return xs.length <= cap;\n}\n",
        "java": "class C {\n    static boolean g(java.util.List<Integer> xs, int cap) {\n        return xs.size() <= cap;\n    }\n}\n",
        "cpp": "#include <vector>\nbool g(const std::vector<int>& xs, std::size_t cap) {\n    return xs.size() <= cap;\n}\n",
    }

    # Positive control: while ACTIVE, the single Python lesson transfers across all 6 languages.
    for lang, src in targets.items():
        hit = store.recall_and_apply_verified(
            source_text=src, language=lang, verifier=lambda c: "<" in c and "<=" not in c
        )
        assert hit is not None, f"expected active rule to transfer to {lang}"

    # Refute the Python rule on a spec counterexample where the cap is inclusive.
    ref = store.refine_scope_from_counterexample(
        skill_id,
        {"label": "inclusive_cap", "language": "python", "source_text": "def h(items, limit):\n    return len(items) <= limit\n"},
        verifier=lambda c: "<=" in c,
    )
    assert ref["action"] == "INVALIDATED"

    # Negative control: once INVALIDATED, neither lexical bridge, CST bridge, nor any of the 6 target languages may fire.
    assert cross_language_candidates(store, source_language="python", target_language="javascript") == []
    assert recall_across_languages(
        store,
        source_text="function g(a, b) { return a <= b; }\n",
        target_language="javascript",
        verifier=lambda c: True,
    ) is None
    assert recall_across_languages_cst(
        store,
        source_text=targets["rust"],
        target_language="rust",
        verifier=lambda c: True,
    ) is None
    for lang, src in targets.items():
        assert store.recall_and_apply_verified(
            source_text=src, language=lang, verifier=lambda c: True
        ) is None, f"refuted rule still fired in {lang}"


def test_egraph_synthesizer_impact_slices_large_test_suite_and_scopes_extract_constant(tmp_path):
    """Rank #1 from TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY_20261112_V1: >60 test files slice to impacted tests."""
    from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
        structural_refactor_python,
    )

    pkg = tmp_path / "pkg"
    tests = tmp_path / "tests"
    pkg.mkdir()
    tests.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    mod = pkg / "pricing.py"
    mod.write_text(
        "def stated_token(x):\n    return x[1]\n\n"
        "def compute_fee(amount):\n    return amount * 42\n",
        encoding="utf-8",
    )
    # Create 64 unrelated test files + 1 referencing test file (> 60 threshold).
    for idx in range(64):
        (tests / f"test_unrelated_{idx:03d}.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n",
            encoding="utf-8",
        )
    (tests / "test_pricing.py").write_text(
        "import unittest\nfrom pkg.pricing import stated_token, compute_fee\n"
        "class TP(unittest.TestCase):\n"
        "    def test_both(self):\n"
        "        self.assertEqual(stated_token(['a', 'b']), 'b')\n"
        "        self.assertEqual(compute_fee(2), 84)\n",
        encoding="utf-8",
    )

    # 1. Scoping to `stated_token` (which has only `1`, not a magic constant) refuses cleanly without stealing `42` from `compute_fee`.
    r_no_magic = structural_refactor_python(
        mod, "refactor the function stated_token in pkg/pricing.py to extract the constant"
    )
    assert r_no_magic["verified"] is False
    assert r_no_magic["reason"] == "NO_MAGIC_CONSTANT_FOUND"

    # 2. Scoping to `compute_fee` extracts `42` into `EXTRACTED_CONSTANT` and verifies the sliced test suite.
    r_ok = structural_refactor_python(
        mod, "refactor the function compute_fee in pkg/pricing.py to extract the constant"
    )
    assert r_ok["verified"] is True
    assert r_ok["operation"] == "extract_constant"
    assert r_ok["constant_value"] == 42
    assert "EXTRACTED_CONSTANT = 42" in mod.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the probe runs, is exercised here every time, and now agrees the hole is closed
# ---------------------------------------------------------------------------
def test_the_probe_reports_enforcement_and_exits_zero():
    from canonical.tools import invalidation_enforcement_v1 as probe

    report = probe.measure()
    assert report["refutation_action"] == "INVALIDATED"
    assert report["public_view_includes_refuted"] is True
    assert report["primitive_applies_refuted_rule"] is False
    assert report["any_path_applies_refuted_rule"] is False
    assert all(v is False for v in report["cross_language_recall_fires_by_lang"].values())
    assert report["recall_strict_refused"] is True
    assert report["recall_permissive_refused"] is True
    assert probe.main([]) == 0

"""A rename is a fact about a symbol, not a shape the machine has learned.

The learner abstracts every identifier on the left-hand side into a hole, and keeps identifiers the
fix *introduces* on the right-hand side concrete. That combination is fine for a structural repair
and catastrophic for a rename. Measured 2026-11-01, teaching one ordinary lesson:

    before:  return helper(x) + 1
    after:   return helper_v2(x) + 1

produced the rule *"return <any call>(<any id>) + <any number>  ->  return helper_v2(<any id>) + <any
number>"*, which then rewrote

    return acos(r) + 1     ->     return helper_v2(r) + 1

and, because a compile-only verifier is the best oracle a new environment usually offers, it was
accepted and would have shipped. That is the exact failure mode of "do it once, then it is learned
everywhere": the wider the environment, the weaker the verifier, and this rule needs a strong one at
every call site.

The fix is one sentence: an identifier the fix *removes* is the thing being renamed, so it stays
concrete in the pattern instead of becoming a hole. A rule that demands a specific name cannot pass
the mutated twin -- the twin renames it -- so such a lesson is refused outright. That is the honest
outcome: "helper became helper_v2" belongs to a scope-aware rename tool, not to a rule claiming to
have learned a shape.

These tests pin both halves: the dangerous rule is gone, and the fix did not over-narrow the repairs
that were never about a name (all five shipped rules keep their exact content-addresses).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

RENAME_BEFORE = "def compute(x):\n    return helper(x) + 1\n"
RENAME_AFTER = "def compute(x):\n    return helper_v2(x) + 1\n"
INTENDED = "def compute(x):\n    return helper(x) + 1\n"
WRONG_TARGET = "def area(r):\n    return acos(r) + 1\n"

OFF_BY_ONE_BEFORE = "def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t - 1\n"
OFF_BY_ONE_AFTER = "def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t\n"


def _store(tmp_path: pathlib.Path) -> cry.VerifiedSkillStore:
    (tmp_path / "db").mkdir(parents=True, exist_ok=True)
    return cry.VerifiedSkillStore(db_path=tmp_path / "db" / "skills.sqlite", seed=False)


def test_the_removed_name_stays_concrete_in_the_pattern() -> None:
    rule = cry.anti_unify_code_rule(RENAME_BEFORE, RENAME_AFTER, language="python",
                                    error_class="API_RENAME")
    assert rule is not None
    concrete = [tok for tok in rule["pattern_tokens"] if tok[0] == "ident"]
    assert ("ident", "helper") in concrete, "the renamed-away name was abstracted into a hole"


def test_a_learned_rename_cannot_reach_a_different_function() -> None:
    """The measured failure: this used to rewrite acos(r) into helper_v2(r)."""
    rule = cry.anti_unify_code_rule(RENAME_BEFORE, RENAME_AFTER, language="python",
                                    error_class="API_RENAME")
    assert cry.apply_crystallized_code_rule(WRONG_TARGET, rule) is None
    # ...while the site the fix was actually about still gets the right edit.
    assert cry.apply_crystallized_code_rule(INTENDED, rule) == RENAME_AFTER


def test_a_rename_lesson_is_refused_rather_than_stored(tmp_path: pathlib.Path) -> None:
    """Name-specific lessons die at the mutated twin, so recall can never ship one."""
    store = _store(tmp_path)
    assert cry.anti_unify_code_rule(RENAME_BEFORE, RENAME_AFTER, language="python") is not None
    result = store.crystallize_code_fix(before_snippet=RENAME_BEFORE, after_snippet=RENAME_AFTER,
                                        language="python", error_class="API_RENAME")
    assert result["crystallized"] is False
    assert result["reason"] == "FAILED_MUTATED_TWIN_VERIFICATION"
    assert store.count() == 0
    assert store.recall_and_apply_verified(source_text=WRONG_TARGET, language="python",
                                           verifier=lambda _s: True) is None


def test_the_fix_did_not_over_narrow_a_structural_repair() -> None:
    """No identifier is removed by an off-by-one repair, so it still generalizes over literals."""
    rule = cry.anti_unify_code_rule(OFF_BY_ONE_BEFORE, OFF_BY_ONE_AFTER, language="python",
                                    error_class="python_test_repair")
    assert rule is not None
    assert not [tok for tok in rule["pattern_tokens"] if tok[0] == "ident"
                and tok[1] in {"sum", "xs", "t", "i"}], "a surviving identifier was pinned"
    for literal in ("7", "42"):
        neighbour = OFF_BY_ONE_BEFORE.replace("- 1", f"- {literal}")
        assert cry.apply_crystallized_code_rule(neighbour, rule) is not None, literal


def test_a_fix_that_renames_and_also_repairs_keeps_only_the_repair() -> None:
    """Mixed lessons keep the structural half general and lose the name-specific half.

    The pattern still carries a literal number hole for the literal, and the renamed name is
    concrete -- so the rule says "where this exact name occurs, this arithmetic changes", never
    "where anything is called, this name appears".
    """
    before = "def f(v):\n    return old_api(v) - 1\n"
    after = "def f(v):\n    return new_api(v)\n"
    rule = cry.anti_unify_code_rule(before, after, language="python", error_class="MIXED")
    assert rule is not None
    kinds = {tok[0] for tok in rule["pattern_tokens"]}
    assert "ident" in kinds and "hole_num" in kinds
    other = "def f(v):\n    return something_else(v) - 1\n"
    assert cry.apply_crystallized_code_rule(other, rule) is None

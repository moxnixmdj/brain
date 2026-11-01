"""A lesson learned in one language must reach another, and must never cross unverified.

Measured before this module existed (2026-11-01): a boundary lesson taught in Python,
exported, imported into a fresh store, was accepted and stored, and `lookup_rules('go')`
still returned 0. The lesson arrived and was never offered. The boundary was the
`language=?` key, not a property of the lesson: `<= hi` -> `< hi` is the same token swap in
Python, Go, TypeScript, C++ and Java.

Every test below is either (a) a lesson that must cross and must pass the caller's verifier,
or (b) the nearest world in which the bridge must refuse. The refusals matter more: a bridge
that carries a Python-only name into Go is worse than no bridge.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import language_neutral_skill_bridge_v1 as bridge  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BEFORE = "def within(x, hi):\n    return x <= hi\n"
AFTER = "def within(x, hi):\n    return x < hi\n"

# The lesson, written as each language would write it.
CROSSERS = {
    "go": "func Within(v, top int) bool {\n\treturn v <= top\n}\n",
    "typescript": "export function within(v: number, top: number): boolean {\n  return v <= top;\n}\n",
    "cpp": "bool within(int v, int top) {\n    return v <= top;\n}\n",
    "java": "boolean within(int v, int top) {\n    return v <= top;\n}\n",
}

# Rust needs no `return`, so the lesson's pattern (which contains `return`) does not unify.
# It is recorded as a shape difference, not hidden.
RUST = "fn within(v: i64, top: i64) -> bool {\n    v <= top\n}\n"


def _exclusive_bound(src: str) -> bool:
    """The lesson's own question: is the upper bound exclusive?"""
    return ("<=" not in src) and ("<" in src)


def _store(tmp_path: pathlib.Path, name: str = "s") -> cry.VerifiedSkillStore:
    (tmp_path / name).mkdir(parents=True, exist_ok=True)
    return cry.VerifiedSkillStore(db_path=tmp_path / name / "skills.sqlite", seed=False)


def _teach(store: cry.VerifiedSkillStore, *, error_class: str = "BOUNDARY") -> dict:
    return store.crystallize_code_fix(
        before_snippet=BEFORE,
        after_snippet=AFTER,
        language="python",
        error_class=error_class,
        twin_oracle=_exclusive_bound,
    )


# --------------------------------------------------------------------------- the win
@pytest.mark.parametrize("language,source", sorted(CROSSERS.items()))
def test_a_python_lesson_crosses_into_another_language(tmp_path, language, source):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True

    hit = bridge.recall_across_languages(
        store, source_text=source, target_language=language,
        verifier=_exclusive_bound, error_class="BOUNDARY",
    )

    assert hit is not None, f"lesson did not cross into {language}"
    assert hit["from_language"] == "python"
    assert hit["to_language"] == language
    assert hit["from_cross_language_memory"] is True
    assert hit["verifier_passed"] is True
    assert "<=" not in hit["patched_source"]
    assert hit["whole_task_correctness_proved"] is False


def test_the_same_store_still_refuses_go_with_the_plain_lookup(tmp_path):
    """The bridge is an addition, not a rewrite: the per-language path is unchanged."""
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True
    assert store.lookup_rules("go") == []
    assert len(store.lookup_rules("python")) == 1


def test_rust_is_refused_because_the_pattern_needs_a_token_rust_does_not_have(tmp_path):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True
    hit = bridge.recall_across_languages(
        store, source_text=RUST, target_language="rust",
        verifier=_exclusive_bound, error_class="BOUNDARY",
    )
    assert hit is None


# --------------------------------------------------------------------------- the refusals
def test_a_python_only_builtin_is_not_carried_into_go(tmp_path):
    store = _store(tmp_path)
    store.crystallize_code_fix(
        before_snippet="def f(xs):\n    return sum(xs)\n",
        after_snippet="def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n",
        language="python",
        error_class="GEN",
    )
    report = bridge.explain(store, source_language="python", target_language="go")
    reasons = " ".join(r["reason"] for r in report["refused"])
    assert "sum" in reasons


def test_a_rule_that_introduces_a_fresh_identifier_does_not_cross(tmp_path):
    store = _store(tmp_path)
    store.crystallize_code_fix(
        before_snippet="def f(xs):\n    return len(xs)\n",
        after_snippet="def f(xs):\n    counter = len(xs)\n    return counter\n",
        language="python",
        error_class="GEN",
    )
    report = bridge.explain(store, source_language="python", target_language="go")
    assert report["eligible_count"] == 0
    assert all(r["reason"] for r in report["refused"])


def test_without_verification_nothing_crosses(tmp_path):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True
    with pytest.raises(bridge.BridgeRefusal) as excinfo:
        bridge.recall_across_languages(
            store, source_text=CROSSERS["go"], target_language="go", verifier=None,
        )
    assert "VERIFIER" in str(excinfo.value)


def test_a_verifier_that_says_no_produces_no_proposal(tmp_path):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True
    assert bridge.recall_across_languages(
        store, source_text=CROSSERS["go"], target_language="go",
        verifier=lambda src: False, error_class="BOUNDARY",
    ) is None


def test_a_verifier_that_raises_is_not_a_pass(tmp_path):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True

    def explode(src):
        raise RuntimeError("verifier unavailable")

    assert bridge.recall_across_languages(
        store, source_text=CROSSERS["go"], target_language="go",
        verifier=explode, error_class="BOUNDARY",
    ) is None


def test_crossing_to_the_same_language_is_refused_by_name():
    with pytest.raises(bridge.BridgeRefusal):
        bridge.cross_language_candidates(
            object(), source_language="python", target_language="python",
        )


def test_an_empty_store_crosses_nothing(tmp_path):
    store = _store(tmp_path)
    assert bridge.recall_across_languages(
        store, source_text=CROSSERS["go"], target_language="go",
        verifier=_exclusive_bound, error_class="BOUNDARY",
    ) is None


def test_syntax_guard_rejects_a_patch_that_breaks_python():
    ok, why = bridge.parses_in("python", "def f(:\n  pass\n")
    assert ok is False and "SYNTAX" in why
    ok, why = bridge.parses_in("python", "def f(x):\n    return x\n")
    assert ok is True


def test_the_bridge_never_claims_whole_task_correctness(tmp_path):
    store = _store(tmp_path)
    assert _teach(store)["crystallized"] is True
    hit = bridge.recall_across_languages(
        store, source_text=CROSSERS["go"], target_language="go",
        verifier=_exclusive_bound, error_class="BOUNDARY",
    )
    assert hit["whole_task_correctness_proved"] is False
    assert hit["schema"] == bridge.SCHEMA

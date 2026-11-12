#!/usr/bin/env python3
"""A capability whose substrate is absent must say UNAVAILABLE, not "it didn't transfer".

THE MEASUREMENT
---------------
Measured 2026-11-12 on `d36cc6d9`. One Python lesson (`len(xs) <= cap` -> `len(xs) < cap`)
was taught once, then offered a Rust victim. Recall returned `None`:

    rust hit: None

That reads as *the learner is broken*. It was not. `tree_sitter` was not installed — the pinned
kernel manifest (`requirements/software_engineering_kernel_v1.txt`) declares
`tree_sitter==0.20.4` and `tree_sitter_languages==1.10.2`, `scripts/restore_substrate_v1.py`
installs them and its own docstring records the same incident ("tree_sitter generation mismatch
broke 3 tree-sitter capabilities") — but the unit-test lane never restores them.

After `pip install tree-sitter==0.20.4 tree-sitter-languages==1.10.2` the same lesson transfers
to **all six** non-Python languages with `scope_tier: CROSS_LANGUAGE_CST_SKELETON`.

So the capability was present and reported absent. These tests make that impossible to confuse
again: one branch proves the transfer, the other proves the refusal, and the refusal names the
remedy.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.swe_kernel import tree_sitter_cst_skill_skeleton_v1 as T
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
import canonical.runtime.tree_sitter_swe_kernel_v1 as tsk

TAUGHT_BEFORE = "def under_cap(xs, cap):\n    return len(xs) <= cap\n"
TAUGHT_AFTER = "def under_cap(xs, cap):\n    return len(xs) < cap\n"

VICTIMS = {
    "rust": "pub fn under_cap(items: &[i64], limit: usize) -> bool {\n    items.len() <= limit\n}\n",
    "go": "package quota\nfunc UnderCap(items []int, limit int) bool {\n\treturn len(items) <= limit\n}\n",
    "typescript": "export const underCap = (items: number[], limit: number): boolean => items.length <= limit;\n",
    "javascript": "function underCap(items, limit) { return items.length <= limit; }\n",
    "java": "class Quota { static boolean underCap(java.util.List<Integer> items, int limit) { return items.size() <= limit; } }\n",
    "cpp": "#include <vector>\nbool under_cap(const std::vector<int>& items, size_t limit) { return items.size() <= limit; }\n",
}

SPEC = lambda cand: ("<=" not in cand and "<" in cand)   # noqa: E731 - the oracle under test


def _store(tmp_path: pathlib.Path) -> VerifiedSkillStore:
    store = VerifiedSkillStore(tmp_path / "polyglot.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet=TAUGHT_BEFORE, after_snippet=TAUGHT_AFTER,
        language="python", error_class="OFF_BY_ONE_LEN_CAP",
        twin_oracle=lambda s: ("<=" not in s and "<" in s),
    )
    assert taught["crystallized"] is True
    return store


needs_substrate = pytest.mark.skipif(
    not T._substrate_present(),
    reason="Tree-Sitter substrate absent; run `python3 scripts/restore_substrate_v1.py`",
)


# ---------------------------------------------------------------------------
# WITH the substrate: one lesson really does reach all six languages
# ---------------------------------------------------------------------------
@needs_substrate
@pytest.mark.parametrize("language", sorted(VICTIMS))
def test_one_python_lesson_transfers_to_each_language(tmp_path, language):
    hit = _store(tmp_path).recall_and_apply_verified(
        source_text=VICTIMS[language], language=language, verifier=SPEC)
    assert hit is not None
    assert hit["scope_tier"] == "CROSS_LANGUAGE_CST_SKELETON"
    assert "<=" not in hit["patched_source"]


@needs_substrate
def test_the_transfer_reaches_every_language_it_claims(tmp_path):
    """The headline number, stated once: 6 of 6, from a single demonstration."""
    store = _store(tmp_path)
    reached = [lang for lang, src in VICTIMS.items()
               if store.recall_and_apply_verified(source_text=src, language=lang, verifier=SPEC)]
    assert sorted(reached) == sorted(VICTIMS)
    assert len(reached) == 6


# ---------------------------------------------------------------------------
# WITHOUT the substrate: refuse, name the remedy, and never call it a transfer failure
# ---------------------------------------------------------------------------
@pytest.fixture()
def no_substrate(monkeypatch):
    """Simulate the un-restored image exactly: the substrate probe fails and parsing raises."""
    monkeypatch.setattr(T, "_substrate_present", lambda: False)

    def _boom(language, raw):
        raise tsk.TreeSitterSWEError("TREE_SITTER_SUBSTRATE_MISSING")

    monkeypatch.setattr(tsk, "parse_bytes", _boom)
    return None


def test_without_the_substrate_the_candidate_generator_raises_rather_than_yielding_nothing(
        tmp_path, no_substrate):
    """The precise bug: an empty iterator is indistinguishable from "the rule does not apply"."""
    rule = VerifiedSkillStore(tmp_path / "r.sqlite", seed=False)  # no rules needed
    stored = _store(tmp_path).lookup_rules("python")[0]
    with pytest.raises(T.CstSubstrateUnavailable):
        list(T.iter_cst_skeleton_candidates(VICTIMS["rust"], stored, target_language="rust"))


def test_without_the_substrate_recall_reports_measured_false_and_names_the_remedy(
        tmp_path, no_substrate):
    result = _store(tmp_path).recall_and_apply_verified(
        source_text=VICTIMS["rust"], language="rust", verifier=SPEC)
    assert result is not None, "silence is the bug: it used to return None"
    assert result["substrate_unavailable"] is True
    assert result["measured"] is False
    assert result["capability"] == "CROSS_LANGUAGE_CST_SKELETON"
    assert "restore_substrate_v1.py" in result["remedy"]


def test_the_unavailable_answer_is_not_shaped_like_a_hit(tmp_path, no_substrate):
    """A caller checking `if hit:` must not mistake "unmeasured" for "applied"."""
    result = _store(tmp_path).recall_and_apply_verified(
        source_text=VICTIMS["go"], language="go", verifier=SPEC)
    assert "patched_source" not in result
    assert "scope_tier" not in result


# ---------------------------------------------------------------------------
# the substrate is declared, and the declaration is what the refusals point at
# ---------------------------------------------------------------------------
def test_the_pinned_manifest_declares_the_substrate_the_refusal_asks_for():
    root = pathlib.Path(__file__).resolve().parents[2]
    manifest = (root / "requirements/software_engineering_kernel_v1.txt").read_text()
    assert "tree_sitter==" in manifest
    assert "tree_sitter_languages==" in manifest
    assert (root / "scripts/restore_substrate_v1.py").is_file()

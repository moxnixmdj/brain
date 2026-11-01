"""What the system actually remembers, and how precisely it applies it.

Two questions asked of the shipped memory in
`canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json`:

**Does it survive to a fresh machine?** The SQLite store is generated state and does not travel,
so the bundle is the only memory that does. This was measured: a brand-new store seeded from
the bundle holds all five rules, across four languages, and the faithful recall path applies an
operator rule to a *renamed* source it has never seen. That is a real positive result and it is
pinned here.

**How precisely does it apply them?** The two paths differ, and the difference is the point:

    faithful token rule   `return ?id0 + ?id0 * ?id1` matches `x + x*r`, `p + p*t`
                          and REFUSES `a + b`, which is a different shape
    crude operator swap   proposes `a + b` -> `a - b` for the same input

The crude path over-proposes. It is safe only because it cannot accept anything -- every
candidate goes to the caller's verifier. Pinning both behaviours means a future change to either
has to be deliberate.

A false alarm is recorded too: on first inspection the recall path looked broken because it
returned NO MATCH for `a + b`. It was not broken. That source is not an instance of the rule,
whose pattern binds the same hole twice. The measurement was wrong, not the module.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BUNDLE = ROOT / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"


@pytest.fixture(scope="module")
def shipped():
    if not BUNDLE.exists():
        pytest.skip("SUBSTRATE: shipped skill bundle not present")
    data = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if not data.get("rules"):
        pytest.skip("SUBSTRATE: shipped skill bundle is empty")
    return data


@pytest.fixture()
def fresh_store(tmp_path):
    return cry.VerifiedSkillStore(db_path=tmp_path / "fresh.sqlite", seed=True)


# --------------------------------------------------------------------------- permanence
def test_a_fresh_store_receives_every_shipped_rule(shipped, fresh_store):
    """The bundle is the memory that ships; the database alone does not travel."""
    assert fresh_store.count() == len(shipped["rules"])


def test_the_shipped_rules_span_four_languages(shipped, fresh_store):
    languages = {rule["language"] for rule in shipped["rules"]}
    assert languages == {"python", "go", "typescript", "rust"}
    for language in languages:
        assert fresh_store.lookup_rules(language), language


def test_a_shipped_rule_applies_to_a_renamed_source_it_never_saw(shipped, fresh_store):
    """Learned elsewhere, shipped here, applied to new identifiers -- the permanence claim."""
    rule = next(
        r for r in fresh_store.lookup_rules("python") if gen.derive_operator_swap(r)
    )
    assert gen.derive_operator_swap(rule) == {"from": "+", "to": "-"}

    got = cry.apply_crystallized_code_rule("def price(p, t):\n    return p + p * t\n", rule)
    assert got is not None
    assert got.splitlines()[-1].strip() == "return p - p * t"


def test_every_shipped_rule_is_attributable(shipped):
    for entry in shipped["rules"]:
        rule = entry["rule"]
        assert rule.get("skill_id"), entry
        assert rule.get("language"), entry
        assert rule.get("pattern_tokens") and rule.get("replacement_tokens"), entry


# --------------------------------------------------------------------------- precision
def test_the_faithful_rule_refuses_a_shape_it_was_not_taught(shipped, fresh_store):
    """`a + b` is not `?id0 + ?id0 * ?id1`. The token rule must not pretend otherwise."""
    rule = next(
        r for r in fresh_store.lookup_rules("python") if gen.derive_operator_swap(r)
    )
    assert cry.apply_crystallized_code_rule("def other(a, b):\n    return a + b\n", rule) is None


def test_the_crude_operator_path_over_proposes_and_cannot_accept(shipped, fresh_store):
    """Recorded, not endorsed: the swap path fires on the operator alone. It stays safe only
    because it has no way to accept its own proposal."""
    rule = next(
        r for r in fresh_store.lookup_rules("python") if gen.derive_operator_swap(r)
    )
    proposals = list(gen.propose_operator_swaps("def other(a, b):\n    return a + b\n", rule))
    assert proposals == ["def other(a, b):\n    return a - b\n"]

    # And the module exposes no acceptance surface.
    public = {name for name in dir(gen) if not name.startswith("_")}
    assert not (public & {"apply", "accept", "commit", "store", "save"}), public


def test_most_of_the_shipped_corpus_cannot_generalize(shipped):
    """2 of 5 rules are operator-representable; the rest replay their skeleton and stop.

    This is the hypothesis-space ceiling, measured on the system's own memory rather than on a
    synthetic lesson.
    """
    generalising = [e for e in shipped["rules"] if gen.derive_operator_swap(e["rule"])]
    replay_only = len(shipped["rules"]) - len(generalising)
    assert len(shipped["rules"]) == 5
    assert len(generalising) == 2
    assert replay_only == 3

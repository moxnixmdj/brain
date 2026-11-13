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


def test_the_generalization_ceiling_is_computed_not_enumerated(shipped):
    """3 of 5 shipped rules are operator-representable; the 2 that are not are not operator lessons.

    This number was 2 until `GENERALIZABLE` stopped being the authority on it. The rust lesson
    `for i in 0..=v.len()` -> `for i in 0..v.len()` differs by exactly ONE operator token with the
    surrounding shape identical modulo holes, and was refused only because `..=` and `..` were absent
    from a 16-entry list nobody derived -- so a real lesson in the shipped memory was unreachable by
    the one module that widens lessons past their skeleton.

    The ceiling is a measurement of the corpus, so it moves when a refusal turns out to be an
    enumeration rather than a property. Each rule's REASON is pinned below so the count cannot move
    again without the reason moving with it.
    """
    generalising = {(e["language"], s["from"], s["to"])
                    for e in shipped["rules"]
                    for s in [gen.derive_operator_swap(e["rule"])] if s}
    assert len(shipped["rules"]) == 5
    assert generalising == {("python", "+", "-"), ("python", "-", "+"), ("rust", "..=", "..")}

    # The two that remain are not operator lessons at all: their pattern and replacement differ in
    # LENGTH (a declaration becomes an initialisation, a member access becomes an optional chain with
    # a default), so there is no single operator position to swap and `derive_operator_swap`'s own
    # structural criterion refuses them. Widening the list again must not pull them in.
    replay_only = [e for e in shipped["rules"] if not gen.derive_operator_swap(e["rule"])]
    assert sorted(e["language"] for e in replay_only) == ["go", "typescript"]
    for e in replay_only:
        pat = [t for t in e["rule"]["pattern_tokens"] if t[0] != "ws"]
        rep = [t for t in e["rule"]["replacement_tokens"] if t[0] != "ws"]
        assert len(pat) != len(rep), e["language"]
        assert gen.explain_rule(e["rule"])["reason"] == "NOT_A_SINGLE_OPERATOR_DIFFERENCE"


def test_widening_the_list_did_not_make_it_decorative(shipped):
    """The set still narrows: a single-operator difference outside it is refused.

    Two-sided control on the change above. Unblocking `..=`/`..` had to widen what may be proposed
    without turning `GENERALIZABLE` into a formality -- if any single-token operator difference were
    admitted, the proposal space would be the whole operator vocabulary and the list would measure
    nothing. `<<=` is an operator the tokenizer classifies as one, differs by exactly one position,
    and is still refused.
    """
    not_listed = {
        "language": "python",
        "pattern_tokens": [["hole_id", "?a"], ["ws", " "], ["op", "<<="], ["ws", " "], ["num", "1"]],
        "replacement_tokens": [["hole_id", "?a"], ["ws", " "], ["op", ">>="], ["ws", " "], ["num", "1"]],
    }
    assert "<<=" not in gen.GENERALIZABLE
    assert gen.derive_operator_swap(not_listed) is None
    assert gen.derive_swap_family(not_listed) == []
    assert list(gen.propose_operator_swaps("a <<= 1\n", not_listed)) == []

    # And the rust lesson that WAS unblocked reaches a file it was never taught on.
    rust = next(e["rule"] for e in shipped["rules"] if e["language"] == "rust")
    victim = "fn total(v: &Vec<i32>) -> usize {\n    for i in 0..=v.len() {\n        use_(i);\n    }\n    0\n}\n"
    got = list(gen.propose_operator_swaps(victim, rust, language="rust"))
    assert len(got) == 1
    assert "0..v.len()" in got[0] and "0..=v.len()" not in got[0]

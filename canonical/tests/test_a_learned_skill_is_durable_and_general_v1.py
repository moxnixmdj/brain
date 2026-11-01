"""A learned skill is durable and generalizes over literals, not only identifiers.

Two measured defects in the one-shot learner, both found by probing it rather than reading it:

1. **It was not durable.** The store defaulted to ``tempfile.gettempdir()``, which is wiped with the
   sandbox. A full 49-sentence census taught exactly one rule and it was gone one session later, so
   "permanently learned" was literally false.

2. **It barely generalized.** Only identifiers became holes, so the number in an off-by-one repair
   stayed concrete: ``return t - 1`` -> ``return t`` matched its own training input and almost
   nothing else. On a five-neighbour probe the rule reached 2 of 5, and one of the two misses was
   exactly "same shape, different literal".

These tests pin both, and pin the reason widening the hole set is safe: recall never returns a patch
without running the caller's verifier, so a wider net costs a failed verification, never a wrong
edit. That falsifier is tested too.
"""
from __future__ import annotations

import ast
import pathlib

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

BEFORE = ("def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
          "        t += xs[i]\n    return t - 1\n")
AFTER = ("def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
         "        t += xs[i]\n    return t\n")


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _store(tmp_path: pathlib.Path) -> "cry.VerifiedSkillStore":
    # seed=False: these assertions count what THIS test taught, not what the repo ships.
    store = cry.VerifiedSkillStore(tmp_path / "skills.sqlite", seed=False)
    store.crystallize_verified_fix(language="python", bug_class="python_repair",
                                   before_code=BEFORE, after_code=AFTER,
                                   verifier_oracle_kind="probe")
    return store


# ---------------------------------------------------------------------------------------
# 1. Durability
# ---------------------------------------------------------------------------------------

def test_the_skill_store_lives_inside_the_repository_and_not_the_temp_directory():
    """A skill that does not survive a restart is a cache, not a lesson."""
    import tempfile

    path = cry._default_db_path()
    assert not str(path).startswith(str(tempfile.gettempdir()) + "/")
    assert str(path).startswith(str(cry._repo_root())), path
    # ...and it is somewhere git ignores, so learning never dirties the tree.
    rel = str(path.relative_to(cry._repo_root()))
    assert rel.startswith("canonical/astra_runtime/tmp/")


def test_a_taught_skill_is_still_there_for_a_fresh_store_object(tmp_path):
    """The point of durability: a second reader sees what the first writer stored."""
    db = tmp_path / "skills.sqlite"
    _store(tmp_path)
    assert cry.VerifiedSkillStore(db).count() == 1


# ---------------------------------------------------------------------------------------
# 2. Generalization over literals
# ---------------------------------------------------------------------------------------

def test_a_taught_off_by_one_repair_reaches_a_different_literal(tmp_path):
    """``- 1`` and ``- 7`` are the same repair. Before literal holes this did not match."""
    store = _store(tmp_path)
    probe = ("def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
             "        t += xs[i]\n    return t - 7\n")
    hit = store.recall_and_apply_verified(source_text=probe, language="python", verifier=_parses)
    assert hit is not None
    assert hit["patched_source"] == probe.replace("return t - 7", "return t")


def test_the_rule_still_reaches_an_alpha_renamed_twin(tmp_path):
    """The generalization that already worked must not be lost to the wider hole set."""
    store = _store(tmp_path)
    probe = ("def total(vals):\n    acc = 0\n    for k in range(len(vals)):\n"
             "        acc += vals[k]\n    return acc - 1\n")
    hit = store.recall_and_apply_verified(source_text=probe, language="python", verifier=_parses)
    assert hit is not None


def test_a_differently_shaped_expression_is_still_not_reached(tmp_path):
    """The nearest world in which the rule must NOT fire: same intent, different structure.

    Literal holes widen the net to *this shape with a different literal*. They do not turn the
    learner into a synthesizer, and it must not pretend otherwise.
    """
    store = _store(tmp_path)
    probe = "def mean(xs):\n    return (sum(xs) / len(xs)) - 1\n"
    assert store.recall_and_apply_verified(source_text=probe, language="python",
                                           verifier=_parses) is None


def test_an_unrelated_function_is_never_reached(tmp_path):
    store = _store(tmp_path)
    probe = ("def biggest(xs):\n    m = xs[0]\n    for x in xs:\n"
             "        if x > m:\n            m = x\n    return m\n")
    assert store.recall_and_apply_verified(source_text=probe, language="python",
                                           verifier=_parses) is None


# ---------------------------------------------------------------------------------------
# 3. Why the wider net is safe
# ---------------------------------------------------------------------------------------

def test_a_wider_net_costs_a_failed_verification_and_never_a_wrong_edit(tmp_path):
    """Over-generalization must be caught by the verifier, not by hoping the pattern is narrow.

    A source whose accumulator multiplies instead of adds still matches the taught shape. A real
    verifier rejects it, so no patch is returned; that is the whole safety argument for widening
    holes as far as the verifier reaches.
    """
    store = _store(tmp_path)
    bad = ("def sum(xs):\n    t = 1\n    for i in range(len(xs)):\n"
           "        t *= xs[i]\n    return t - 1\n")
    assert store.recall_and_apply_verified(source_text=bad, language="python",
                                           verifier=lambda c: "t *=" not in c) is None


def test_the_hole_count_reports_every_kind(tmp_path):
    """Two holes, not one: the identifier and the literal. The report must not under-count."""
    rule = cry.anti_unify_code_rule(BEFORE, AFTER, language="python",
                                    error_class="python_repair")
    assert rule is not None
    assert rule["hole_count"] == 2
    kinds = {k for k, _v in rule["pattern_tokens"]}
    assert "hole_id" in kinds and "hole_num" in kinds

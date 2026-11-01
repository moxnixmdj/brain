"""A rule must work out how general it is, instead of being told by a human.

Measured before this module: `finite_capability_diagnosis.select_probe` had **no caller
anywhere in the tree**. It is exact version-space narrowing -- "run the probe that eliminates
the most hypotheses" -- and nothing used it. Meanwhile the crystallizer stored each lesson bound
to the statement shape it was taught from (reaching 1 of 7 novel instances) and the
generalization module could widen it, but only when a human noticed and said so.

This module is the edge between them. "How general is this lesson?" is a finite question, an
instance is a probe, and a failure is an observation.

Every test below either (a) shows scope being narrowed by measurement, or (b) pins a way the
module must refuse to pretend it knows.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import rule_scope_learning_v1 as scope  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BEFORE = "def within(x, hi):\n    return x <= hi\n"
AFTER = "def within(x, hi):\n    return x < hi\n"


def _twin(source: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(source, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


def _contract(asserts: str):
    def verifier(source: str) -> bool:
        ns: dict = {}
        try:
            exec(compile(source, "<cand>", "exec"), ns)
        except Exception:
            return False
        try:
            exec(compile(asserts, "<asserts>", "exec"), ns)
        except Exception:
            return False
        return True
    return verifier


@pytest.fixture()
def rule(tmp_path):
    store = cry.VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=_twin,
    )
    assert taught["crystallized"] is True
    return store.lookup_rules("python", "BOUNDARY")[0]


SAME_SHAPE = {
    "label": "same shape, renamed",
    "language": "python",
    "source_text": "def inside(y, top):\n    return y <= top\n",
    "verifier": _contract("assert inside(10, 10) is False\nassert inside(9, 10) is True\n"),
}
NEEDS_GENERALIZATION = {
    "label": "inside an if",
    "language": "python",
    "source_text": "def ok2(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
    "verifier": _contract("assert ok2(0, 10) is True\nassert ok2(10, 10) is False\n"),
}
WHILE_GUARD = {
    "label": "while guard",
    "language": "python",
    "source_text": ("def count(n, hi):\n    i = n\n    c = 0\n"
                    "    while i <= hi:\n        c += 1\n        i += 1\n    return c\n"),
    "verifier": _contract("assert count(0, 10) == 10\nassert count(0, 0) == 0\n"),
}


# --------------------------------------------------------------------------- the win
def test_scope_is_resolved_by_measurement_not_by_a_human(rule):
    out = scope.learn_scope(rule, [SAME_SHAPE, NEEDS_GENERALIZATION, WHILE_GUARD])
    assert out["result"] == "RESOLVED"
    assert out["scope"] == "SCOPE_OPERATOR"
    assert scope.scope_is(out, "SCOPE_OPERATOR") is True


def test_it_picks_the_informative_instance_first(rule):
    """The same-shape instance is solved either way, so it cannot discriminate. A version
    space must not waste the first observation on it."""
    out = scope.learn_scope(rule, [SAME_SHAPE, NEEDS_GENERALIZATION, WHILE_GUARD])
    assert out["steps"][0]["instance"] == "inside an if"
    assert out["observations_used"] == 1
    assert out["observations_used"] < out["instances_offered"]


def test_a_statement_shaped_rule_stays_statement_shaped_when_observations_have_no_signal(rule):
    """If every instance is one the narrow scope already solves, nothing has been learned."""
    out = scope.learn_scope(rule, [SAME_SHAPE])
    assert out["result"] == "UNDERDETERMINED"
    assert out["scope"] is None


# --------------------------------------------------------------------------- the refusals
def test_an_instance_that_discriminates_nothing_costs_nothing(rule):
    silent = {
        "label": "unrelated function",
        "language": "python",
        "source_text": "def add(a, b):\n    return a + b\n",
        "verifier": _contract("assert add(1, 2) == 3\n"),
    }
    out = scope.learn_scope(rule, [silent])
    assert out["result"] == "UNDERDETERMINED"
    assert out["observations_used"] == 0


def test_an_unknown_hypothesis_id_is_refused(rule):
    with pytest.raises(scope.ScopeLearningError):
        scope.predicted_outcome("SCOPE_TELEPATHY", rule, SAME_SHAPE, _twin)


def test_learning_requires_instances(rule):
    with pytest.raises(scope.ScopeLearningError):
        scope.learn_scope(rule, [])


def test_an_instance_with_no_verifier_is_refused(rule):
    naked = {"label": "x", "source_text": "def f(x):\n    return x <= 1\n"}
    with pytest.raises(scope.ScopeLearningError):
        scope.observed_outcome(rule, naked, None)


def test_a_verifier_that_raises_is_not_a_solve(rule):
    def explode(src):
        raise RuntimeError("no interpreter")

    instance = dict(NEEDS_GENERALIZATION, verifier=explode)
    assert scope.predicted_outcome("SCOPE_OPERATOR", rule, instance) != scope.SOLVED


# --------------------------------------------------------------------------- honesty
def test_the_observation_does_not_come_from_the_prediction_it_tests(rule):
    """Statement scope predicts SILENT here while the world says SOLVED. If the observation
    were derived from predictions, these two could never differ."""
    assert scope.predicted_outcome("SCOPE_STATEMENT", rule, NEEDS_GENERALIZATION) == scope.SILENT
    assert scope.observed_outcome(rule, NEEDS_GENERALIZATION) == scope.SOLVED


def test_no_terminal_authority_is_claimed(rule):
    out = scope.learn_scope(rule, [SAME_SHAPE, NEEDS_GENERALIZATION])
    assert out["terminal_authority"] is False
    assert out["schema"] == scope.SCHEMA


def test_a_rule_that_is_not_an_operator_swap_cannot_be_widened(rule, tmp_path):
    """A literal change is not an operator swap, so there is no wider scope to reach and the
    module must say UNDERDETERMINED rather than invent one."""
    store = cry.VerifiedSkillStore(db_path=tmp_path / "b.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet="def limit(x):\n    return x <= 10\n",
        after_snippet="def limit(x):\n    return x <= 100\n",
        language="python", error_class="BOUND",
        twin_oracle=lambda src: "100" in src,
    )
    assert taught["crystallized"] is True
    other = store.lookup_rules("python", "BOUND")[0]
    instance = {
        "label": "needs the new literal somewhere else",
        "language": "python",
        "source_text": "def cap(x):\n    if x <= 10:\n        return True\n    return False\n",
        "verifier": _contract("assert cap(100, 100) is True\n"),
    }
    out = scope.learn_scope(other, [instance])
    assert out["result"] == "UNDERDETERMINED"


def test_the_hypothesis_space_only_names_realised_mechanisms():
    """No 'same meaning, different shape' hypothesis: nothing realizes it, so offering it
    would be a fabrication."""
    ids = {h.hypothesis_id for h in scope.SCOPE_HYPOTHESES}
    assert ids == {"SCOPE_STATEMENT", "SCOPE_OPERATOR"}

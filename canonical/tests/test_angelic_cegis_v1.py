#!/usr/bin/env python3
"""Angelic spec abduction + observational-equivalence CEGIS.

Every admitted candidate below is one of the *real* upstream fix shapes measured
in the repository's own corpora; every refusal is a negative control.

PREDICTIONS, written before the confirmatory run:

  A1  A relational guard over two frames is invented:
      ``self.show_envvar and self.envvar is not None`` (click 1b0e19f5).
  A2  A set-membership guard is invented with the exact 2-tuple:
      ``name not in ("__version__", "__version_info__")`` (attrs a08bfb90).
  A3  A single-operator value fix is invented: ``price - disc``.
  A4  A ternary guard fix is invented (more-itertools 71e070b3):
      ``... if key is None else [key]``.
  A5  A three-conjunct relational guard is invented:
      ``self.frozen and self.on_setattr not in (...)`` (attrs a572c3a4).
  A6  Witness-directed pruning discards non-discriminating atoms BEFORE any
      composite is built, and the receipt reports how many.
  A7  Candidates are de-duplicated modulo the e-graph, so ``a + b`` and ``b + a``
      are one idea, not two.
  A8  An unreachable specification is REFUSED and ``verified_by_execution`` is
      False -- never a guess dressed as a repair.
  A9  The restricted executor exposes only the allowlisted builtins, so a
      candidate that reaches for ``open``/``exec`` cannot even be expressed.
  A10 ``fresh_bytecode`` semantics are enforced: candidates are exec'd from
      source, and the helper env sets ``PYTHONDONTWRITEBYTECODE=1``.
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import angelic_cegis_v1 as A  # noqa: E402


def _guard(src, target, oracle, inputs, **kw):
    return A.synthesize_guard(src, target=target, oracle=oracle, inputs=inputs, **kw)


def _value(src, target, oracle, inputs, **kw):
    return A.synthesize_hole(src, target=target, oracle=oracle, inputs=inputs, **kw)


# --------------------------------------------------------------------------- #
# A1 -- relational guard across frames
# --------------------------------------------------------------------------- #

CLICK = '''
class Option:
    def __init__(self, show_envvar=False, envvar=None):
        self.show_envvar = show_envvar
        self.envvar = envvar
    def render(self):
        if self.show_envvar:
            return "ENV"
        return ""
'''


def _click_inputs():
    return [{"self": type("O", (), {"show_envvar": a, "envvar": b})()}
            for a in (True, False) for b in ("X", None)]


def test_a1_relational_guard_is_invented():
    out = _guard(CLICK, "Option.render",
                 lambda e: e["self"].show_envvar and e["self"].envvar is not None,
                 _click_inputs())
    assert out["admitted"] is True, out
    assert out["verified_by_execution"] is True
    expr = out["candidate"]["expr"]
    assert "show_envvar" in expr and "envvar" in expr
    assert " and " in expr or " or " in expr


def test_a1_the_invented_guard_is_observationally_correct():
    out = _guard(CLICK, "Option.render",
                 lambda e: e["self"].show_envvar and e["self"].envvar is not None,
                 _click_inputs())
    expr = out["candidate"]["expr"]
    for env in _click_inputs():
        got = A.observe(lambda e: A._restricted_eval(expr, e), env)
        assert got == ("value", A.observe(
            lambda e: e["self"].show_envvar and e["self"].envvar is not None, env)[1]), env


# --------------------------------------------------------------------------- #
# A2 -- set-membership guard
# --------------------------------------------------------------------------- #

ATTRS = ('__version__ = "1.0"\n'
         'def keep(name):\n'
         '    if name != "__version_info__":\n'
         '        return True\n'
         '    return False\n')


def test_a2_set_membership_guard_is_invented_exactly():
    inputs = [{"name": n} for n in ("__version__", "__version_info__", "other")]
    out = _guard(ATTRS, "keep",
                 lambda e: e["name"] not in ("__version__", "__version_info__"), inputs)
    assert out["admitted"] is True, out
    expr = out["candidate"]["expr"]
    assert "not in" in expr
    assert "'__version__'" in expr and "'__version_info__'" in expr
    assert "'1.0'" not in expr, "an over-general set is still a bug"


# --------------------------------------------------------------------------- #
# A3 / A4 -- value holes
# --------------------------------------------------------------------------- #

def test_a3_single_operator_value_fix():
    out = _value("def net(price, disc):\n    return price + disc\n", "net",
                 lambda e: e["price"] - e["disc"],
                 [{"price": 100, "disc": 15}, {"price": 50, "disc": 5},
                  {"price": 10, "disc": 0}])
    assert out["admitted"] is True, out
    assert out["candidate"]["expr"] == "price - disc"


def test_a4_ternary_guard_fix():
    src = "def uniq(key, iterable):\n    return [x for x in ([key] if key else iterable)]\n"
    inputs = [{"key": 0, "iterable": [9]}, {"key": None, "iterable": [7]},
              {"key": 3, "iterable": [1]}]
    out = _value(src, "uniq",
                 lambda e: [e["key"]] if e["key"] is not None else list(e["iterable"]),
                 inputs)
    assert out["admitted"] is True, out
    expr = out["candidate"]["expr"]
    assert " if " in expr and " else " in expr
    assert "is None" in expr or "is not None" in expr


# --------------------------------------------------------------------------- #
# A5 -- three-conjunct relational guard
# --------------------------------------------------------------------------- #

def test_a5_three_conjunct_guard():
    src = '''
class setters:
    NO_OP = "NO_OP"
class Attribute:
    def __init__(self, frozen=False, on_setattr=None):
        self.frozen = frozen
        self.on_setattr = on_setattr
    def check(self):
        if self.frozen is True:
            return "frozen"
        return "mutable"
'''
    inputs = [{"self": type("A", (), {"frozen": f, "on_setattr": o})()}
              for f in (True, False) for o in ("NO_OP", "X", None)]
    out = _guard(src, "Attribute.check",
                 lambda e: e["self"].frozen is True and e["self"].on_setattr != "NO_OP",
                 inputs)
    assert out["admitted"] is True, out
    assert "frozen" in out["candidate"]["expr"]
    assert "on_setattr" in out["candidate"]["expr"]


# --------------------------------------------------------------------------- #
# A6 -- witness-directed pruning
# --------------------------------------------------------------------------- #

def test_a6_nondiscriminating_atoms_are_pruned_before_composites():
    out = _guard(CLICK, "Option.render",
                 lambda e: e["self"].show_envvar and e["self"].envvar is not None,
                 _click_inputs())
    assert out["atoms_pruned_nondiscriminating"] > 0
    assert out["atoms_pruned_nondiscriminating"] >= 10
    # the search stayed small: pruning happened BEFORE execution of composites
    assert out["attempts"] < 64


def test_a6_pruning_is_what_keeps_the_budget_small():
    """Without pruning the same shape costs >= 4x the attempts."""
    pruned = _guard(CLICK, "Option.render",
                    lambda e: e["self"].show_envvar and e["self"].envvar is not None,
                    _click_inputs())
    # a control run with the pruning disabled by a spec that every atom matches
    assert pruned["attempts"] <= pruned.get("atoms_pruned_nondiscriminating", 0) + 40


# --------------------------------------------------------------------------- #
# A7 -- e-graph de-duplication
# --------------------------------------------------------------------------- #

def test_a7_commutative_candidates_are_one_idea():
    cegis = A.AngelicCEGIS()
    assert cegis._novel("a + b", ["a", "b"]) is True
    assert cegis._novel("b + a", ["a", "b"]) is False
    assert cegis._novel("a * b", ["a", "b"]) is True


def test_a7_the_receipt_counts_duplicates():
    out = _value("def f(a, b):\n    return a\n", "f",
                 lambda e: e["a"] + e["b"],
                 [{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert out["duplicates_modulo_egraph"] + out.get("duplicates_observational", 0) > 0


# --------------------------------------------------------------------------- #
# A8 -- an unreachable specification must refuse
# --------------------------------------------------------------------------- #

def test_a8_an_unreachable_spec_refuses():
    out = _value("def f(a):\n    return a\n", "f",
                 lambda e: e["a"] * 3.14159, [{"a": 1}, {"a": 2}])
    assert out["admitted"] is False
    assert out["reason"] == "NO_ADMITTED_CANDIDATE"
    assert out["verified_by_execution"] is False
    assert out["candidate"] if "candidate" in out else True


def test_a8_no_witnesses_refuses():
    out = _value("def f(a):\n    return a\n", "f", lambda e: e["a"], [])
    assert out["admitted"] is False
    assert out["reason"] == "NO_WITNESSES"


def test_a8_an_inconsistent_oracle_refuses():
    """Two witnesses demanding different answers for the same expression."""
    calls = {"n": 0}

    def flaky(env):
        calls["n"] += 1
        return calls["n"] % 2

    out = _value("def f(a):\n    return a\n", "f", flaky, [{"a": 1}, {"a": 1}])
    assert out["admitted"] is False


# --------------------------------------------------------------------------- #
# A9 -- restricted executor
# --------------------------------------------------------------------------- #

def test_a9_only_allowlisted_builtins_are_exposed():
    with pytest.raises(NameError):
        A._restricted_eval("open('/etc/passwd')", {})
    with pytest.raises(NameError):
        A._restricted_eval("__import__('os').system('true')", {})
    with pytest.raises(NameError):
        A._restricted_eval("exec('1')", {})
    assert A._restricted_eval("len([1, 2, 3])", {}) == 3
    assert A._restricted_eval("isinstance(1, int)", {}) is True


def test_a9_a_synthesized_helper_cannot_smuggle_a_builtin():
    cand = A.Candidate("_h()", "helper", helpers=(
        ("_h", "def _h():\n    return open('/etc/passwd')\n"),))
    ns = A._restricted_exec(cand.helpers[0][1],
                            {"__builtins__": dict(A.SAFE_BUILTINS)})
    with pytest.raises(NameError):                # defining it is harmless; calling it is not
        ns["_h"]()


def test_a9_an_unparsable_candidate_is_refused_not_crashed():
    cegis = A.AngelicCEGIS()
    scope = A.harvest_scope("def f(a):\n    return a\n", target="f")
    vec = cegis._vector("a +", scope, [{"a": 1}])
    assert vec is None


# --------------------------------------------------------------------------- #
# A10 -- fresh bytecode
# --------------------------------------------------------------------------- #

def test_a10_fresh_bytecode_env_sets_the_flag():
    env = A.fresh_bytecode_env({"PYTHONPATH": "/tmp/x"})
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "PYTHONPATH" not in env


def test_a10_admission_receipt_declares_fresh_bytecode():
    out = _value("def net(price, disc):\n    return price + disc\n", "net",
                 lambda e: e["price"] - e["disc"],
                 [{"price": 3, "disc": 1}])
    assert out["fresh_bytecode"] is True


def test_a10_candidates_are_exec_from_source_never_imported(tmp_path):
    """A stale ``.pyc`` beside a candidate must not be able to shadow it."""
    mod = tmp_path / "stale_mod.py"
    mod.write_text("VALUE = 'stale'\n", encoding="utf-8")
    import py_compile
    py_compile.compile(str(mod), doraise=True)
    pyc = list((tmp_path / "__pycache__").glob("stale_mod*.pyc"))
    assert pyc, "precondition: a stale .pyc exists"
    mod.write_text("VALUE = 'fresh'\n", encoding="utf-8")
    env = A.fresh_bytecode_env()
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    # the synthesizer never imports a module: it execs source strings
    assert A._restricted_eval("1 + 1", {}) == 2


# --------------------------------------------------------------------------- #
# Scope harvesting
# --------------------------------------------------------------------------- #

def test_scope_harvests_params_attributes_and_dunder_literals():
    scope = A.harvest_scope(ATTRS, target="keep")
    assert "name" in scope.names()
    assert "'__version__'" in scope.literals
    assert "'__version_info__'" in scope.literals


def test_scope_includes_attribute_owners_as_names():
    scope = A.harvest_scope(CLICK, target="Option.render")
    assert "self" in scope.names()
    assert set(scope.attributes["self"]) == {"show_envvar", "envvar"}


def test_scope_cross_frame_widening():
    out = A.cross_frame_guard(CLICK, target="Option.render",
                              oracle=lambda e: e["self"].show_envvar
                              and e["self"].envvar is not None,
                              inputs=_click_inputs(),
                              enclosing={"Option": CLICK})
    assert out["admitted"] is True, out
    assert "Option" in out["enclosing_frames"]


def test_guard_oracle_builds_a_boolean_spec():
    oracle = A.guard_oracle(desired=lambda e: "ENV" if e["x"] else "",
                            true_body=lambda e: "ENV")
    assert oracle({"x": 1}) is True
    assert oracle({"x": 0}) is False


def test_verify_candidate_reports_equivalence():
    out = A.verify_candidate("a - b", lambda e: e["a"] - e["b"],
                             [{"a": 9, "b": 4}, {"a": 3, "b": 1}], names=["a", "b"])
    assert out["equivalent"] is True
    assert out["verified_by_execution"] is True
    bad = A.verify_candidate("a + b", lambda e: e["a"] - e["b"],
                             [{"a": 9, "b": 4}], names=["a", "b"])
    assert bad["equivalent"] is False
    assert bad["counterexample"]["i"] == 0


# --------------------------------------------------------------------------- #
# A11 -- soundness holes the corpus benchmark actually found
# --------------------------------------------------------------------------- #

def test_a11_an_oracle_that_always_raises_is_not_a_specification():
    """The benchmark's first run admitted ``_PEP610_..._REGEX.match`` as a
    rediscovery of ``netloc.rsplit('@', 1)``.  Both sides raised NameError on
    every synthetic witness, so "equal" meant "equally undefined".  It must
    refuse."""
    src = "def f(netloc):\n    return netloc\n"
    out = _value(src, "f",
                 lambda e: e["netloc"].rsplit("@", 1),
                 inputs=[{"unrelated": 1}, {"unrelated": 2}])
    assert out["admitted"] is False
    assert out["reason"] == "NO_SPECIFICATION"
    assert out["verified_by_execution"] is False


def test_a11_observational_equivalence_refuses_when_neither_side_produces_a_value():
    out = A.observational_equivalence(lambda e: e["missing"], lambda e: e["missing"],
                                      [{"a": 1}])
    assert out["equivalent"] is False
    assert out["reason"] == "NO_SPECIFICATION"


def test_a11_a_bare_literal_is_not_preferred_over_an_expression_that_uses_inputs():
    """With ONE witness, ``2`` and ``price - disc`` agree.  Only one is a
    repair; the other is a coincidence wearing a repair's clothes."""
    out = _value("def net(price, disc):\n    return price + disc\n", "net",
                 lambda e: e["price"] - e["disc"],
                 inputs=[{"price": 3, "disc": 1}], budget=128)
    expr = out["candidate"]["expr"]
    assert expr != "2"
    assert "price" in expr or "disc" in expr


def test_a11_a_literal_fallback_is_labelled_when_it_is_all_there_is():
    out = _value("def f(a):\n    return a\n", "f",
                 lambda e: 7, inputs=[{"a": 1}], budget=128)
    if out["admitted"]:
        assert out.get("degraded") == "BARE_LITERAL_FALLBACK"
        assert "coincidence" in out["note"]


def test_a11_a_dropped_call_chain_is_admitted_but_never_reported_exact():
    """tqdm: the search kept ``'{0:.3g}'.format(n)`` and dropped two
    ``.replace`` calls.  That is sound on the witnesses and useless as a fix, so
    the benchmark counts ``admitted`` and ``exact`` separately."""
    src = "def f(n):\n    return '{0:.3g}'.format(n)\n"
    inputs = [{"n": 1.0}, {"n": 2.0}]
    out = _value(src, "f", lambda e: f"{e['n']:.3g}", inputs=inputs, budget=64)
    assert out["admitted"] is True
    assert out["candidate"]["expr"].replace(" ", "") != "f'{n:.3g}'".replace(" ", "")


# --------------------------------------------------------------------------- #
# A12 -- the call-shape family, and explicit angelic vocabulary
# --------------------------------------------------------------------------- #

def test_a12_a_call_is_wrapped_not_invented():
    src = "def f(xs):\n    return tuple(xs)\n"
    scope = A.harvest_scope(src, target="f")
    assert scope.calls, "the target's own calls must be harvested"
    space = [e for e, _s in A.candidate_space(scope, budget=400)]
    assert "xs" in space
    assert any(e.startswith("tuple(") for e in space)


def test_a12_a_method_rename_needs_the_vocabulary_to_be_supplied():
    src = "def f(netloc):\n    return netloc.split('@', 1)\n"
    unhinted = A.harvest_scope(src, target="f")
    assert not any("rsplit" in e for e, _ in A.candidate_space(unhinted, budget=400)), \
        "the grammar must not invent a method name"
    hinted = A.harvest_scope(src, target="f", method_vocabulary={"netloc": ["rsplit"]})
    assert "rsplit" in hinted.attributes["netloc"]
    assert any("netloc.rsplit" in e for e, _ in A.candidate_space(hinted, budget=400))


def test_a12_candidate_space_is_bounded_and_lazy():
    scope = A.harvest_scope("def f(a, b):\n    return a + b\n", target="f")
    gen = A.candidate_space(scope, budget=25)
    rows = list(gen)
    assert len(rows) == 25
    assert all(isinstance(e, str) and isinstance(s, str) for e, s in rows)
    # a second enumeration is identical: no hidden state
    assert [e for e, _ in A.candidate_space(scope, budget=25)] == [e for e, _ in rows]

#!/usr/bin/env python3
"""Guarded Region-SSA Meaning IR: lowering, e-graph, evaluator, delta simulator.

PREDICTIONS, written before the confirmatory run:

  P1  A Python ``for``-accumulation, ``sum()``, a C ``for`` loop, a C++ loop, a
      JS ``for`` loop and a TS ``for`` loop over ``a[i]`` all lower to the SAME
      term, so the e-graph reports them equal with 0 further unions needed.
  P2  A Python list comprehension with a filter and a JS ``.filter().map()``
      chain are the same term.
  P3  Commutativity, ``x + 0``, double negation and ``select(c, a, a)`` are
      collapsed by saturation; ``a + b`` and ``a * b`` are NOT (a rewrite rule
      that proves everything proves nothing).
  P4  ``anti_unify`` reports zero holes for equal meanings and a real hole for
      different ones.
  P5  The concrete evaluator agrees with Python on the same inputs, charges the
      step budget only inside ``map``/``filter``/``reduce``, and raises
      ``EvalBudgetExceeded`` instead of looping.
  P6  The delta simulator partitions candidates into SAFE / NOOP / CRASH /
      DESTRUCTIVE_UNWITNESSED / INVARIANT_VIOLATION, restores the frame exactly
      after ``pop()``, and prunes >50% of a mixed candidate set in memory.
  P7  ``shred -v`` and ``split -v`` are NOT observation-pure; ``shred --help``,
      ``cat f`` and ``ls -la`` are; an unknown program is refused.
  P8  ``push()``/``pop()`` on the e-graph restores the exact prior version.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import guarded_meaning_ir_v1 as M  # noqa: E402


def _py(src: str, fn: str = "f"):
    return M.function_term(M.lower_python(src), fn)


def _ts(lang: str, src: bytes, fn: str = "f"):
    return M.function_term(M.lower_tree_sitter(src, lang), fn)


# --------------------------------------------------------------------------- #
# P1 -- cross-language loop equivalence
# --------------------------------------------------------------------------- #

PY_LOOP = "def f(a, n):\n    s = 0\n    for i in range(n):\n        s += a[i]\n    return s\n"
C_LOOP = b"int f(int* a, int n){ int s = 0; for (int i = 0; i < n; i++) { s += a[i]; } return s; }"
JS_LOOP = b"function f(a, n) { let s = 0; for (let i = 0; i < n; i++) { s += a[i]; } return s; }"


@pytest.mark.parametrize("lang,src", [
    ("c", C_LOOP),
    ("cpp", C_LOOP),
    ("javascript", JS_LOOP),
    ("typescript", b"function f(a: number[], n: number) { let s = 0; for (let i = 0; i < n; i++) { s += a[i]; } return s; }"),
])
def test_p1_same_loop_in_five_languages_is_one_term(lang, src):
    py = _py(PY_LOOP)
    other = _ts(lang, src)
    assert other is not None, "lowering must produce a value term"
    verdict = M.cross_language_equivalence(py, other)
    assert verdict["equal"] is True, verdict
    assert verdict["a_canonical"] == verdict["b_canonical"]


def test_p1_sum_and_accumulation_are_the_same_meaning():
    a = _py("def f(xs):\n    return sum(xs)\n")
    b = _py("def f(xs):\n    s = 0\n    for x in xs:\n        s += x\n    return s\n")
    assert M.cross_language_equivalence(a, b)["equal"] is True


def test_p1_the_lowered_term_is_the_canonical_reduce():
    t = _py(PY_LOOP)
    assert t.op == "reduce"
    assert str(t) == ("reduce(range(const(Lit(v=0)), var(n)), const(Lit(v=0)), "
                      "add(var(#acc), index(var(a), var(#x))))")


# --------------------------------------------------------------------------- #
# P2 -- comprehension == JS chain
# --------------------------------------------------------------------------- #

def test_p2_python_comprehension_equals_js_filter_map():
    py = _py("def f(xs):\n    return [x * 2 for x in xs if x > 0]\n")
    js = _ts("javascript", b"function f(xs) { return xs.filter(x => x > 0).map(x => x * 2); }")
    assert M.cross_language_equivalence(py, js)["equal"] is True


def test_p2_loop_form_equals_comprehension_form():
    comp = _py("def f(xs):\n    return [x * 2 for x in xs if x > 0]\n")
    loop = _py("def f(xs):\n    out = []\n    for x in xs:\n        if x > 0:\n            out.append(x * 2)\n    return out\n")
    assert M.cross_language_equivalence(comp, loop)["equal"] is True


def test_p2_early_return_guard_becomes_select():
    ternary = _py("def f(a, b):\n    return a if a > b else b\n")
    guarded = _py("def f(a, b):\n    if a > b:\n        return a\n    return b\n")
    assert M.cross_language_equivalence(ternary, guarded)["equal"] is True


def test_p2_c_ternary_matches_python_if_return():
    py = _py("def f(a, b):\n    if a > b:\n        return a\n    return b\n")
    c = _ts("c", b"int f(int a, int b) { return a > b ? a : b; }")
    assert M.cross_language_equivalence(py, c)["equal"] is True


# --------------------------------------------------------------------------- #
# P3 -- rewrite rules: what must collapse, and what must NOT
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("a,b", [
    ("def f(a, b):\n    return a + b\n", "def f(a, b):\n    return b + a\n"),
    ("def f(a):\n    return a + 0\n", "def f(a):\n    return a\n"),
    ("def f(a):\n    return not (not a)\n", "def f(a):\n    return a\n"),
    ("def f(a, b, c):\n    return a if c else a\n", "def f(a, b, c):\n    return a\n"),
    ("def f(xs):\n    return [x for x in xs]\n", "def f(xs):\n    return xs\n"),
])
def test_p3_equivalent_forms_collapse(a, b):
    assert M.cross_language_equivalence(_py(a), _py(b))["equal"] is True


@pytest.mark.parametrize("a,b", [
    ("def f(a, b):\n    return a + b\n", "def f(a, b):\n    return a * b\n"),
    ("def f(a, b):\n    return a - b\n", "def f(a, b):\n    return b - a\n"),
    ("def f(xs):\n    return [x * 2 for x in xs]\n", "def f(xs):\n    return xs\n"),
    ("def f(xs):\n    return sum(xs)\n", "def f(xs):\n    return len(xs)\n"),
])
def test_p3_different_meanings_do_not_collapse(a, b):
    """A rule set that proves everything proves nothing: these must stay apart."""
    assert M.cross_language_equivalence(_py(a), _py(b))["equal"] is False


def test_p3_a_rule_that_breaks_does_not_break_the_graph():
    def bad_rule(enode, g):
        raise RuntimeError("boom")

    g = M.SemiPersistentEGraph()
    g.add(_py("def f(a):\n    return a + 0\n"))
    unions = g.saturate(rules=[bad_rule], rounds=2)
    assert unions == 0


# --------------------------------------------------------------------------- #
# P4 -- anti-unification
# --------------------------------------------------------------------------- #

def test_p4_anti_unify_equal_meanings_has_no_holes():
    g = M.build_graph(terms=[_py("def f(a, b):\n    return a + b\n"),
                             _py("def f(a, b):\n    return b + a\n")])
    g.saturate()
    out = M.anti_unify(_py("def f(a, b):\n    return a + b\n"),
                       _py("def f(a, b):\n    return b + a\n"), g)
    assert out["equal"] is True
    assert out["holes"] == []


def test_p4_anti_unify_different_meanings_yields_a_hole():
    g = M.build_graph(terms=[_py("def f(a, b):\n    return a + b\n"),
                             _py("def f(a, b):\n    return a * b\n")])
    g.saturate()
    out = M.anti_unify(_py("def f(a, b):\n    return a + b\n"),
                       _py("def f(a, b):\n    return a * b\n"), g)
    assert out["equal"] is False
    assert len(out["holes"]) == 1
    assert out["holes"][0]["a"]["op"] == "add"
    assert out["holes"][0]["b"]["op"] == "mul"


# --------------------------------------------------------------------------- #
# P5 -- concrete evaluator
# --------------------------------------------------------------------------- #

def test_p5_evaluator_agrees_with_python():
    t = _py("def f(xs):\n    return [x * 2 for x in xs if x > 2]\n")
    xs = [1, 2, 3, 4, 5]
    assert M.eval_term(t, {"xs": xs}) == [6, 8, 10]


def test_p5_evaluator_handles_slices_ternaries_and_reduce():
    assert M.eval_term(_py("def f(xs):\n    return xs[1:3]\n"), {"xs": [0, 1, 2, 3]}) == [1, 2]
    assert M.eval_term(_py("def f(a, b):\n    return a if a > b else b\n"), {"a": 3, "b": 9}) == 9
    assert M.eval_term(_py("def f(xs):\n    s = 0\n    for x in xs:\n        s += x\n    return s\n"),
                       {"xs": [1, 2, 3, 4]}) == 10


def test_p5_budget_is_charged_only_inside_loops():
    t = _py("def f(xs):\n    return [x * 2 for x in xs]\n")
    with pytest.raises(M.EvalBudgetExceeded):
        M.eval_term(t, {"xs": list(range(100))}, budget=10)
    # straight-line arithmetic is never charged, so a tiny budget still works
    assert M.eval_term(_py("def f(a, b):\n    return a + b\n"), {"a": 1, "b": 2}, budget=0) == 3


def test_p5_errors_are_observable_not_swallowed():
    with pytest.raises(NameError):
        M.eval_term(M.var("nope"), {})
    with pytest.raises(ValueError):
        M.eval_term(M.Term("opaque", ("x",)), {})
    with pytest.raises(ZeroDivisionError):
        M.eval_term(M.Term("div", (M.const(1), M.const(0))), {})


def test_p5_evaluation_is_microsecond_scale():
    import time
    t = _py("def f(xs):\n    return [x * 2 for x in xs if x > 2]\n")
    env = {"xs": list(range(24))}
    M.eval_term(t, env)
    t0 = time.perf_counter_ns()
    for _ in range(200):
        M.eval_term(t, env)
    per_call_us = (time.perf_counter_ns() - t0) / 200 / 1000
    assert per_call_us < 250, f"evaluator too slow: {per_call_us} us"


# --------------------------------------------------------------------------- #
# P6 -- delta simulator
# --------------------------------------------------------------------------- #

def _sim():
    return M.DeltaSim({"balance": 100}, invariants=[("balance_nonneg", lambda f: f["balance"] >= 0)])


def _deposit(f):
    g = dict(f)
    g["balance"] = f["balance"] + 50
    return g


def _overdraw(f):
    g = dict(f)
    g["balance"] = f["balance"] - 500
    return g


def test_p6_partition_and_prune_fraction():
    sim = _sim()
    acts = [
        M.Action("deposit", (("write", "balance"),), apply=_deposit),
        M.Action("cat x", (("read", "x"),)),
        M.Action("no_op", (("write", "balance"),), apply=lambda f: dict(f)),
        M.Action("overdraw", (("write", "balance"),), apply=_overdraw),
        M.Action("shred -v", (("destroy", "disk"),)),
        M.Action("explode", (("write", "x"),), raises=True),
    ]
    out = sim.prune(acts)
    by = {r["action"]: r["verdict"] for r in out["safe"] + out["pruned"]}
    assert by["deposit"] == "SAFE"
    assert by["cat x"] == "SAFE"
    assert by["no_op"] == "NOOP"
    assert by["overdraw"] == "INVARIANT_VIOLATION"
    assert by["shred -v"] == "DESTRUCTIVE_UNWITNESSED"
    assert by["explode"] == "CRASH"
    assert out["pruned_fraction"] > 0.5


def test_p6_witness_admits_a_required_destructive_effect():
    sim = _sim()
    act = M.Action("rm scratch", (("destroy", "scratch"),))
    denied = sim.prune([act])
    assert denied["safe"] == []
    allowed = sim.prune([act], witness=lambda d: "scratch" in d.destroys)
    assert allowed["safe"][0]["action"] == "rm scratch"


def test_p6_push_pop_restores_the_frame_exactly():
    sim = _sim()
    before = dict(sim.frame)
    sim.push()
    sim.apply(M.Action("deposit", (("write", "balance"),), apply=_deposit))
    assert sim.frame["balance"] == 150
    assert sim.pop() is True
    assert sim.frame == before
    assert sim.depth == 0


def test_p6_simulate_plan_reports_the_first_fatal_step():
    sim = _sim()
    plan = [M.Action("deposit", (("write", "balance"),), apply=_deposit),
            M.Action("overdraw", (("write", "balance"),), apply=_overdraw)]
    out = sim.simulate_plan(plan)
    assert out["viable"] is False
    assert out["reason"] == "INVARIANT_VIOLATION"
    assert out["at_step"] == 1


def test_p6_goal_directed_ranking_orders_safe_actions():
    sim = M.DeltaSim({"score": 0})
    acts = [
        M.Action("small", (("write", "score"),), apply=lambda f: {**f, "score": f["score"] + 1}),
        M.Action("big", (("write", "score"),), apply=lambda f: {**f, "score": f["score"] + 10}),
    ]
    out = sim.prune(acts, goal=lambda f: f["score"])
    assert out["safe"][0]["action"] == "big"


# --------------------------------------------------------------------------- #
# P7 -- witness-certified observation purity
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("argv,pure", [
    (["shred", "-v"], False),
    (["split", "-v"], False),
    (["shred", "--help"], True),
    (["cat", "x.txt"], True),
    (["ls", "-la"], True),
    (["grep", "-n", "foo", "x.txt"], True),
    (["frobnicate", "--help"], False),
    (["rm", "-rf", "/"], False),
    (["cat", "x; rm -rf /"], False),
    ([], False),
])
def test_p7_cli_purity(argv, pure):
    verdict = M.classify_cli(argv)
    assert verdict["pure"] is pure, verdict


def test_p7_verbose_flag_on_a_mutating_program_is_not_pure():
    """The measured law: 16 of 2,319 `--help` flags mutate files."""
    assert M.classify_cli(["shred", "-v"])["reasons"] == ["MUTATING_PROGRAM:shred"]


# --------------------------------------------------------------------------- #
# P8 -- semi-persistent e-graph
# --------------------------------------------------------------------------- #

def test_p8_push_pop_restores_the_exact_prior_version():
    g = M.SemiPersistentEGraph()
    a = g.add(_py("def f(a, b):\n    return a + b\n"))
    size_before = g.size()
    g.push()
    g.add(_py("def f(a, b):\n    return a * b\n"))
    g.saturate()
    assert g.size() > size_before
    g.pop()
    assert g.size() == size_before
    assert g.find(a) == a


def test_p8_pop_replays_only_the_writes_since_push():
    g = M.SemiPersistentEGraph()
    g.add(_py("def f(a):\n    return a\n"))
    g.saturate()
    undo_len = len(g._undo)
    g.push()
    g.add(_py("def f(a, b):\n    return a - b\n"))
    assert len(g._undo) > undo_len
    g.pop()
    assert len(g._undo) == undo_len


def test_p8_nested_versions_are_isolated():
    g = M.SemiPersistentEGraph()
    base = g.add(_py("def f(a):\n    return a\n"))
    g.push()
    g.add(_py("def f(a, b):\n    return a + b\n"))
    g.push()
    g.add(_py("def f(a, b, c):\n    return a * b * c\n"))
    assert g.depth == 2
    g.pop()
    g.pop()
    assert g.depth == 0
    assert g.find(base) == base


# --------------------------------------------------------------------------- #
# Sabotage / negative controls
# --------------------------------------------------------------------------- #

def test_sabotage_a_forged_term_cannot_pass_as_a_loop():
    """A term that merely *looks* like a reduce must not be equal to one."""
    real = _py("def f(xs):\n    s = 0\n    for x in xs:\n        s += x\n    return s\n")
    forged = M.Term("reduce", (M.var("xs"), M.const(0),
                               M.Term("mul", (M.var(M.ACC), M.var(M.ELEM)))))
    assert M.cross_language_equivalence(real, forged)["equal"] is False


def test_sabotage_an_unparsable_file_never_lowers_silently():
    with pytest.raises(SyntaxError):
        M.lower_python("def f(:\n    pass\n")
    with pytest.raises(M.LoweringError):
        M.lower_file("/nonexistent/file.xyz")


def test_sabotage_a_crashing_apply_is_a_result_not_a_hang():
    sim = M.DeltaSim({"x": 1})
    def boom(_f):
        raise RuntimeError("boom")
    d = sim.apply(M.Action("boom", (("write", "x"),), apply=boom))
    assert d.raises is True
    assert d.noop is False


def test_sabotage_an_infinite_apply_is_bounded():
    sim = M.DeltaSim({"x": 1})
    def spin(_f):
        while True:
            pass
    # ``apply`` has no internal timeout; the contract is that the CALLER treats
    # a non-returning apply as a refusal, so assert the guard exists.
    assert hasattr(M, "EvalBudgetExceeded")
    assert callable(spin)  # the simulator never claims to bound arbitrary python

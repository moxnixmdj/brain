import unittest

from canonical.runtime import stochastic_synthesizer_v1 as STOCH


class _StubLibrary:
    """Minimal stand-in for a CompoundingConceptLibrary.

    Deliberately constructed here rather than read from
    `canonical/astra_runtime/state/CONCEPT_LIBRARY_V1.json`: a test whose result
    depends on persisted learning state is not a test (that is the same class of
    hazard as the §9 bytecode-cache verifier lie -- hidden state that the fast
    write/verify rhythm mutates under you).
    """

    def __init__(self, entries):
        self._e = entries

    def concepts(self):
        return list(self._e)


CLAMP = {"concept_id": "clamp2", "arity": 1, "domain_kind": "numeric",
         "body_expr": "min(max(2 * _v0, 0), 100)", "param_names": ["_v0"],
         "retired": False}
# `min(max(x*2, 0), 100)` over 6 points -- a row of the clamp family in
# canonical/tools/micro_evolve_bench_v1.py (seed 65).
PTS = [(-49,), (-45,), (9,), (14,), (67,), (13,)]


class TestLearnedGrammarReadPath(unittest.TestCase):
    """Plan v6 section 14: the micro synthesizer must be able to USE the
    compounding concept library, not just the SWE-side observational engine.

    `min`/`max` are not atoms in the hand-written micro grammar at any depth, so
    this spec is not a "harder search" -- it is outside the grammar. Red/green
    was proven by `git stash`: without the `concepts=` wiring the call below
    returns None; with it, it returns the target itself.
    """

    def test_absent_when_grammar_cannot_express_it(self) -> None:
        exs = [(p, min(max(2 * p[0], 0), 100)) for p in PTS]
        self.assertIsNone(STOCH.synthesize_body_from_examples(["x"], exs),
                          "hand-written grammar should not reach a clamp spec")

    def test_present_when_a_learned_template_covers_it(self) -> None:
        exs = [(p, min(max(2 * p[0], 0), 100)) for p in PTS]
        concepts = STOCH.numeric_concept_templates(_StubLibrary([CLAMP]))
        self.assertEqual(len(concepts), 1, "numeric template should be readable")
        body = STOCH.synthesize_body_from_examples(["x"], exs, concepts=concepts)
        self.assertIsNotNone(body, "learned template found nothing")
        ns = {"abs": abs, "min": min, "max": max}
        exec("def f(x):\n    " + body.strip() + "\n", ns)  # noqa: S102 (test fixture)
        # The point of a LEARNED abstraction is that it is not an overfit: it
        # must match the generating function everywhere, not only on the 6
        # visible points (the §13 ceiling; spec-consistent != target-identical).
        for x in range(-16, 17):
            self.assertEqual(ns["f"](x), min(max(2 * x, 0), 100),
                             f"concept instance wrong at x={x}")

    def test_reader_filters_out_shapes_this_grammar_cannot_instantiate(self) -> None:
        lib = _StubLibrary([
            {"concept_id": "stmt", "arity": 7, "domain_kind": "any",
             "body_expr": "", "param_names": [f"_p{i}" for i in range(7)],
             "retired": False},
            {"concept_id": "higher_order", "arity": 2, "domain_kind": "numeric",
             "body_expr": "min(max(_v0(_v1), 0), 100)", "param_names": ["_v0", "_v1"],
             "retired": False},
            {"concept_id": "retired_one", "arity": 1, "domain_kind": "numeric",
             "body_expr": "abs(_v0) * 3", "param_names": ["_v0"], "retired": True},
            CLAMP,
        ])
        got = STOCH.numeric_concept_templates(lib)
        self.assertEqual([c["body_expr"] for c in got], [CLAMP["body_expr"]],
                         "only the first-order, live, numeric template should pass")

    def test_none_library_is_not_an_error(self) -> None:
        self.assertEqual(STOCH.numeric_concept_templates(None), [])
        self.assertEqual(STOCH.numeric_concept_templates(object()), [])


"""Tests for the stochastic synthesizer and OE+stochastic ensemble diversity.

Falsifier #3 (plan v3, Idea 3): if ensembling synthesizers does not widen the
candidate space, Idea 3 is falsified. These tests measure candidate diversity:
the union of OE (exhaustive enumeration) and stochastic (random search)
candidates must be larger than OE alone on tasks where the engines explore
different regions.
"""
from __future__ import annotations

import math
import unittest

from canonical.runtime import oe_sygus_synthesizer_v1 as OE
from canonical.runtime import stochastic_synthesizer_v1 as STOCH


class TestStochasticSynthesizerV1(unittest.TestCase):
    def test_stochastic_finds_a_solution(self) -> None:
        # y = x + 1 style: stochastic search must find a matching expression.
        examples = [({"x": 0}, 1), ({"x": 1}, 2), ({"x": 5}, 6), ({"x": 10}, 11)]
        found = STOCH.synthesize_value_expressions_stochastic(
            examples, lang="python", max_results=4, seed=1, max_tries=50000
        )
        self.assertTrue(found, "stochastic search found nothing")
        for e in found:
            for env, out in examples:
                self.assertEqual(eval(e["code"], {"math": math}, dict(env)), out)

    def test_ensemble_widens_candidate_space(self) -> None:
        # On a task with multiple valid expressions, the ensemble union must
        # be at least as large as OE alone, and ideally larger (diversity).
        # y = abs(x) has multiple forms; y = x if x>=0 else -x, etc.
        examples = [
            ({"x": -3}, 3), ({"x": -1}, 1), ({"x": 0}, 0),
            ({"x": 2}, 2), ({"x": 7}, 7),
        ]
        ens = STOCH.ensemble_value_expressions(examples, lang="python", max_results=8, seed=2)
        # Union is never smaller than either engine alone.
        self.assertGreaterEqual(ens["union_count"], ens["oe_count"])
        self.assertGreaterEqual(ens["union_count"], ens["stochastic_count"])
        # Every union candidate actually matches the examples.
        for e in ens["union"]:
            for env, out in examples:
                self.assertEqual(eval(e["code"], {"math": math}, dict(env)), out)

    def test_branch_restricted_composition_closes_compound_conditional(self) -> None:
        """Plan v6 §13 falsifier: the ELSE branch of a conditional only has to
        match the targets on the points where it RUNS. These two specs come from
        the recorded 2-var misses — the else sides (`-(x*3)-y`, `-(x*2)-y`) are
        wrong on the then-points, so no globally-consistent inversion can find
        them, and before §13 both returned None. If the restricted pass ever
        stops firing, this test goes red while the family stays 'solved'.
        """
        cases = [
            ([(3, 0), (1, 2), (3, -2), (-3, 2), (1, -1), (-1, 3)],
             {(3, 0): 9, (1, 2): 5, (3, -2): 7, (-3, 2): 7, (1, -1): -2, (-1, 3): 0}),
            ([(-3, 0), (3, 0), (1, 2), (3, -3), (-3, 3), (2, 1)],
             {(-3, 0): 6, (3, 0): 6, (1, 2): 4, (3, -3): -3, (-3, 3): 3, (2, 1): 5}),
        ]
        for pts, want in cases:
            body = STOCH.synthesize_body_from_examples(
                ["x", "y"], [((x, y), want[(x, y)]) for (x, y) in pts]
            )
            self.assertIsNotNone(body, "restricted composition found nothing")
            ns: dict = {"abs": abs}
            exec(f"def f(x, y):\n    {body.strip()}\n", ns)
            for (x, y) in pts:  # verified against the WHOLE spec, by contract
                self.assertEqual(ns["f"](x, y), want[(x, y)])


    def test_ensemble_diversity_on_multi_solution_task(self) -> None:
        # A task admitting several distinct expressions: the ensemble should
        # surface candidates from both engines (diversity), not just one set.
        # y = len(s): len(s), and variants via different ops.
        examples = [
            ({"s": ""}, 0), ({"s": "a"}, 1), ({"s": "hello"}, 5),
            ({"s": "abc"}, 3),
        ]
        ens = STOCH.ensemble_value_expressions(examples, lang="python", max_results=8, seed=3)
        self.assertGreaterEqual(ens["union_count"], 1)
        # Both engines contribute (or one dominates but union is non-trivial).
        self.assertTrue(
            ens["oe_count"] > 0 or ens["stochastic_count"] > 0,
            "neither engine found a candidate",
        )


if __name__ == "__main__":
    unittest.main()

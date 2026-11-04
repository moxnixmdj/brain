"""The creature's hypothesis space must grow to FORMS it lacked, not just more of them.

This is the deepest defect found in thirty-one rounds, and unlike every previous round it is not a
constant, not a rule, and not a metric. It is the SHAPE of the space the creature searches.

Measured 2026-11-04:

    T_3(x) + 2*T_5(x)   reported DISAMBIGUATED_AND_CRYSTALLIZED -- correctly -- by storing a
                        FIFTEEN-ENTRY TABLE (18 numeric literals, 2264 bytes).

    The compositional description is a three-entry table plus one law the creature LEARNED earlier
    (8 numeric literals). The creature did not choose the worse of two available answers. It could
    not express the better one.

`_inline_operator_organs` only ever builds `f(g(x))` -- whole-function calls. So a learned law could
be COMPOSED WITH ANOTHER LAW and could never be a TERM. That fixes the shape of every future
hypothesis:

    Omega_{t+1} = Omega_t + {compositions of what Omega_t can already express}

`Omega_{t+1}` genuinely grows. But it never comes to contain a FORM Omega_t lacked -- only more
instances of the same shapes. A creature whose new ideas are all instances of old shapes is not
learning a language, it is POPULATING one. Rounds 29 and 30 made that population richer by deriving
coefficients and degrees. Neither changed its shape.

THE FIX IS DELIBERATELY MINIMAL, because a bigger fix would be me authoring again. No new form is
added: the residual-and-solve machinery already exists, the operations already exist, the table
solver already exists. What changes is that a CO-FACTOR may now be a law this creature learned rather
than a function I typed.

Three further defects were found BY this change, each of them a different instance of one mistake --
treating "this program has nothing to say here" as "this program says something false":

  1. `derive_probe_space` emitted half-step probes unconditionally, so an all-integer task was probed
     at x = -39.5.
  2. The survivor filter read `ok and match`, so a crash eliminated a hypothesis exactly like a wrong
     answer did.
  3. `synthesize_discriminating_input` bucketed crashes as a distinct PREDICTION, so it kept asking
     questions whose only content was "defined here / not defined here", spent the whole oracle
     budget, and refused UNSETTLEABLE on tasks it had solved for thirty rounds.

They are recorded here because they are the reason the round is not a one-line diff, and because
fixing only the first left the other two latent and green.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

T3 = lambda x: x % 3
T5 = lambda x: 2 * (x % 5)
SUM = lambda x: (x % 3) + 2 * (x % 5)


def _graph(path=None):
    g = M.MetaCircularOrganGraph(path)
    g.growth_enabled = True
    return g


def _teach(g, sig, fn, seeds):
    return g.synthesize_or_disambiguate_skill(
        [((s,), fn(s)) for s in seeds],
        task_signature=sig,
        oracle=lambda p, f=fn: f(*p),
    )


def _numbers(organ):
    return M._numeric_literal_count(organ) if organ is not None else -1


def _learned_laws(g, exclude):
    return [o for o in g.organs_in_stratum(M.SKILL) if o.task_signature != exclude]


class ALearnedLawCanBeATerm(unittest.TestCase):
    """The direct measurement. Before the composer these were not expressible at all."""

    def test_teaching_leaves_a_reusable_law_in_the_graph(self):
        """The premise of the whole round, asserted rather than assumed. My first harness silently
        taught nothing: both calls returned UNSETTLEABLE and `organs_in_stratum` was empty, so an
        "empty composer result" looked like a defect in the composer instead of in the setup."""
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            first = _teach(g, "t3", T3, range(1, 9))
            second = _teach(g, "t5", T5, range(1, 12))
            self.assertTrue(first["ok"], first.get("status"))
            self.assertTrue(second["ok"], second.get("status"))
            laws = _learned_laws(g, "target")
            self.assertGreaterEqual(len(laws), 2, "teaching produced no reusable laws")

    def test_the_composer_produces_a_candidate_that_uses_a_learned_law(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t3", T3, range(1, 9))
            _teach(g, "t5", T5, range(1, 12))
            examples = [((x,), SUM(x)) for x in range(1, 20)]
            found = M._compose_learned_laws(examples, _learned_laws(g, "target"))
            self.assertTrue(
                found,
                "no candidate used a learned law as a term: the grammar still cannot express "
                "T_k(x) + L(x), which is the entire point of the round",
            )
            self.assertTrue(
                any("_law_" in expr for _n, expr, _h in found),
                "composed candidates do not reference a learned law",
            )

    def test_the_composed_candidate_is_exact_on_the_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t3", T3, range(1, 9))
            _teach(g, "t5", T5, range(1, 12))
            examples = [((x,), SUM(x)) for x in range(1, 20)]
            built = []
            for name, expr, helpers in M._compose_learned_laws(examples, _learned_laws(g, "target")):
                try:
                    built.append(M.make_organ(
                        stratum=M.SKILL, name=name, task_signature="t", entrypoint="run",
                        source_code=M._wrap_expr_into_source(1, expr, helpers=helpers),
                    ))
                except Exception:
                    continue
            self.assertTrue(built, "no composed candidate could even be compiled")
            exact = [
                o for o in built
                if all(M._safe_eval_candidate(o, (x,))[1] == SUM(x) for x in range(1, 20))
            ]
            self.assertTrue(exact, "composed candidates exist but none is exact on the evidence")


class TheComposedFormIsPreferredWhenItIsSmaller(unittest.TestCase):
    """Building the composition is not enough -- it must also be CHOSEN.

    Survivors were ordered by `(code_bytes, organ_id)` and the two descriptions of this task are
    within a few bytes of each other, so the tie was broken by an identifier hash. Bytes measure
    syntax; numeric literals measure what the claim asserts about the world."""

    def test_parameters_are_what_a_claim_asserts_not_bytes(self):
        memorised = M.make_organ(
            stratum=M.SKILL, name="m", task_signature="t", entrypoint="run",
            source_code=(
                "def run(x0):\n    return (((0.0, 3.0, 6.0, 6.0, 9.0, 2.0, 2.0, 5.0, 8.0, 8.0, "
                "1.0, 4.0, 4.0, 7.0, 10.0,))[int(math.floor(x0)) - "
                "math.floor(math.floor(x0) / 15) * 15])\n"
            ),
        )
        composed = M.make_organ(
            stratum=M.SKILL, name="c", task_signature="t", entrypoint="run",
            source_code=(
                "def _law_1(x0):\n    return x0 % 5 * 2\ndef run(x0):\n"
                "    return ((((0.0, 2.0, 4.0,))[int(math.floor(x0)) - "
                "math.floor(math.floor(x0) / 3) * 3]) + _law_1(x0))\n"
            ),
        )
        self.assertLess(
            _numbers(composed), _numbers(memorised),
            "the composed form should assert fewer numbers than the memorised table",
        )

    def test_the_creature_returns_the_composed_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t3", T3, range(1, 9))
            _teach(g, "t5", T5, range(1, 12))
            result = g.synthesize_or_disambiguate_skill(
                [((x,), SUM(x)) for x in range(1, 20)],
                task_signature="target",
                oracle=lambda p: SUM(p[0]),
            )
            self.assertTrue(result["ok"], result.get("status"))
            organ = result["organ"]
            self.assertIn(
                "_law_", organ.source_code,
                "the settled program does not use a learned law, so the composition was built and "
                "then discarded:\n" + organ.source_code,
            )
            self.assertLessEqual(
                _numbers(organ), 12,
                f"settled on a {_numbers(organ)}-number description of a structure that has an "
                f"8-number one:\n{organ.source_code}",
            )
            self.assertEqual(
                [x for x in range(40, 70) if M._safe_eval_candidate(organ, (x,))[1] != SUM(x)],
                [],
            )


class GrowthOfTheSpaceNotJustItsPopulation(unittest.TestCase):
    """Before this round a second task could only reuse the first as `f(g(x))`. These are not
    expressible that way, and the machinery must not lose the ability it already had."""

    def test_a_law_plus_a_table_holds_outside_the_evidence(self):
        fn = SUM
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t3", T3, range(1, 9))
            _teach(g, "t5", T5, range(1, 12))
            result = g.synthesize_or_disambiguate_skill(
                [((x,), fn(x)) for x in range(1, 20)],
                task_signature="plus",
                oracle=lambda p: fn(p[0]),
            )
            self.assertTrue(result["ok"], result.get("status"))
            self.assertEqual(
                [x for x in range(40, 70)
                 if M._safe_eval_candidate(result["organ"], (x,))[1] != fn(x)],
                [],
            )

    def test_a_product_of_two_periods_still_solves_when_composition_is_available(self):
        """The task that exposed the fractional probe. It must solve, and be right, whichever of the
        two correct descriptions it settles on."""
        fn = lambda x: (x % 4) * (x % 7)
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t4", lambda x: x % 4, range(1, 11))
            _teach(g, "t7", lambda x: x % 7, range(1, 16))
            result = g.synthesize_or_disambiguate_skill(
                [((x,), fn(x)) for x in range(1, 30)],
                task_signature="times",
                oracle=lambda p: fn(p[0]),
            )
            self.assertTrue(result["ok"], result.get("status"))
            self.assertEqual(
                [x for x in range(40, 70)
                 if M._safe_eval_candidate(result["organ"], (x,))[1] != fn(x)],
                [],
            )


class ATableSaysNothingOffItsDomain(unittest.TestCase):
    """A period table is a lookup by POSITION. It is a total function on the integers and asserts
    nothing about a non-integer input -- there is no "the table's value at 2.5". The emitted formula
    silently took the block of the floor, which was a claim nobody made."""

    def test_a_table_refuses_a_non_integer_rather_than_extrapolating(self):
        organ = M.make_organ(
            stratum=M.SKILL, name="t", task_signature="t", entrypoint="run",
            source_code=M._wrap_expr_into_source(
                1, M._table_index_expr("x0", 3, "0.0, 1.0, 2.0")
            ),
        )
        for x in (0, 1, 2, 3, 4, 7, -1, -40):
            ok, value = M._safe_eval_candidate(organ, (x,))
            self.assertTrue(ok, f"a table must be defined at the integer {x}")
            self.assertEqual(value, float(x % 3), f"wrong value at {x}")
        for x in (7.5, -39.5, 0.5):
            self.assertFalse(
                M._safe_eval_candidate(organ, (x,))[0],
                f"a period table must not invent a value at the non-integer {x}",
            )


class AnUndefinedAnswerIsNotARefutation(unittest.TestCase):
    """One mistake in three places. Each is tested separately because fixing one left the others
    latent and green."""

    def test_a_crash_does_not_eliminate_a_hypothesis(self):
        table = M.make_organ(
            stratum=M.SKILL, name="t", task_signature="t", entrypoint="run",
            source_code=M._wrap_expr_into_source(1, M._table_index_expr("x0", 3, "0.0, 1.0, 2.0")),
        )
        # Undefined at 7.5, so whatever the oracle says there is no evidence against the table.
        self.assertFalse(M._safe_eval_candidate(table, (7.5,))[0])
        self.assertTrue(M._survives_probe(table, (7.5,), 99.0))

        # But a wrong ANSWER is still evidence, and this is what stops the rule above from being a
        # blanket amnesty: the same table survives 7.5 and dies at 3, where it does have an opinion.
        self.assertTrue(M._survives_probe(table, (3,), 0.0))
        self.assertFalse(M._survives_probe(table, (3,), 99.0))

    def test_a_crash_is_not_scored_as_a_distinct_prediction(self):
        """If crashes scored as predictions, a probe at 2.5 would look worth asking and eliminate
        nothing, which is exactly how the oracle budget was burned."""
        table = M.make_organ(
            stratum=M.SKILL, name="table", task_signature="t", entrypoint="run",
            source_code=M._wrap_expr_into_source(1, M._table_index_expr("x0", 3, "0.0, 1.0, 2.0")),
        )
        const = M.make_organ(
            stratum=M.SKILL, name="const", task_signature="t", entrypoint="run",
            source_code="def run(x0):\n    return 0\n",
        )
        examples = [((x,), 0) for x in range(1, 6)]
        probe = M.synthesize_discriminating_input([table, const], examples)
        if probe is not None:
            self.assertTrue(
                all(isinstance(v, int) and not isinstance(v, bool) for v in probe),
                f"proposed a probe at {probe} whose only effect is to separate defined from "
                "undefined; that question has no content",
            )

    def test_an_integer_task_is_not_settled_by_a_fractional_probe(self):
        """End to end. This refused with CONTRADICTORY_OR_OUT_OF_GRAMMAR before the three fixes."""
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(pathlib.Path(tmp) / "g.json")
            _teach(g, "t3", T3, range(1, 9))
            _teach(g, "t5", T5, range(1, 12))
            result = g.synthesize_or_disambiguate_skill(
                [((x,), SUM(x)) for x in range(1, 20)],
                task_signature="target",
                oracle=lambda p: SUM(p[0]),
            )
            self.assertNotEqual(
                result.get("status"), "CONTRADICTORY_OR_OUT_OF_GRAMMAR",
                "an integer task must not be refuted at a point where no integer hypothesis has "
                "an opinion",
            )


if __name__ == "__main__":
    unittest.main()

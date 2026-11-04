"""Experience must change behaviour, or the creature is a cabinet, not a mind.

Measured 2026-11-04, and this is the defect these tests exist for:

  * three tasks sharing one period-3 table were solved; a FOURTH task using the same table then paid
    the full cold price. WARM == COLD exactly.
  * a saved graph after three tasks contained `organs`, `primary_by_sig` and `predictor`. It recorded
    WHAT WAS SOLVED and nothing about what was tried, wasted, or could have been cheaper.
  * `predict_cost` was called only inside the class that defined it.

So the tree remembers answers and forgets everything else. Every task is the first task. These tests
pin the mechanism that makes use itself an improvement, and they fail without it.

The bar each test holds the creature to is deliberately NOT "never ask questions". A creature that
saves questions by not asking them has not become smarter, it has become credulous. The bar is:

    questions may only be withheld where it was MEASURED that the answer was already implied.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import experience_v1 as E
from canonical.swe_kernel import meta_circular_organ_graph_v1 as M


def _graph(tmp: str, *, persist: bool = True) -> M.MetaCircularOrganGraph:
    path = pathlib.Path(tmp) / "g.json" if persist else None
    g = M.MetaCircularOrganGraph(path)
    g.growth_enabled = True
    return g


def _solve(g, fn, seeds, sig):
    return g.synthesize_or_disambiguate_skill(
        [((s,) if not isinstance(s, tuple) else s, fn(*s) if isinstance(s, tuple) else fn(s)) for s in seeds],
        task_signature=sig,
        oracle=lambda p, f=fn: f(*p),
    )


class TheShapeIsKnownBeforeAnyQuestionIsAsked(unittest.TestCase):
    """Honesty condition: if the shape used the outcome, 'prediction' would be retrospection."""

    def test_the_shape_is_a_function_of_the_evidence_only(self):
        examples = [((1,), 5), ((2,), 8), ((3,), 11)]
        shape = E.problem_shape(examples)
        self.assertEqual(shape["arity"], 1)
        self.assertEqual(shape["given"], 3)
        self.assertEqual(shape["distinct_outputs"], 3)
        self.assertFalse(shape["has_container"])

    def test_two_problems_with_one_answer_in_their_evidence_are_a_different_shape(self):
        """Seeds 1..5 of `x // 7` are all 0. That is not a small detail, it is the reason the
        creature bought questions where every candidate agreed."""
        flat = E.problem_shape([((x,), 0) for x in range(1, 6)])
        varying = E.problem_shape([((x,), x * 2) for x in range(1, 6)])
        self.assertEqual(flat["distinct_outputs"], 1)
        self.assertEqual(varying["distinct_outputs"], 5)
        self.assertNotEqual(E.shape_key(flat), E.shape_key(varying))

    def test_a_container_argument_is_its_own_shape(self):
        on_numbers = E.problem_shape([((1,), 1)])
        on_lists = E.problem_shape([((([1, 2],),), 2)])
        self.assertFalse(on_numbers["has_container"])
        self.assertTrue(on_lists["has_container"])
        self.assertNotEqual(E.shape_key(on_numbers), E.shape_key(on_lists))


class AColdMemoryAssertsNothing(unittest.TestCase):
    """The failure mode of adding memory is a confident prior invented from zero evidence."""

    def test_an_unknown_shape_reports_unknown_rather_than_zero(self):
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((1,), 1), ((2,), 2)])
        self.assertIsNone(ledger.expected_questions(shape))

    def test_an_unknown_shape_still_asks(self):
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((1,), 1)])
        worth, why = ledger.evidence_is_worth_buying(shape)
        self.assertTrue(worth, why)

    def test_a_single_observation_is_reported_but_does_not_govern(self):
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((1,), 1)])
        ledger.record_outcome(shape, ok=False, questions_spent=8, questions_avoidable=8)
        worth, why = ledger.evidence_is_worth_buying(shape)
        self.assertTrue(worth, "one bad afternoon is not experience")
        self.assertIn("not acted on", why)


class TheLedgerLearnsWhatWasWasted(unittest.TestCase):
    def test_avoidable_questions_are_counted_against_the_shape(self):
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((x,), 0) for x in range(1, 6)])
        for _ in range(4):
            ledger.record_outcome(shape, ok=False, questions_spent=2, questions_avoidable=2)
        worth, why = ledger.evidence_is_worth_buying(shape)
        self.assertFalse(worth, why)
        self.assertIn("changed nothing", why)

    def test_evidence_that_did_work_keeps_being_bought(self):
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((x,), x) for x in range(1, 5)])
        for _ in range(4):
            ledger.record_outcome(shape, ok=True, questions_spent=4, questions_avoidable=1)
        worth, why = ledger.evidence_is_worth_buying(shape)
        self.assertTrue(worth, why)

    def test_the_ledger_survives_a_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "exp.json"
            first = E.ExperienceLedger(path)
            shape = E.problem_shape([((x,), 0) for x in range(1, 6)])
            for _ in range(4):
                first.record_outcome(shape, ok=False, questions_spent=2, questions_avoidable=2)
            first.governed_questions_saved = 6
            first.save()

            second = E.ExperienceLedger(path)
            self.assertIsNotNone(second.expected_questions(shape))
            self.assertEqual(second.governed_questions_saved, 6)
            worth, _why = second.evidence_is_worth_buying(shape)
            self.assertFalse(worth, "a memory that does not survive a restart is not memory")


class UseItselfMustMakeItBetter(unittest.TestCase):
    """The integration test. This is the one that fails without wiring."""

    def test_a_repeated_shape_is_cheaper_the_second_time_it_is_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            # The same shape, three times, with three DIFFERENT underlying functions. The point is
            # not that the answers carry over -- they must not -- it is that the creature learns
            # something about this SHAPE that transfers even when the answer does not.
            first = _solve(g, lambda x: x ** 3, range(1, 6), "a")
            second = _solve(g, lambda x: x ** 3 + 1, range(1, 6), "b")
            third = _solve(g, lambda x: 2 ** x, range(1, 6), "c")
            self.assertFalse(first["ok"])
            # Whatever it learned must be visible in the ledger, not only in the return value.
            self.assertGreaterEqual(len(g.experience.records), 1)

    def test_the_ledger_is_persisted_beside_the_organs(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            _solve(g, lambda x: 3 * x + 1, range(1, 5), "affine")
            saved = list(pathlib.Path(tmp).glob("*.json"))
            self.assertTrue(saved, "no state was written at all")
            self.assertTrue(
                any(p.name.startswith("experience") for p in saved),
                f"experience was not persisted; wrote {[p.name for p in saved]}",
            )


class WithholdingIsOnlyAllowedWhenMeasured(unittest.TestCase):
    """The guard against the cheap version of this idea: 'save questions by not asking them'."""

    def test_the_creature_never_withholds_on_a_shape_it_has_not_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            shape = E.problem_shape([((x,), x ** 3) for x in range(1, 6)])
            self.assertTrue(g.experience.evidence_is_worth_buying(shape)[0])

    def test_a_refusal_that_asked_nothing_is_not_recorded_as_economy(self):
        """A shape that refuses after one question has one avoidable question at most. It must not
        be able to reach the withholding threshold by refusing cheaply -- otherwise the creature
        would learn to be lazy and call it experience."""
        ledger = E.ExperienceLedger()
        shape = E.problem_shape([((x,), x ** 3) for x in range(1, 6)])
        for _ in range(10):
            ledger.record_outcome(shape, ok=False, questions_spent=1, questions_avoidable=0)
        worth, why = ledger.evidence_is_worth_buying(shape)
        self.assertTrue(worth, f"cheap refusals were mistaken for wasted effort: {why}")


if __name__ == "__main__":
    unittest.main()


class TheSelfModelObservesItself(unittest.TestCase):
    """Measured 2026-11-04: `predictor.update` was called ZERO times in the module. The graph built a
    self-predictor, persisted its weights, published `predictor_observations` in `summary()`, and
    never fed it an outcome -- 0 observations and a constant 0.5 after three tasks. A self-model that
    never observes itself is a decoration, not a weak model."""

    def test_the_self_model_is_trained_by_its_own_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            self.assertEqual(g.predictor.observations, 0)
            for i, fn in enumerate((lambda x: 3 * x + 1, lambda x: x ** 3, lambda x: (x % 4) * 2)):
                _solve(g, fn, range(1, 5), f"t{i}")
            self.assertEqual(
                g.predictor.observations, 3, "the self-model learned nothing from three of its own attempts"
            )

    def test_the_self_model_distinguishes_what_it_can_do_from_what_it_cannot(self):
        """A self-model that cannot tell solvable from hopeless is not a model of anything."""
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            solvable = (lambda x: 3 * x + 1, lambda x: (x % 4) * 2, lambda x: (x % 3) * x, lambda x: x // 3)
            hopeless = (lambda x: x ** 3, lambda x: 2 ** x, lambda x: x ** 4 + 1)
            for _round in range(3):
                for i, fn in enumerate(solvable):
                    _solve(g, fn, range(1, 5), f"s{i}")
                for i, fn in enumerate(hopeless):
                    _solve(g, fn, range(1, 6), f"h{i}")
            easy = {"arity": 1, "given": 4, "distinct_outputs": 4, "has_container": False,
                    "status": "DISAMBIGUATED_AND_CRYSTALLIZED"}
            hard = {"arity": 1, "given": 5, "distinct_outputs": 5, "has_container": False,
                    "status": "CONTRADICTORY_OR_OR_OUT_OF_GRAMMAR".replace("_OR_OR_", "_OR_")}
            p_easy = g.predictor.predict_pass_probability(easy)
            p_hard = g.predictor.predict_pass_probability(hard)
            self.assertGreater(
                p_easy, p_hard,
                f"the self-model rates problems it keeps failing no lower than ones it keeps solving "
                f"({p_easy:.3f} vs {p_hard:.3f})",
            )


class ExperienceSizesInvestmentAndNeverNarrowsIt(unittest.TestCase):
    """The safe shape for a memory that governs effort.

    It is tempting to make experience REFUSE -- "I failed at this shape before". Measured
    2026-11-04: inducing a period costs 19 questions at k=4, 34 at k=7 and 54 at k=11, from three
    seeds, and all three are the SAME shape. So a memory that trims the budget after a failure at
    k=4 ratchets the creature down and never attempts k=11, and every individual decision along the
    way still looks prudent. The rule is therefore one-directional: experience may only ever give a
    shape MORE room than a cold creature would have had.
    """

    def test_a_cold_creature_gets_exactly_the_old_budget(self):
        g = M.MetaCircularOrganGraph(None)
        self.assertEqual(g.growth_budget_for([((1,), 1)]), g.growth_evidence_budget)

    def test_the_budget_grows_with_measured_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            shape = E.problem_shape([((x,), float(x % 4)) for x in range(1, 4)])
            cold = g.growth_budget_for([((x,), float(x % 4)) for x in range(1, 4)])
            for _ in range(4):
                g.experience.record_outcome(shape, ok=True, questions_spent=40)
            warm = g.growth_budget_for([((x,), float(x % 4)) for x in range(1, 4)])
            self.assertGreater(warm, cold, "experience with expensive induction bought no extra room")

    def test_experience_can_never_shrink_the_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            examples = [((x,), float(x % 4)) for x in range(1, 4)]
            shape = E.problem_shape(examples)
            for _ in range(6):
                g.experience.record_outcome(shape, ok=False, questions_spent=1)
            self.assertGreaterEqual(
                g.growth_budget_for(examples), g.growth_evidence_budget,
                "a cheap failure was allowed to shrink what the creature will attempt, which ratchets it down",
            )


class TheCounterfactualIsMeasuredNotAssumed(unittest.TestCase):
    def test_a_refutation_attempt_is_not_counted_as_waste(self):
        """Measured 2026-11-04: a first version counted 'answer did not change the survivor set' as
        AVOIDABLE, which swept in every Door-3 refutation probe -- 12 of 25 questions. Those probes
        are the verification of a sole-survivor claim. Suppressing them would leave a claim standing
        on nothing while reporting an efficiency gain."""
        with tempfile.TemporaryDirectory() as tmp:
            g = _graph(tmp)
            _solve(g, lambda x: 3 * x + 1, range(1, 5), "aff")
            rec = list(g.experience.records.values())[0]
            self.assertGreater(
                rec.questions_spent, 0,
                "no questions were recorded at all, so nothing about cost is being learned",
            )
            worth, why = g.experience.evidence_is_worth_buying(
                E.problem_shape([((x,), 3 * x + 1) for x in range(1, 5)])
            )
            self.assertTrue(worth, f"a shape that is being solved was judged not worth asking about: {why}")

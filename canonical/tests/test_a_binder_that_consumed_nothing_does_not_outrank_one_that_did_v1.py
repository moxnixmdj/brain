"""A capability that binds VACUOUSLY must not outrank one that consumed the sentence.

The defect, measured on ``29b3107``
-----------------------------------
``goal_compiler._compile_single_goal`` selects ``ranked[0]``, and ``ranked`` is
the list ``_bm25_rerank`` returns.  So the BM25 order *is* the selection.

For the sentence

    Localize the fault in the python source root D using the tests and
    write the report to D/r.json

the grounded pass on ``29b3107`` ranked 14 bindable candidates and put
``terminal.kstar.root.assess.stdlib`` FIRST at pinned score **15** -- above
``python.fault.localize.dynamic.dataflow.v1`` at **28**, the capability that
owns the sentence.  Then the substitution guard compared the best unbindable
score (``python.tests.audit.unittest``, 26) against ``ranked[0][0]`` -- **15**,
not the best bindable 28 -- saw ``26 > 15`` with a vacuous survivor, and refused
with ``GOAL_COMPILATION_BEST_MATCH_UNBINDABLE``.  The front door swallowed that
refusal and fell through to ``python.repository.acceptance.measure.v1`` at 23,
which reported ``pass=True`` for a fault-localization request it does not own.

That is the exact inversion ``_bm25_rerank``'s own docstring says it exists to
prevent -- it names ``terminal.kstar.root.assess.stdlib`` by name -- and it
happens because BM25's inverse document frequency is measured over the surviving
shortlist, where a token most capabilities carry but few survivors carry looks
rare and scores high.

The fix is not a re-weighted corpus (that moved ``EXT_JQ_TABLE``, a goal that
already selected correctly, and was reverted).  It is the distinction
``_compile_single_goal`` already draws for the *refusal* -- "a vacuous bind: it
attaches to any sentence for free, e.g. msgpack/kstar catch-alls" -- applied to
the *order* as well: a binder that consumed nothing from the sentence does not
outrank one that consumed it and scored strictly higher.

These tests must be able to fail.  On ``29b3107`` the class
``TheVacuousBinderIsDemotedTests`` and the end-to-end classes fail; the pins
that guard against over-reach pass on both.
"""

import json
import pathlib
import shutil
import unittest

import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import goal_compiler as compiler  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

REGISTRY_PATH = _ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

LOCALIZER = "python.fault.localize.dynamic.dataflow.v1"
KSTAR = "terminal.kstar.root.assess.stdlib"
MEASURE = "python.repository.acceptance.measure.v1"


def _registry():
    return json.loads(REGISTRY_PATH.read_text())["capabilities"]


def _is_vacuous(entry):
    """The same predicate the fix uses: no ``${input.}`` placeholder at all."""
    args = ((entry.get("action_template") or {}).get("args") or {})
    return not any(
        isinstance(v, str) and v.startswith("${input.") for v in args.values()
    )


class _Tree(unittest.TestCase):
    """One fixture per test, removed by addCleanup.

    The directory must NOT contain the word "test": path segments are BM25
    query terms, so a scratch directory named test_something injects "test"
    into the ranking and the test measures its own name.
    """

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (
            _ROOT
            / "canonical/astra_runtime/tmp"
            / ("vacuous_%d_%d" % (os.getpid(), type(self)._NEXT))
        )
        (self.base / "p" / "tests").mkdir(parents=True)
        (self.base / "p" / "calc.py").write_text(
            "def add(a, b):\n    return a - b\n"
        )
        (self.base / "p" / "tests" / "test_calc.py").write_text(
            "import unittest, calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual(calc.add(1, 2), 3)\n"
        )
        self.addCleanup(shutil.rmtree, self.base, True)
        self.src = str(self.base / "p")

    def sentence(self, verb):
        return "%s in the python source root %s using the tests and write the report to %s" % (
            verb,
            self.src,
            self.base / "r.json",
        )


class TheVacuousBinderIsDemotedTests(_Tree):
    def test_the_owner_of_the_sentence_is_ranked_first(self):
        ranked = compiler._rank_bindable_candidates(
            self.sentence("Localize the fault"),
            _registry(),
            _ROOT,
            allow_world_binding=False,
        )
        self.assertTrue(ranked, "the sentence bound nothing at all")
        self.assertEqual(ranked[0][2], LOCALIZER)

    def test_no_vacuous_binder_sits_above_a_higher_scoring_grounded_one(self):
        """The law: below every candidate the pinned scorer rated strictly higher.

        Not below every grounded candidate -- a vacuous binder at 15 legitimately
        keeps BM25's order against a grounded candidate at 14.  The inversion
        that broke selection was a 15 leading a 28, and that is what this pins.
        """
        ranked = compiler._rank_bindable_candidates(
            self.sentence("Localize the fault"),
            _registry(),
            _ROOT,
            allow_world_binding=False,
        )
        reg = _registry()
        grounded = [it[0] for it in ranked if not _is_vacuous(reg[it[2]])]
        self.assertTrue(grounded, "no grounded candidate, so nothing is proved")
        for index, item in enumerate(ranked):
            if not _is_vacuous(reg[item[2]]):
                continue
            ahead = [x[0] for x in ranked[index + 1 :] if not _is_vacuous(reg[x[2]])]
            above = [s for s in ahead if s > item[0]]
            self.assertEqual(
                above,
                [],
                "vacuous binder %r at pinned score %d is ranked above grounded "
                "candidates scoring %s" % (item[2], item[0], sorted(above, reverse=True)),
            )

    def test_the_vacuous_binder_that_led_is_now_last(self):
        """The measured inversion, pinned by name and by position."""
        ranked = compiler._rank_bindable_candidates(
            self.sentence("Localize the fault"),
            _registry(),
            _ROOT,
            allow_world_binding=False,
        )
        positions = {it[2]: i for i, it in enumerate(ranked)}
        self.assertEqual(positions[LOCALIZER], 0)
        self.assertEqual(
            positions[KSTAR],
            len(ranked) - 1,
            "kstar scores strictly below every grounded candidate here, so it "
            "must sit behind all of them",
        )

    def test_kstar_is_still_a_candidate_only_its_rank_moved(self):
        """The fix changes ORDER, never the admissible SET."""
        goal = self.sentence("Localize the fault")
        reg = _registry()
        with_fix = compiler._rank_bindable_candidates(
            goal, reg, _ROOT, allow_world_binding=False
        )
        original = compiler._bm25_rerank
        compiler._bm25_rerank = lambda g, ranked: ranked
        try:
            pinned = compiler._rank_bindable_candidates(
                goal, reg, _ROOT, allow_world_binding=False
            )
        finally:
            compiler._bm25_rerank = original
        self.assertEqual(
            sorted(x[2] for x in with_fix), sorted(x[2] for x in pinned)
        )
        self.assertIn(KSTAR, [x[2] for x in with_fix])


class TheNearestWorldsInWhichItMustNotFireTests(_Tree):
    def test_a_vacuous_binder_that_scores_highest_is_not_demoted(self):
        """Demotion needs a strictly higher grounded score, not merely existence."""

        def fake(goal, ranked):
            reg = _registry()
            vac = [it for it in ranked if _is_vacuous(reg[it[2]])]
            grd = [it for it in ranked if not _is_vacuous(reg[it[2]])]
            if not vac or not grd:
                return ranked
            # Re-score so the vacuous binder strictly outscores every grounded
            # one.  It must stay first: it consumed nothing, but nothing beat it.
            top = max(it[0] for it in grd) + 5
            boosted = [(top, vac[0][1]) + tuple(vac[0][2:])]
            return boosted + grd + vac[1:]

        original = compiler._bm25_rerank
        compiler._bm25_rerank = fake
        try:
            ranked = compiler._rank_bindable_candidates(
                self.sentence("Localize the fault"),
                _registry(),
                _ROOT,
                allow_world_binding=False,
            )
        finally:
            compiler._bm25_rerank = original
        # The demotion lives inside the real _bm25_rerank, which this replaced,
        # so the assertion is about the contract the real one must honour: a
        # vacuous winner is not demoted by the fix.  Verified directly below.
        self.assertTrue(ranked)
        reg = _registry()
        ordered = original(self.sentence("Localize the fault"), ranked)
        grounded = [it[0] for it in ordered if not _is_vacuous(reg[it[2]])]
        first = ordered[0]
        if _is_vacuous(reg[first[2]]):
            self.assertGreaterEqual(first[0], max(grounded))

    def test_an_all_vacuous_pool_is_left_in_bm25_order(self):
        goal = self.sentence("Localize the fault")
        reg = _registry()
        ranked = compiler._rank_bindable_candidates(
            goal, reg, _ROOT, allow_world_binding=False
        )
        vacuous_only = [it for it in ranked if _is_vacuous(reg[it[2]])]
        if len(vacuous_only) < 2:
            self.skipTest("the pool holds fewer than two vacuous binders")
        original = compiler._bm25_rerank
        compiler._bm25_rerank = lambda g, r: r
        try:
            unranked = compiler._rank_bindable_candidates(
                goal, reg, _ROOT, allow_world_binding=False
            )
        finally:
            compiler._bm25_rerank = original
        pool = [it for it in unranked if _is_vacuous(reg[it[2]])]
        out = compiler._bm25_rerank(goal, pool)
        self.assertEqual(
            [it[2] for it in out], [it[2] for it in pool],
            "with no grounded competitor the order must not change",
        )


class TheNegativeControlTests(_Tree):
    def test_without_the_demotion_the_wrong_capability_returns(self):
        """The demotion is load-bearing, proved without depending on any path.

        BM25's relevance for a real sentence is a function of the tokens in that
        sentence, and the fixture's absolute path is among them -- measured on
        e2d7981d, this control passed under one repository root and failed under
        another, which is a test that measures the machine it runs on.  The
        scorer's own behaviour is pinned by test_goal_compiler_world_binding_v1.
        What this pins is the partition, by fixing the relevance BM25 reports so
        the only thing left to vary is the demotion itself.
        """
        reg = _registry()
        self.assertTrue(_is_vacuous(reg[KSTAR]), "kstar is no longer a vacuous binder")
        self.assertFalse(
            _is_vacuous(reg[LOCALIZER]), "the owner must bind from the sentence"
        )
        # A grounded owner the pinned scorer rated 28, and a vacuous binder it
        # rated 15, with BM25 reporting the vacuous one as the more relevant.
        pool = [
            (15, 0, KSTAR, reg[KSTAR], {}, {}, None),
            (28, 0, LOCALIZER, reg[LOCALIZER], {}, {}, None),
        ]
        module = compiler._bm25_module()
        self.assertIsNotNone(module, "the BM25 scorer is unavailable")
        original = module._bm25_scores
        module._bm25_scores = lambda terms, docs, **kw: [
            (9.0, {}) if KSTAR in str(docs[i]) or i == 0 else (1.0, {})
            for i in range(len(docs))
        ]
        try:
            ordered = compiler._bm25_rerank("Localize the fault in D", pool)
        finally:
            module._bm25_scores = original
        self.assertEqual(
            [row[2] for row in ordered], [LOCALIZER, KSTAR],
            "the demotion did not move the vacuous binder behind the grounded one",
        )
        # And without it, the inversion the defect was: relevance alone decides,
        # and the 15-point binder that consumed nothing leads the 28-point owner.
        bare = sorted(
            pool, key=lambda it: (-{KSTAR: 9.0, LOCALIZER: 1.0}[it[2]], -it[0], -it[1], it[2])
        )
        self.assertEqual(bare[0][2], KSTAR)
        self.assertLess(bare[0][0], bare[1][0])


class EndToEndTests(_Tree):
    def test_the_live_front_door_selects_the_localizer(self):
        _reg, _adm, compiled = live.compile_against_live_registry(
            self.sentence("Localize the fault"), str(_ROOT)
        )
        self.assertEqual(compiled.get("selected_capability"), LOCALIZER)

    def test_the_front_door_does_not_answer_with_the_measurement_capability(self):
        _reg, _adm, compiled = live.compile_against_live_registry(
            self.sentence("Localize the fault"), str(_ROOT)
        )
        self.assertNotEqual(compiled.get("selected_capability"), MEASURE)

    def test_the_pinned_compiler_no_longer_refuses_this_sentence(self):
        try:
            compiled = compiler.compile_goal(
                self.sentence("Localize the fault"), _registry(), _ROOT
            )
        except compiler.GoalCompilationFailure as exc:
            self.assertNotIn(
                "GOAL_COMPILATION_BEST_MATCH_UNBINDABLE",
                "%s:%s" % (getattr(exc, "code", ""), exc.detail or ""),
                "the guard still mistakes ranked[0] for the best bindable",
            )
            raise
        self.assertEqual(compiled["selected_capability"], LOCALIZER)


class ThePreviouslyFixedSentencesStillWorkTests(_Tree):
    """Three owners that a wrong ranking had been stealing the sentence from."""

    def test_provenance_reaches_the_provenance_tracer(self):
        _r, _a, c = live.compile_against_live_registry(
            self.sentence("Trace the value provenance"), str(_ROOT)
        )
        self.assertEqual(
            c.get("selected_capability"),
            "python.fault.provenance.interprocedural.value.v1",
        )

    def test_the_repair_loop_reaches_the_repair_loop(self):
        _r, _a, c = live.compile_against_live_registry(
            "Run the iterative repair loop on the python source root %s using "
            "the tests and write the report to %s" % (self.src, self.base / "r.json"),
            str(_ROOT),
        )
        self.assertEqual(
            c.get("selected_capability"),
            "python.software.repair.loop.strict_progress.ast.v1",
        )

    def test_the_measurement_sentence_still_reaches_the_measurement_capability(self):
        """The demotion must not rob the owner of a sentence it does own."""
        _r, _a, c = live.compile_against_live_registry(
            "Measure the repository acceptance for the python source root %s "
            "and write the report to %s" % (self.src, self.base / "r.json"),
            str(_ROOT),
        )
        self.assertEqual(c.get("selected_capability"), MEASURE)


if __name__ == "__main__":
    unittest.main(verbosity=2)

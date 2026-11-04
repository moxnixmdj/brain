"""The language must not be the list of forms I happened to anticipate.

This is the deepest defect found in twenty-eight rounds, and unlike the others it is not a bug in a
rule. It is the language itself being a fixed part of me.

`_solve_composed_table` carried a docstring warning against "a list of forms a human anticipated" and
then WAS exactly that -- four handwritten entries:

    cofactors = [x, 2x, x*x, const]

Consequences, measured 2026-11-04:

    T(x) + 2x   DISAMBIGUATED_AND_CRYSTALLIZED            <- in the list
    T(x) + 3x   HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED    <- not in the list
    T(x) + x^3  CONTRADICTORY_OR_OUT_OF_GRAMMAR

Nothing separated "2" from "3" except a Python literal I typed. A creature that can only compose with
the coefficients I thought of is not acquiring structure; it is indexing my foresight. Every round I
have run so far was quality assurance on that fixed language, which is why it kept producing a better
STATIC artifact rather than a creature.

The replacement is a rule, not a longer list:

    if   y = T_k(x) + s(x)  with T_k of period k
    then D_k(x) = y(x+k) - y(x) = s(x+k) - s(x)

so the k-th increment CANCELS the table and whatever survives is the co-factor. Constant D_k means
`s` is affine and its slope is D_k/k. Constant SECOND difference means `s` is quadratic and its
coefficient is that constant over 2k. Nothing is guessed; both are recovered by division.

These tests hold the line in the only way that matters: they demand values that were NEVER in the old
list, and they demand that the list not come back.
"""

from __future__ import annotations

import inspect
import pathlib
import tempfile
import unittest

from canonical.swe_kernel import meta_circular_organ_graph_v1 as M


def _solve(fn, seeds=range(1, 14)):
    with tempfile.TemporaryDirectory() as tmp:
        g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
        g.growth_enabled = True
        return g.synthesize_or_disambiguate_skill(
            [((x,), fn(x)) for x in seeds],
            task_signature="cofactor",
            oracle=lambda p, f=fn: f(p[0]),
        )


def _held_out_wrong(organ, fn, xs=range(40, 70)):
    if organ is None:
        return list(xs)
    return [x for x in xs if M._safe_eval_candidate(organ, (x,))[1] != fn(x)]


class CofactorsNeverInTheHandwrittenList(unittest.TestCase):
    """The direct measurement. Every one of these was IMPOSSIBLE before, for no reason but a literal."""

    def test_a_linear_cofactor_of_slope_three(self):
        fn = lambda x: (x % 3) + 3 * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_a_linear_cofactor_of_slope_five(self):
        fn = lambda x: (x % 3) + 5 * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_a_negative_cofactor_not_reachable_by_the_old_list(self):
        fn = lambda x: (x % 3) - 3 * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_a_large_slope(self):
        fn = lambda x: (x % 3) + 10 * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_the_same_rule_holds_at_a_different_period(self):
        """A recovered rule must not be period-specific. The old list was not, but neither was it a
        rule -- it was four entries that happened to work at the periods I tried."""
        fn = lambda x: (x % 7) + 7 * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])


class QuadraticCofactorsAreDetectedNotListed(unittest.TestCase):
    """`x*x` WAS in the old list. Removing it without deriving it silently cost the capability: `T+x^2`
    went from DISAMBIGUATED to HELD_OUT_REFUTED, a capability loss disguised as a cleanup. The entry
    was never the problem by itself -- the problem was that nothing could derive it.

    The detection is the second difference: for s = a*x*x, D_k(x) = 2akx + ak^2, so
    D_k(x+1) - D_k(x) = 2ak, constant, and a = that constant over 2k.
    """

    def test_the_original_quadratic_still_works(self):
        fn = lambda x: (x % 3) + x * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_a_quadratic_coefficient_that_was_never_listed(self):
        fn = lambda x: (x % 3) + 2 * x * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])

    def test_a_fractional_quadratic_coefficient(self):
        """No integer list could ever have contained this, which is the point."""
        fn = lambda x: (x % 3) + 0.5 * x * x
        result = _solve(fn)
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn), [])


class TheHandwrittenListMustNotComeBack(unittest.TestCase):
    """A source-level guard, because this is the failure mode that keeps recurring: the comment says
    one thing and the code below it does another. It is not enough for the tests above to pass -- a
    future edit could re-add a literal list and still pass every behavioural test while silently
    re-fixing the language."""

    def test_the_cofactor_table_is_not_a_literal_list_of_forms(self):
        source = inspect.getsource(M._solve_composed_table)
        for banned in ('("2x"', '"x2"', 'lambda x: 2 * x', 'lambda x: x * x'):
            self.assertNotIn(
                banned, source,
                f"a handwritten co-factor {banned!r} is back in the closure rule; the coefficient "
                "must be RECOVERED by differencing, not typed",
            )

    def test_the_recovery_is_by_differencing(self):
        source = inspect.getsource(M._solve_composed_table)
        self.assertIn("_solve_affine_cofactor", source)
        self.assertIn("_detected_cofactors", source)


class TheRegressionThatTaughtTheRule(unittest.TestCase):
    """Recorded because it is the honest version of what happened: my first rewrite DROPPED a
    capability while claiming to generalise one. `T+x^2` worked before and refused after, and I would
    not have noticed without measuring the old cases alongside the new ones."""

    def test_every_previously_working_form_still_works(self):
        cases = {
            "T+x": lambda x: (x % 3) + x,
            "T+2x": lambda x: (x % 3) + 2 * x,
            "T-2x": lambda x: (x % 3) - 2 * x,
            "T*x": lambda x: (x % 3) * x,
            "T+x2": lambda x: (x % 3) + x * x,
            "T+7": lambda x: (x % 3) + 7,
        }
        for name, fn in cases.items():
            with self.subTest(name=name):
                result = _solve(fn)
                self.assertTrue(result["ok"], f"{name}: {result.get('status')}")
                self.assertEqual(_held_out_wrong(result.get("organ"), fn), [], name)


if __name__ == "__main__":
    unittest.main()


class ThePeriodCapIsALimitOfEvidenceNotOfMe(unittest.TestCase):
    """`range(2, 13)` made period 13 unreachable for a reason unrelated to the data: measured
    2026-11-04, periods 12, 13 and 17 all returned HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED while
    period 3 crystallised. A block of period k has k residues, so k cannot exceed the number of
    distinct inputs observed -- that is the only bound the evidence supports, and the existing residue
    check already refuses below it. The constant was a limit of my imagination standing in for a limit
    of the evidence, which is the same error as the cofactor list one level up."""

    def test_period_thirteen_is_reachable(self):
        fn = lambda x: (x % 13) + x
        result = _solve(fn, seeds=range(1, 29))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn, xs=range(60, 90)), [])

    def test_period_seventeen_is_reachable(self):
        fn = lambda x: (x % 17) + x
        result = _solve(fn, seeds=range(1, 37))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_held_out_wrong(result.get("organ"), fn, xs=range(60, 90)), [])

    def test_the_cap_is_not_a_literal_again(self):
        """Check EXECUTABLE lines only. My first version of this guard searched the whole source and
        failed on its own explanatory comment -- a guard that cannot tell code from commentary would
        have forced me to delete the record of the defect to satisfy it."""
        code = [
            line for line in inspect.getsource(M._solve_composed_table).splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertNotIn("range(2, 13)", "\n".join(code), "the hardcoded period cap came back")
        self.assertIn("max_period", "\n".join(code))

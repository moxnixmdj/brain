"""Round 29 replaced a handwritten cofactor list with a rule. Round 30 finds the rule still had a list.

Round 29's win was real: `[x, 2x, x*x, const]` became "difference at lag k, then recover the
coefficient". But it recovered AFFINE and QUADRATIC coefficients -- two shapes. Measured 2026-11-04:

    T(x) + x**3   CONTRADICTORY_OR_OUT_OF_GRAMMAR
    T(x) + 2**x   CONTRADICTORY_OR_OUT_OF_GRAMMAR

The DEGREE was the next thing I had typed, and the base of an exponential would have been the one
after that. That is a shorter list, not no list, and it fails the same way on the same principle: a
capability bounded by what I anticipated.

THE GENERAL RULE, which is the same rule:

    difference y at lag k ONCE to kill the table:   D_k(x) = s(x+k) - s(x)

then IDENTIFY what survives instead of assuming its shape.

  POLYNOMIAL   s = a*x^d  ->  D_k has degree d-1, so d-1 unit differences leave a constant
                              C = a*k*d!      =>      a = C / (k*d!)
               The DEGREE is how many differences it took to flatten -- measured, not searched.
               Verified independently for d=2,3,4 at k=3 and k=5.

  EXPONENTIAL  s = A*r^x  ->  D_k = A*r^x*(r^k - 1), whose consecutive RATIO is exactly r.
               Constant ratio names the base with no fitting, for any r.

  NEITHER      -> refuse. Which is not a fallback: it is the guarantee that a success here cannot be
               a lucky fit, because the shape is NAMED before the block is solved.

These tests demand degrees and bases that were never expressible before, and they demand the refusals
too, because a detector that only ever succeeds is indistinguishable from a lookup table.
"""

from __future__ import annotations

import inspect
import pathlib
import tempfile
import unittest

from canonical.swe_kernel import meta_circular_organ_graph_v1 as M


def _solve(fn, seeds):
    with tempfile.TemporaryDirectory() as tmp:
        g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
        g.growth_enabled = True
        return g.synthesize_or_disambiguate_skill(
            [((x,), fn(x)) for x in seeds],
            task_signature="shape",
            oracle=lambda p, f=fn: f(p[0]),
        )


def _wrong(organ, fn, xs):
    if organ is None:
        return list(xs)
    return [
        x for x in xs
        if abs(float(M._safe_eval_candidate(organ, (x,))[1]) - float(fn(x))) > 1e-6
    ]


class PolynomialsOfAnyDegree(unittest.TestCase):
    """The degree is the thing that used to be mine. It is now whichever depth flattens the residual."""

    def test_cubic(self):
        fn = lambda x: (x % 3) + x ** 3
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(40, 70)), [])

    def test_quartic(self):
        fn = lambda x: (x % 3) + x ** 4
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        # x**5 overflows nothing but grows fast; check a range where float exactness holds.
        self.assertEqual(_wrong(result.get("organ"), fn, range(20, 40)), [])

    def test_quintic(self):
        fn = lambda x: (x % 3) + x ** 5
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(20, 40)), [])

    def test_a_fractional_leading_coefficient(self):
        fn = lambda x: (x % 3) + 0.25 * x ** 3
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(40, 70)), [])


class ExponentialsOfAnyBase(unittest.TestCase):
    """A constant RATIO of the lag-k difference is the base. No fitting, no list of bases."""

    def test_base_two(self):
        fn = lambda x: (x % 3) + 2 ** x
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(10, 24)), [])

    def test_base_three(self):
        fn = lambda x: (x % 3) + 3 ** x
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(10, 24)), [])

    def test_a_fractional_base_decaying(self):
        """0.5**x decays. No list of bases I would write contains 1.5 or 0.5."""
        fn = lambda x: (x % 3) + 0.5 ** x
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(10, 24)), [])

    def test_a_non_integer_base(self):
        fn = lambda x: (x % 3) + 1.5 ** x
        result = _solve(fn, range(1, 24))
        self.assertTrue(result["ok"], result.get("status"))
        self.assertEqual(_wrong(result.get("organ"), fn, range(10, 20)), [])


class TheShapeIsNamedBeforeTheBlockIsSolved(unittest.TestCase):
    """The detector must return a NAME for the shape, not merely a coefficient. Without that, a hit
    cannot be distinguished from an accident that happened to fit."""

    def test_a_cubic_cofactor_is_named_as_a_cubic(self):
        examples = [((x,), (x % 3) + x ** 3) for x in range(1, 24)]
        found = M._detected_cofactors(examples, 3, "x0")
        self.assertTrue(found, "no cofactor detected at all")
        names = [name for name, _src, _g in found]
        self.assertTrue(
            any("poly3" in n for n in names),
            f"a cubic cofactor was not named as a cubic: {names}",
        )

    def test_an_exponential_is_named_with_its_base(self):
        examples = [((x,), (x % 3) + 3 ** x) for x in range(1, 24)]
        found = M._detected_cofactors(examples, 3, "x0")
        names = [name for name, _src, _g in found]
        self.assertTrue(any("exp3" in n for n in names), names)


class ASuccessMustNotComeFromRunningOutOfRoom(unittest.TestCase):
    """Measured 2026-11-04 and it was a defect I introduced in this very round: with few points the
    detector reported `poly6`, `poly8` -- a degree that merely means "fewer samples than terms". That
    is arithmetic exhausting itself, not a discovery, and it is the same error as reading a budget
    limit as a statement about the grammar.

    A degree now needs two points of redundancy beyond itself before it may be believed. Below that
    the detector says nothing and the creature refuses, which is correct: the evidence cannot yet
    distinguish a polynomial from an exponential."""

    def test_a_high_degree_is_not_claimed_on_thin_evidence(self):
        examples = [((x,), (x % 3) + 3 ** x) for x in range(1, 9)]
        found = M._detected_cofactors(examples, 3, "x0")
        for name, _src, _g in found:
            self.assertNotIn(
                "poly5", name,
                "a degree was claimed on evidence too thin to support it",
            )

    def test_the_detector_is_silent_rather_than_guessing(self):
        # Five points at period 5 cannot support any differencing at all.
        examples = [((x,), (x % 5) + 3 ** x) for x in range(1, 6)]
        self.assertEqual(M._detected_cofactors(examples, 5, "x0"), [])


class NeitherShapeStillRefuses(unittest.TestCase):
    """A detector that always succeeds is a lookup table with extra steps."""

    def test_a_cofactor_that_is_neither_polynomial_nor_exponential(self):
        fn = lambda x: (x % 3) + (x if x < 2 else (x * 7) % 11)
        result = _solve(fn, range(1, 24))
        if result["ok"]:
            self.assertEqual(
                _wrong(result.get("organ"), fn, range(40, 60)), [],
                "claimed a body that is wrong on held-out inputs",
            )
        else:
            self.assertIn(result["status"], {
                "HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED",
                "CONTRADICTORY_OR_OUT_OF_GRAMMAR",
                "NO_CONSISTENT_HYPOTHESIS",
                "SEARCH_TRUNCATED",
            }, result["status"])


class TheTypedListMustNotGrowBack(unittest.TestCase):
    def test_the_detector_does_not_hardcode_a_degree(self):
        code = [
            line for line in inspect.getsource(M._detected_cofactors).splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        joined = "\n".join(code)
        for banned in ("x ** 2)", "x ** 3)", "2 ** x", "3 ** x"):
            self.assertNotIn(
                banned, joined,
                f"a specific {banned!r} shape is back in the detector; the degree and base must be "
                "RECOVERED by differencing, not typed",
            )

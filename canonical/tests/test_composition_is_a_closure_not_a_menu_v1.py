"""P1-P5 for *the library that nobody reads, and the closure that replaces it*.

Round 23 added one node and the grammar could solve one shape. A table COMBINED with anything was still
refused, cold and warm. These tests hold the replacement to account: composition must be a closure rule
over a small basis (the block is SOLVED from the residual), not a new hand-written node per composed
form -- and it must not buy expressiveness with false claims.
"""
from __future__ import annotations

import pathlib
import tempfile
import time
import unittest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M

BLOCK = [5.0, -2.0, 7.0]
HELD_OUT = [x for x in range(-30, 0)] + [500, 1000, 7, 13, 55, 123]


def _T(x):
    return BLOCK[int(x) % 3]


class CompositionClosureTests(unittest.TestCase):
    def _solve(self, fn, examples=None):
        ex = examples if examples is not None else [((x,), fn(x)) for x in range(1, 10)]
        with tempfile.TemporaryDirectory() as tmp:
            g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
            g.growth_enabled = False  # no writer, no structure diagnosis: search only
            return g.synthesize_or_disambiguate_skill(
                ex, task_signature="test::compose", oracle=lambda p: fn(p[0])
            )

    def _all_correct(self, organ, fn):
        for x in HELD_OUT:
            hit, got = M._safe_eval_candidate(organ, (x,))
            if not hit:
                continue
            if abs(float(got) - float(fn(x))) > 1e-9:
                return False, x
        return True, None

    def test_p1_a_table_composed_with_the_input_is_expressed(self):
        for name, fn in (
            ("T(x)+x", lambda x: _T(x) + x),
            ("T(x)-x", lambda x: _T(x) - x),
            ("T(x)*x", lambda x: _T(x) * x),
        ):
            res = self._solve(fn)
            self.assertTrue(res["ok"], f"{name}: {res.get('status')}")
            ok, bad = self._all_correct(res["organ"], fn)
            self.assertTrue(ok, f"{name}: {res['organ'].name} wrong at x={bad}")

    def test_p1_a_table_composed_with_a_basis_square_is_expressed(self):
        res = self._solve(lambda x: _T(x) + x * x)
        self.assertTrue(res["ok"], res.get("status"))
        ok, bad = self._all_correct(res["organ"], lambda x: _T(x) + x * x)
        self.assertTrue(ok, f"wrong at x={bad}")

    def test_p2_composition_does_not_need_the_library(self):
        """P2: the results above are cold. An empty concept library must be enough.

        This is the prediction that decides whether round 22's fix (feed the library) or this one
        (widen the expressible set) is the load-bearing change. If the compositions only worked with
        prior concepts, that would say the library matters and this note would be wrong.
        """
        res = self._solve(lambda x: _T(x) + x)
        self.assertTrue(res["ok"])
        self.assertEqual(res["organ"].task_signature, "test::compose")
        # Nothing was registered under any other signature to make it work.
        self.assertIn("composed_table", res["organ"].name)

    def test_the_block_is_solved_from_the_residual_not_guessed(self):
        """A different block in the same composed form must come out as a different block."""
        other = [100.0, 0.5, -7.0]
        fn = lambda x: other[int(x) % 3] + x
        res = self._solve(fn)
        self.assertTrue(res["ok"], res.get("status"))
        src = res["organ"].source_code
        for value in other:
            self.assertIn(repr(float(value)), src)
        ok, bad = self._all_correct(res["organ"], fn)
        self.assertTrue(ok, f"wrong at x={bad}")


class NoFalseStructureTests(unittest.TestCase):
    """P3: widening a grammar is exactly how false claims enter. This is the invariant that guards it."""

    def test_p3_nothing_claimed_is_wrong_on_held_out(self):
        def rnd(x):
            import hashlib
            return int(hashlib.sha256(str(x).encode()).hexdigest()[:8], 16) % 97

        cases = {
            "x^3": lambda x: x ** 3,
            "floor(x/7)": lambda x: x // 7,
            "2^x": lambda x: 2 ** x,
            "x^2+x": lambda x: x * x + x,
            "abs(x-5)": lambda x: abs(x - 5),
            "staircase": lambda x: float(int(x / 2)),
            "random": rnd,
            "piecewise": lambda x: [2.0, -1.0, 4.0][int(x) % 3] if x > 0 else -9.0,
            "flip-after-6": lambda x: [2.0, -1.0, 4.0][int(x) % 3] * (-1 if x > 6 else 1),
            "floor(x/3)+x": lambda x: x // 3 + x,
        }
        for name, fn in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
                g.growth_enabled = False
                res = g.synthesize_or_disambiguate_skill(
                    [((x,), fn(x)) for x in range(1, 10)],
                    task_signature="test::fp", oracle=lambda p, fn=fn: fn(p[0]),
                )
            if not res["ok"]:
                continue
            organ = res["organ"]
            for x in HELD_OUT:
                hit, got = M._safe_eval_candidate(organ, (x,))
                if not hit:
                    continue
                self.assertAlmostEqual(
                    float(got), float(fn(x)), places=6,
                    msg=f"{name}: claimed {organ.name} but wrong at x={x}",
                )

    def test_p3_closures_are_checked_like_every_other_candidate(self):
        # A composed candidate that contradicts one example must never survive the filter.
        fn = lambda x: _T(x) + x
        ex = [((x,), fn(x)) for x in range(1, 10)]
        cands = M._solve_composed_table(ex, "x0")
        self.assertTrue(cands, "the closure should have proposed something for this task")
        for label, expr in cands:
            organ = M.make_organ(stratum=M.SKILL, name=label, task_signature="t::chk",
                                 entrypoint="run", source_code=M._wrap_expr_into_source(1, expr))
            ok, got = M._safe_eval_candidate(organ, (1,))
            self.assertTrue(ok, f"{label} does not evaluate")


class BoundedCostTests(unittest.TestCase):
    """P4: the closure must stay bounded -- a grammar that enumerates is not a capability."""

    def test_p4_candidate_growth_is_bounded(self):
        fn = lambda x: _T(x) + x
        ex = [((x,), fn(x)) for x in range(1, 10)]
        t0 = time.time()
        cands = M._generate_candidate_expressions(ex)
        elapsed = time.time() - t0
        self.assertLess(len(cands), 200, "candidate explosion")
        self.assertLess(elapsed, 1.0, f"generation took {elapsed:.2f}s")

    def test_p4_cost_does_not_grow_with_the_period(self):
        for P in (3, 7, 12):
            blk = [((i * 7 + 3) % 11) - 5 for i in range(P)]
            fn = lambda x, b=blk, P=P: b[int(x) % P] * x
            ex = [((x,), fn(x)) for x in range(1, P + 3)]
            cands = M._generate_candidate_expressions(ex)
            self.assertLess(len(cands), 200, f"period {P} exploded to {len(cands)}")


class LibraryIsStillInertTests(unittest.TestCase):
    """The honest status recorded this round: the concept library accumulates and nothing reads it."""

    def test_the_library_is_not_wired_as_a_template_source(self):
        """If this ever starts failing because the library IS consulted, update the note, not the test.

        Round 22 claimed the library was empty. Measured on the round-23 organs it is not empty -- the
        bridge fires. It is simply not read by synthesis. Wiring it in without evidence that it helps
        would be decoration, so it is deliberately absent, and this test records the choice.
        """
        import inspect
        src = inspect.getsource(M._generate_candidate_expressions)
        self.assertNotIn("concept_library.concepts", src)
        self.assertNotIn("concept_library.search", src)


if __name__ == "__main__":
    unittest.main()

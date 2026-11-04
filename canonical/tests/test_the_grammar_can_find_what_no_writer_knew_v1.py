"""P1-P5 for *the grammar can only express what a writer already knows*.

The measurement that produced this round: with growth disabled, the general grammar returned
NO_CONSISTENT_HYPOTHESIS for a period-3 block. The program existed only because a writer emits it.
These tests hold the replacement to account: the table must be FOUND by search, with no writer, and the
things that must still refuse must still refuse.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M

HELD_OUT = [x for x in range(-90, 0)] + [x for x in range(200, 260)]


def _block(P, seed=0):
    return [((i * 7 + 3 + seed) % 11) - 5 for i in range(P)]


def _periodic(P, seed=0):
    blk = _block(P, seed)
    return lambda x: blk[int(x) % P], blk


class SearchedNotWrittenTests(unittest.TestCase):
    """P1/P2: the general grammar reaches the shape with the writers switched OFF."""

    def _search(self, fn, examples, enabled_growth=False):
        with tempfile.TemporaryDirectory() as tmp:
            g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
            g.growth_enabled = enabled_growth
            return g.synthesize_or_disambiguate_skill(
                examples, task_signature="test::grammar-only", oracle=lambda p: fn(p[0])
            )

    def _accuracy(self, organ, fn):
        if organ is None:
            return 0, len(HELD_OUT)
        ok = 0
        for x in HELD_OUT:
            hit, got = M._safe_eval_candidate(organ, (x,))
            if hit and abs(float(got) - float(fn(x))) < 1e-9:
                ok += 1
        return ok, len(HELD_OUT)

    def test_period_3_is_found_by_search_with_no_writer(self):
        f, blk = _periodic(3)
        res = self._search(f, [((x,), f(x)) for x in (1, 2, 3)])
        self.assertTrue(res["ok"], res.get("status"))
        ok, total = self._accuracy(res["organ"], f)
        self.assertEqual(ok, total)

    def test_every_period_is_found_by_the_same_rule(self):
        # No per-period code, no writer: one parametric node covers all of them.
        for P in (2, 3, 4, 5, 7):
            f, _ = _periodic(P)
            res = self._search(f, [((x,), f(x)) for x in range(1, P + 2)])
            self.assertTrue(res["ok"], f"period {P}: {res.get('status')}")
            ok, total = self._accuracy(res["organ"], f)
            self.assertEqual(ok, total, f"period {P} held-out {ok}/{total}")

    def test_three_examples_cannot_identify_a_longer_period(self):
        # This is a property of the world, not a defect: with three consecutive samples a period-4
        # block is indistinguishable from a period-3 one, because a 4th entry was never observed.
        # The creature must not claim otherwise. It may answer (the 3-period reading fits every
        # observation available) but it must NOT be credited with solving period 4.
        f4, _ = _periodic(4)
        res = self._search(f4, [((x,), f4(x)) for x in (1, 2, 3)])
        if res["ok"]:
            self.assertNotIn("parametric_table_4", res["organ"].name)

    def test_search_is_cheaper_than_the_writer_it_replaces(self):
        f, _ = _periodic(3)
        res = self._search(f, [((x,), f(x)) for x in (1, 2, 3)])
        # The writer path cost 14 questions for this structure; search must beat it.
        self.assertLess(res.get("oracle_queries_used", 99), 14)


class StillRefusesTests(unittest.TestCase):
    """P4: widening the grammar must not start claiming things it cannot do."""

    def test_non_periodic_functions_still_refuse(self):
        # Round 24 moved `x*x` out of this list, and that is not a weakened test -- it is a corrected
        # one. `x*x` is genuinely expressible as a solved table T_2(x) = [0,0] plus x*x, and the organ
        # is exact at 10**6. Asserting a refusal there would have been asserting that the creature is
        # worse than it is. What must still refuse is anything the basis cannot compose: a genuine
        # period-2 table cannot reproduce x**3 or floor(x/7).
        for name, fn in (("x^3", lambda x: x ** 3), ("floor(x/7)", lambda x: x // 7),
                         ("2^x", lambda x: 2 ** x)):
            with tempfile.TemporaryDirectory() as tmp:
                g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
                g.growth_enabled = False
                res = g.synthesize_or_disambiguate_skill(
                    [((x,), fn(x)) for x in range(1, 6)],
                    task_signature="test::refuse", oracle=lambda p, fn=fn: fn(p[0]),
                )
                self.assertFalse(res["ok"], f"{name} must not be claimed: {res.get('status')}")

    def test_a_claim_is_never_wrong_on_held_out(self):
        """Whatever it claims must be exact, whatever the corpus. This is the invariant that matters.

        Checking names is a proxy; checking the answers is the property. Anything claimed and then wrong
        on unseen inputs is a false positive, and this catches it without me guessing which functions
        are 'supposed' to be refused.
        """
        cases = {
            "x*x": lambda x: x * x, "x^3": lambda x: x ** 3, "floor(x/7)": lambda x: x // 7,
            "2^x": lambda x: 2 ** x, "x^2+x": lambda x: x * x + x,
            "abs(x-5)": lambda x: abs(x - 5), "staircase": lambda x: float(int(x / 2)),
        }
        held = [x for x in range(-20, 0)] + [x for x in (500, 1000, 12345)]
        for name, fn in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
                g.growth_enabled = False
                res = g.synthesize_or_disambiguate_skill(
                    [((x,), fn(x)) for x in range(1, 10)],
                    task_signature="test::heldout", oracle=lambda p, fn=fn: fn(p[0]),
                )
                if not res["ok"]:
                    continue
                organ = res["organ"]
                for x in held:
                    hit, got = M._safe_eval_candidate(organ, (x,))
                    if not hit:
                        continue  # an undefined point is not a wrong claim
                    self.assertAlmostEqual(
                        float(got), float(fn(x)), places=6,
                        msg=f"{name}: claimed {organ.name} but wrong at x={x}",
                    )

    def test_the_node_declines_when_evidence_is_thin(self):
        self.assertIsNone(M._solve_parametric_table([((1,), 5.0)]))
        self.assertIsNone(M._solve_parametric_table([]))

    def test_the_node_never_proposes_a_table_its_own_evidence_contradicts(self):
        # My first version of this test asserted `None` for these three pairs -- and failed, because
        # for k=2 the inputs 1, 4 and 7 fall in DIFFERENT residues, so a k=2 table is legitimately
        # consistent with them. The assertion was my assumption, not a property. The property that
        # actually holds is the universal one: whatever period is proposed, every example must agree
        # with the proposed block. A table that contradicts its own evidence would be a fabricated
        # explanation, which is the one thing this must never do.
        examples = [((1,), 5.0), ((4,), 9.0), ((7,), 5.0)]
        cand = M._solve_parametric_table(examples)
        if cand is None:
            return
        name, expr = cand
        k = int(name.rsplit("_", 1)[1])
        organ = M.make_organ(stratum=M.SKILL, name="probe", task_signature="t::c",
                             entrypoint="run", source_code=M._wrap_expr_into_source(1, expr))
        for x_in, expected in examples:
            ok, got = M._safe_eval_candidate(organ, x_in)
            self.assertTrue(ok, f"proposed table fails to evaluate at {x_in}")
            self.assertAlmostEqual(float(got), float(expected), places=9,
                                   msg=f"proposed period-{k} table contradicts evidence at {x_in}")


class WitnessedNotRememberedTests(unittest.TestCase):
    """P5: what the search returns must be a hypothesis with the world's block in it, not a memory."""

    def test_the_emitted_body_contains_the_observed_block(self):
        f, blk = _periodic(3)
        with tempfile.TemporaryDirectory() as tmp:
            g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
            res = g.synthesize_or_disambiguate_skill(
                [((x,), f(x)) for x in (1, 2, 3)],
                task_signature="test::body", oracle=lambda p: f(p[0]),
            )
        src = res["organ"].source_code
        for value in blk:
            self.assertIn(repr(float(value)), src)

    def test_two_different_blocks_give_two_different_programs(self):
        a, _ = _periodic(3, seed=0)
        b, _ = _periodic(3, seed=1)
        srcs = []
        for fn, sig in ((a, "test::a"), (b, "test::b")):
            with tempfile.TemporaryDirectory() as tmp:
                g = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json")
                res = g.synthesize_or_disambiguate_skill(
                    [((x,), fn(x)) for x in (1, 2, 3)],
                    task_signature=sig, oracle=lambda p, fn=fn: fn(p[0]),
                )
                srcs.append(res["organ"].source_code)
        self.assertNotEqual(srcs[0], srcs[1])


if __name__ == "__main__":
    unittest.main()

"""Plan v5 move 2: the OE/stochastic ensemble is an option inside the planner.

Two layers of proof:

1. Unit: `synthesize_body_from_examples` recovers a branch-using function the
   observational synthesizer cannot express at max_weight 4..8 (ten swept
   configs, 2026-11-25), verified against every example it is given.
2. End-to-end: a workspace whose test asserts a conditional function and whose
   implementation returns a constant is driven through the REAL socket —
   `model_v1.bind(SOVEREIGN_ZERO_LLM_MODEL_SPEC)` + `solve_v1.solve` — and
   must come back DONE with the test green. The patch can only exist if the
   planner's H2 affordance used the ensemble fallback: the observational
   grammar (no if/else at that budget) misses, and the loop's own verifier
   rejects anything that does not pass the test file.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class EnsembleFallbackUnit(unittest.TestCase):
    def test_fallback_finds_branch_program_and_generalizes(self) -> None:
        from canonical.runtime.stochastic_synthesizer_v1 import (
            synthesize_body_from_examples,
        )

        fn = lambda x: x * 3 if x >= 0 else -x * 3  # noqa: E731
        ex = [((x,), fn(x)) for x in (5, 2, 1, -1, -3, 0)]
        body = synthesize_body_from_examples(["x"], ex)
        self.assertIsNotNone(body, "ensemble must recover the conditional")
        ns: dict = {}
        exec("def g(x):\n    " + str(body), ns)  # noqa: S102
        for h in range(-6, 8):  # generalizes to points never shown
            self.assertEqual(ns["g"](h), fn(h), f"held-out x={h}")

    def test_fallback_is_fail_closed_on_unrealizable_or_malformed(self) -> None:
        from canonical.runtime.stochastic_synthesizer_v1 import (
            synthesize_body_from_examples,
        )

        self.assertIsNone(synthesize_body_from_examples(["x"], []))
        self.assertIsNone(synthesize_body_from_examples(["x", "y"], [((1,), 2)]))
        # contradictory examples: no expression passes -> None, never a guess
        self.assertIsNone(
            synthesize_body_from_examples(["x"], [((1,), 2), ((1,), 3)])
        )


class EnsembleAffordanceEndToEnd(unittest.TestCase):
    def test_planner_patches_conditional_function_via_socket(self) -> None:
        from canonical.runtime import brain_unified_model_v1 as bum
        from canonical.runtime import model_v1, solve_v1

        bound_fn = model_v1.bind(bum.SOVEREIGN_ZERO_LLM_MODEL_SPEC)
        self.assertTrue(model_v1.conformance(bound_fn)["ok"])

        with tempfile.TemporaryDirectory(prefix="plan-v5-ens-") as td:
            ws = pathlib.Path(td)
            (ws / "impl.py").write_text("def f(x):\n    return 0\n", encoding="utf-8")
            (ws / "test_f.py").write_text(
                "import unittest\n"
                "from impl import f\n"
                "class T(unittest.TestCase):\n"
                "    def test_pts(self):\n"
                "        self.assertEqual(f(5), 15)\n"
                "        self.assertEqual(f(2), 6)\n"
                "        self.assertEqual(f(1), 3)\n"
                "        self.assertEqual(f(-1), 3)\n"
                "        self.assertEqual(f(-3), 9)\n"
                "        self.assertEqual(f(0), 0)\n",
                encoding="utf-8",
            )
            import time

            t0 = time.perf_counter()
            out = solve_v1.solve(
                "fix f in impl.py so test_f.py passes", str(ws),
                model=bound_fn, learn=False, steps=8,
            )
            ms = (time.perf_counter() - t0) * 1000
            self.assertEqual(out["verdict"], "DONE", out)
            src = (ws / "impl.py").read_text(encoding="utf-8")
            ns: dict = {}
            exec(compile(src, str(ws / "impl.py"), "exec"), ns)  # noqa: S102
            for h in (-9, -2, -1, 0, 1, 4, 11):
                self.assertEqual(ns["f"](h), abs(h) * 3, f"held-out x={h}")
            print(f"\n  end-to-end patch+verify in {ms:.0f} ms, zero LLM tokens")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Tests for the Unified Multi-Language OE-SyGuS + EUSolver Synthesizer v1.

Core synthesis only (no universal_epistemic_kernel dependency): the
separating-predicate and value-expression synthesizers, plus anti-overfit
guarantees. Promoted from branch arena/b81b2217-brain (HARD-51) @ 4fc832f2;
the UEK/`open_model` integration tests from that branch are not included
because universal_epistemic_kernel_v1 is branch-only.
"""
from __future__ import annotations

import unittest

from canonical.runtime import oe_sygus_synthesizer_v1 as OESYGUS


class TestOESyGuSSynthesizerV1(unittest.TestCase):
    def test_01_eusolver_separating_predicates_across_python_js_c(self) -> None:
        # Compound failure set: negative + non-integer float + NaN + Infinity
        # vs valid non-negative ints. The synthesizer must find the semantic
        # predicate (non-integer OR negative), not memorize the literals.
        failing = [{"size": -3}, {"size": 0.5}, {"size": "__NaN__"}, {"size": "__Inf__"}]
        passing = [{"size": 0}, {"size": 1}, {"size": 10}, {"size": 21}]

        for lang, expected_tokens in [
            ("js", ("Number.isInteger(size)", "size < 0", "||")),
            ("python", ("isinstance(size, int)", "size < 0", "or")),
            ("c", ("floor(size)", "size < 0", "||")),
        ]:
            preds = OESYGUS.synthesize_separating_predicates(
                failing, passing, lang=lang, max_results=4
            )
            self.assertTrue(preds, f"No predicate synthesized for {lang}")
            top = preds[0]["code"]
            for tok in expected_tokens:
                self.assertIn(tok, top, f"Expected {tok!r} in {top!r} ({lang})")
            # Must NOT overfit to exact literal 0.5 or -3
            self.assertNotIn("0.5", top)
            self.assertNotIn("-3", top)

    def test_02_synthesized_predicate_actually_separates(self) -> None:
        # The synthesized predicate must be TRUE on every failing input and
        # FALSE on every passing input (it is a separator, not a guess).
        failing = [{"x": -1}, {"x": -7}, {"x": 0.5}]
        passing = [{"x": 0}, {"x": 3}, {"x": 42}]
        preds = OESYGUS.synthesize_separating_predicates(
            failing, passing, lang="python", max_results=4
        )
        self.assertTrue(preds)
        code = preds[0]["code"]
        for env in failing:
            self.assertTrue(eval(code, {}, dict(env)), f"should be True on {env}: {code}")
        for env in passing:
            self.assertFalse(eval(code, {}, dict(env)), f"should be False on {env}: {code}")

    def test_03_value_expression_synthesis(self) -> None:
        # Synthesize a value expression from I/O examples: y = x + 1 style.
        examples = [
            ({"x": 0}, 1),
            ({"x": 1}, 2),
            ({"x": 5}, 6),
            ({"x": 10}, 11),
        ]
        exprs = OESYGUS.synthesize_value_expressions(
            examples, lang="python", max_results=4
        )
        self.assertTrue(exprs, "No value expression synthesized")
        # At least one synthesized expression must reproduce the examples.
        ok = False
        for e in exprs:
            code = e["code"] if isinstance(e, dict) else str(e)
            try:
                if all(eval(code, {}, dict(env)) == out for env, out in examples):
                    ok = True
                    break
            except Exception:
                continue
        self.assertTrue(ok, f"No synthesized expression reproduces examples: {exprs!r}")


if __name__ == "__main__":
    unittest.main()

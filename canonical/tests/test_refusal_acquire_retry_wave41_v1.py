"""Wave 41 verification suite: `REFUSAL_ACQUIRE_RETRY_V1` — abstain, acquire, retry, remember.

Pure stdlib `unittest.TestCase`.

Wave 40's bench measured the gap this wave closes. The Meaning-IR ratchet could apply a learned
rule only verbatim, inside the context it was learned in (`return <a> <= <b>`), so a target line
with different identifiers, no `return`, or the comparison written the other way round declined —
`REFUSED__CROSS_LANGUAGE_TRANSFER_NOT_PRODUCED` — and nothing was done with the name. These tests
check that the name is now acted on, and that acting on it cannot overstate:

  0. the rule's *meaning* is a single operator swap, and anything else is refused by name
  1. the two application procedures are total over comparison expressions and blind to `->`/`<<`/`=>`
  2. acquire → verify → retry succeeds in one step; a second refusal of the same kind is reused
  3. the inverted-operand procedure is what converts the harder instance (two steps, not one)
  4. nothing is admitted without the caller's verifier; no verifier means a named refusal
  5. the ratchet reports `PASS__ACQUIRED_AFTER_REFUSAL` and grows its store
  6. an unreachable instance still refuses, and the verdict says why
  7. the acquisition never moves or renames an operand: the edit is in the file's own alphabet
  8. the bench's seventh category is the capability's own measurement, and removing the
     acquisition makes it fail (the capability is the cause, not the fixture)
  9. the capability is reachable from the federation and from `UnifiedModel`
"""
from __future__ import annotations

import unittest
from unittest import mock

from canonical.evaluation import frontier_bench_v1 as bench
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.unified_hidden_capability_federation_v1 import run_federated_engine
from canonical.swe_kernel import refusal_acquire_retry_v1 as rar
from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import UnifiedFivePillarKernel

PY_LE_RULE = {
    "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                       ["op", "<="], ["ws", " "], ["hole_id", "?id1"]],
    "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                           ["op", "<"], ["ws", " "], ["hole_id", "?id1"]],
}


def _kernel() -> UnifiedFivePillarKernel:
    return UnifiedFivePillarKernel()


class TestOperatorRewrite(unittest.TestCase):
    def test_00_the_meaning_is_one_operator_swap_or_nothing(self) -> None:
        rewrite = rar.OperatorRewrite.from_tokens(
            PY_LE_RULE["pattern_tokens"], PY_LE_RULE["replacement_tokens"]
        )
        self.assertEqual((rewrite.before, rewrite.after), ("<=", "<"))
        self.assertEqual(rewrite.key, ("OPERATOR", "<=", "<"))

        # An identifier change is a different edit and must not be reconstructed as an operator swap.
        moved = [list(t) for t in PY_LE_RULE["replacement_tokens"]]
        moved[2] = ["hole_id", "?id9"]
        self.assertIsNone(rar.OperatorRewrite.from_tokens(PY_LE_RULE["pattern_tokens"], moved))
        # Two operator changes are two edits.
        twice = [list(t) for t in PY_LE_RULE["replacement_tokens"]]
        twice[4] = ["op", ">"]
        twice[6] = ["hole_id", "?id7"]
        self.assertIsNone(rar.OperatorRewrite.from_tokens(PY_LE_RULE["pattern_tokens"], twice))
        # A non-comparison change (arithmetic) is outside this loop's alphabet.
        arithmetic = [list(t) for t in PY_LE_RULE["replacement_tokens"]]
        arithmetic[4] = ["op", "+"]
        self.assertIsNone(rar.OperatorRewrite.from_tokens(PY_LE_RULE["pattern_tokens"], arithmetic))

    def test_01_the_procedures_are_total_and_blind_to_non_comparisons(self) -> None:
        rewrite = rar.OperatorRewrite(before="<=", after="<")
        self.assertEqual(rar.apply_direct("a <= b", rewrite), ("a < b", 1))
        self.assertEqual(rar.apply_direct("a<=b and c <= d", rewrite), ("a<b and c < d", 2))
        self.assertEqual(rar.apply_direct("a < b", rewrite), ("a < b", 0))
        # `->`, `=>` and shifts are not comparisons and must not be touched.
        untouched = "fn f(x: i64) -> bool { let y = x << 2; }"
        self.assertEqual(rar.apply_direct(untouched, rewrite), (untouched, 0))
        self.assertEqual(rar.apply_inverted("cap >= score", rewrite), ("cap > score", 1))
        self.assertEqual(rar.apply_inverted("a < b", rewrite), ("a < b", 0))


class TestAcquisitionLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = RefusalLoop = rar.RefusalAcquisitionLoop()
        self.assertIsInstance(RefusalLoop, rar.RefusalAcquisitionLoop)

    def test_02_acquire_verify_retry_and_remember(self) -> None:
        first = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="fn within(score: i64, cap: i64) -> bool { score <= cap }",
            target_language="rust",
            verifier=lambda s: "score < cap" in s,
        )
        self.assertTrue(first["pass"])
        self.assertEqual(first["status"], "PASS__ACQUIRED_AFTER_REFUSAL")
        self.assertEqual(first["acquisition"]["procedure"], "DIRECT_OPERATOR_REWRITE")
        self.assertEqual(first["acquisition"]["search_steps"], 1)
        self.assertFalse(first["acquisition"]["reused"])
        self.assertEqual(first["model_calls"], 0)
        self.assertEqual(first["refusals"][0]["code"], "CROSS_LANGUAGE_BRIDGE_PRODUCED_NOTHING")

        second = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="fn other(lo: i64, hi: i64) -> bool { lo <= hi }",
            target_language="rust",
            verifier=lambda s: "lo < hi" in s,
        )
        self.assertTrue(second["pass"])
        self.assertTrue(second["acquisition"]["reused"])
        self.assertEqual(second["acquisition"]["search_steps"], 1)
        self.assertEqual(self.loop.store.hits, 1)

    def test_03_the_inverted_procedure_is_what_converts_the_harder_instance(self) -> None:
        result = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="func fits(load int, limit int) bool { return limit >= load }",
            target_language="go",
            verifier=lambda s: "limit > load" in s,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["acquisition"]["procedure"], "INVERTED_OPERAND_REWRITE")
        self.assertEqual(result["acquisition"]["search_steps"], 2)
        tried = [row["procedure"] for row in result["acquisition"]["procedures_tried"]]
        self.assertEqual(tried, ["DIRECT_OPERATOR_REWRITE"])

    def test_04_nothing_is_admitted_without_the_caller_s_verifier(self) -> None:
        rejected = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="fn f(a: i64, b: i64) -> bool { a <= b }",
            target_language="rust",
            verifier=lambda _s: False,
        )
        self.assertFalse(rejected["pass"])
        self.assertEqual(rejected["status"], "REFUSED__ACQUISITION_FAILED")
        self.assertIsNone(rejected["acquisition"]["procedure"])
        self.assertEqual(self.loop.store.as_dict()["admitted"], 0)

        raising = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="fn f(a: i64, b: i64) -> bool { a <= b }",
            target_language="rust",
            verifier=lambda _s: (_ for _ in ()).throw(RuntimeError("VERIFIER_IS_DEAD")),
        )
        self.assertFalse(raising["pass"])
        self.assertEqual(raising["acquisition"]["procedures_tried"][0]["why"], "VERIFIER_RAISED:RuntimeError")

        no_verifier = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE, source_text="a <= b", target_language="rust", verifier=None,
        )
        self.assertEqual(no_verifier["status"], "REFUSED__ACQUISITION_REQUIRES_A_VERIFIER")

    def test_05_a_syntax_check_can_veto_a_verified_candidate(self) -> None:
        result = self.loop.acquire_cross_language_patch(
            rule=PY_LE_RULE,
            source_text="fn f(a: i64, b: i64) -> bool { a <= b }",
            target_language="rust",
            verifier=lambda _s: True,
            parse_check=lambda _lang, _text: (False, "TARGET_SYNTAX_INVALID:rust"),
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["acquisition"]["procedures_tried"][0]["why"], "TARGET_SYNTAX_INVALID:rust")


class TestRatchetIntegration(unittest.TestCase):
    def test_06_the_ratchet_reports_the_acquisition_and_grows_its_store(self) -> None:
        ratchet = _kernel().skill_ratchet
        result = ratchet.consolidate_and_transfer(
            before_snippet="def check(x, hi):\n    return x <= hi\n",
            after_snippet="def check(x, hi):\n    return x < hi\n",
            target_language="rust",
            target_buggy_source="fn within(score: i64, cap: i64) -> bool { score <= cap }",
            target_verifier=lambda s: "score < cap" in s,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["status"], "PASS__ACQUIRED_AFTER_REFUSAL")
        self.assertTrue(result["cross_language_transfer"]["acquired_after_refusal"])
        self.assertEqual(result["cross_language_transfer"]["acquisition_steps"], 1)
        self.assertEqual(result["refusal_acquisition"]["store"]["admitted"], 1)
        self.assertEqual(result["model_calls"], 0)

        again = ratchet.consolidate_and_transfer(
            before_snippet="def check(x, hi):\n    return x <= hi\n",
            after_snippet="def check(x, hi):\n    return x < hi\n",
            target_language="rust",
            target_buggy_source="fn pair(lo: i64, hi: i64) -> bool { lo <= hi }",
            target_verifier=lambda s: "lo < hi" in s,
        )
        self.assertTrue(again["cross_language_transfer"]["acquisition_reused"])

    def test_07_an_unreachable_instance_still_refuses_and_says_why(self) -> None:
        ratchet = _kernel().skill_ratchet
        result = ratchet.consolidate_and_transfer(
            before_snippet="def check(x, hi):\n    return x <= hi\n",
            after_snippet="def check(x, hi):\n    return x < hi\n",
            target_language="go",
            target_buggy_source="func f(a int, b int) bool { return a == b }",
            target_verifier=lambda _s: False,
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "REFUSED__CROSS_LANGUAGE_TRANSFER_NOT_PRODUCED")
        self.assertIsNone(result["cross_language_transfer"])
        self.assertEqual(result["refusal_acquisition"]["status"], "REFUSED__ACQUISITION_FAILED")

    def test_08_the_edit_keeps_the_file_s_own_alphabet(self) -> None:
        ratchet = _kernel().skill_ratchet
        source = "fn within(score: i64, cap: i64) -> bool { score <= cap }"
        result = ratchet.consolidate_and_transfer(
            before_snippet="def check(x, hi):\n    return x <= hi\n",
            after_snippet="def check(x, hi):\n    return x < hi\n",
            target_language="rust",
            target_buggy_source=source,
            target_verifier=lambda s: "score < cap" in s,
        )
        patched = result["cross_language_transfer"]["patched_source"]
        self.assertEqual(patched, source.replace("<=", "<"))
        # No identifier is introduced: every name in the patch is a name the file already had.
        names = lambda text: {w for w in text.replace("<=", " ").replace("<", " ").split()}  # noqa: E731
        self.assertEqual(names(patched), names(source))


class TestMeasuredByTheBench(unittest.TestCase):
    def test_09_the_bench_measures_this_capability_and_it_is_the_cause(self) -> None:
        category = "REFUSAL_ACQUISITION_RETRY"
        self.assertIn(category, bench.CATEGORIES)
        honest = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=3, categories=[category])
        self.assertEqual(honest["instances"], 3)
        self.assertEqual(honest["passed"], 3)
        self.assertEqual(honest["false_success_claims"], 0)

        class _NoAcquisition(bench.Sut):
            """The same kernel, with the acquisition loop refusing everything."""

            def __init__(self) -> None:
                def _factory() -> object:
                    kern = UnifiedFivePillarKernel()
                    dead = mock.Mock()
                    dead.acquire_cross_language_patch.return_value = {
                        "schema": rar.SCHEMA,
                        "pass": False,
                        "status": "REFUSED__ACQUISITION_FAILED",
                        "acquisition": {"procedure": None, "search_steps": 0, "reused": False},
                        "model_calls": 0,
                    }
                    kern.skill_ratchet.refusal_loop = dead
                    return kern

                super().__init__(kernel=_factory, synth=None)

        crippled = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=3,
                                   categories=[category], sut=_NoAcquisition())
        # Two of the three instances can only be passed by acquiring; the refusal control passes.
        self.assertEqual(crippled["by_category"][category]["passed"], 1)
        self.assertEqual(crippled["by_category"][category]["failed"], 2)

        full = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=3)
        self.assertEqual(full["instances"], 3 * len(bench.CATEGORIES))
        self.assertEqual(full["passed"], full["instances"])
        self.assertEqual(full["pass_rate"], 1.0)


class TestReachability(unittest.TestCase):
    def test_10_the_federation_and_the_model_can_ask_for_the_acquisition(self) -> None:
        verifier = lambda s: "score < cap" in s  # noqa: E731 - a one-line predicate is the point
        fed = run_federated_engine(
            "LEAPFROG_W41_REFUSAL_ACQUIRE_RETRY",
            {
                "rule": PY_LE_RULE,
                "source_text": "fn within(score: i64, cap: i64) -> bool { score <= cap }",
                "target_language": "rust",
                "verifier": verifier,
            },
        )
        self.assertTrue(fed["pass"])
        self.assertIn("ACQUIRED_AFTER_REFUSAL", str(fed["status"]))
        self.assertEqual(fed["model_calls"], 0)

        missing_verifier = run_federated_engine(
            "LEAPFROG_W41_REFUSAL_ACQUIRE_RETRY",
            {"rule": PY_LE_RULE, "source_text": "a <= b", "target_language": "rust"},
        )
        self.assertFalse(missing_verifier["pass"])
        # The engine's declared inputs are enforced before dispatch, so the refusal names the
        # missing term at the boundary rather than inside the acquisition.
        self.assertIn("ENGINE_INPUTS_MISSING:verifier", str(missing_verifier["status"]))
        self.assertEqual(missing_verifier["model_calls"], 0)

        model = open_model()
        acquired = model.refusal_acquire_retry(
            rule=PY_LE_RULE,
            source_text="fn fits(mass: f64, budget: f64) -> bool { mass <= budget }",
            target_language="rust",
            verifier=lambda s: "mass < budget" in s,
        )
        self.assertTrue(acquired["pass"])
        self.assertEqual(acquired["patched_source"],
                         "fn fits(mass: f64, budget: f64) -> bool { mass < budget }")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

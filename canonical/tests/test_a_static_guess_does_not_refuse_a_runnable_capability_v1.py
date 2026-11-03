#!/usr/bin/env python3
"""A static guess was refusing 19 capabilities that run fine, and costing 16 more.

WHY THIS FILE EXISTS
--------------------
`_extract_capability_feature_flags` set `causal_precond_met=False` and
`reason="writes_fixed_repo_tmp_under_ro_input"` for any adapter whose source
contained a `canonical/tmp_*` string literal:

    if isinstance(nd, ast.Constant) and nd.value.startswith("canonical/tmp_"):
        reads_repo_rooted_paths = True

Measured 2026-11-03/04, in three steps:

1. Every one of the 19 capabilities carrying that refusal uses the literal as a
   CALLER-OVERRIDABLE FALLBACK -- `str(raw or "canonical/tmp_...")`, or
   `fresh_output(repo, args.get("output_path"), "canonical/tmp_...")` whose
   second parameter exists to override the third. None writes it
   unconditionally.
2. On the onboarding path the adapter's `root` is `/work/repo` -- writable, per
   run -- not the read-only `/input`. So the literal, even when reached, is not
   the read-only write the refusal claims.
3. With the refusal lifted for those 19, FIFTEEN onboard on two genuinely
   passing runs with distinct binds. The four that fail (NO_GENUINELY_PASSING_RUNS,
   WALLCLOCK_LIMIT_EXCEEDED) still fail, so the onboarding gate is doing its job
   and this change does not launder them.

The refusal therefore pre-empted the runtime authority that was going to judge
the write anyway. It is replaced by a test of UNCONDITIONAL writes, which keeps
the genuine protection.

The second, larger cost: the same condition also set
`nested_cost_or_timeout_risk`, which is mandatory, so 16 further capabilities
were failing `not is_mandatory` one layer down. READY went 33 -> 52.

Falsifier for this file: restore the blanket constant test and tests 1, 2 and 4
fail. Test 3 (unconditional write still refused) must keep passing either way --
it is the proof that protection was not removed, only narrowed to the truth.
"""
from __future__ import annotations

import ast
import pathlib
import tempfile
import unittest

from canonical.runtime import creature_runtime_v1 as cr
from canonical.runtime import expect_discrimination_v1 as ED

PREVIOUSLY_REFUSED = "python.fault.patch.supercomposer.v1"

UNCONDITIONAL_WRITE = '''
def run(args, root):
    p = root / "canonical/tmp_unconditional.json"
    p.write_text("x")
'''

OVERRIDABLE_FALLBACK = '''
def run(args, root):
    p = (root / str(args.get("output_path") or "canonical/tmp_ok.json")).resolve()
'''

HELPER_FALLBACK = '''
def run(args, root):
    out = fresh_output(repo, args.get("output_path"), "canonical/tmp_helper.json")
'''


class AStaticGuessIsNotAnAuthority(unittest.TestCase):
    def test_a_caller_overridable_fallback_is_not_a_fixed_write(self) -> None:
        self.assertFalse(cr._writes_fixed_repo_tmp_unconditionally(ast.parse(OVERRIDABLE_FALLBACK)))

    def test_the_fresh_output_helper_convention_is_not_a_fixed_write(self) -> None:
        self.assertFalse(cr._writes_fixed_repo_tmp_unconditionally(ast.parse(HELPER_FALLBACK)))

    # ------------------------------------------------------------------ 3
    # The load-bearing negative control: the real protection must survive.

    def test_an_unconditional_write_to_the_repo_is_still_refused(self) -> None:
        self.assertTrue(cr._writes_fixed_repo_tmp_unconditionally(ast.parse(UNCONDITIONAL_WRITE)))

    # ------------------------------------------------------------------ 4

    def test_a_previously_refused_capability_is_now_ready(self) -> None:
        cr._CAPABILITY_FEATURE_CACHE.clear()
        flags = cr._extract_capability_feature_flags(PREVIOUSLY_REFUSED)
        self.assertNotEqual(flags["reason"], "writes_fixed_repo_tmp_under_ro_input")
        self.assertTrue(flags["causal_precond_met"])
        self.assertFalse(flags["missing_dep_or_env_block"])

    def test_no_registered_capability_is_still_refused_on_that_ground(self) -> None:
        """Every adapter carrying such a literal was measured as fallback-only."""
        reg_ids, _ = cr._registry_and_inspectors()
        cr._CAPABILITY_FEATURE_CACHE.clear()
        still = [c for c in sorted(reg_ids)
                 if cr._extract_capability_feature_flags(c)["reason"] == "writes_fixed_repo_tmp_under_ro_input"]
        self.assertEqual(still, [], f"still refused on a fallback-only literal: {still[:5]}")


class TheCreatureConvertsThatReachIntoCapability(unittest.TestCase):
    """Reach that a session does not convert into an onboarded skill is not capability."""

    def test_a_real_session_onboards_a_previously_refused_capability(self) -> None:
        cr._CAPABILITY_FEATURE_CACHE.clear()
        with tempfile.TemporaryDirectory(prefix="brain-static-guess-") as td:
            creature = cr.boot(pathlib.Path(td) / "creature", identity="reach", life=120.0)
            res = cr._onboard_typed_capability_inspector(PREVIOUSLY_REFUSED, creature)
        self.assertTrue(
            res.get("ok"),
            f"{PREVIOUSLY_REFUSED} was refused statically and reports {res.get('reason')} when "
            f"actually run; the static refusal was right after all",
        )

    def test_the_reachable_set_is_much_larger_than_before(self) -> None:
        reg_ids, _ = cr._registry_and_inspectors()
        cr._CAPABILITY_FEATURE_CACHE.clear()
        ready = 0
        for cid in sorted(reg_ids):
            f = cr._extract_capability_feature_flags(cid)
            if f["host_ready"] and f["grounding_complete"] and f["causal_precond_met"] \
                    and not f["missing_dep_or_env_block"]:
                ready += 1
        # 33 before this change; 52 measured with it. The floor is set well below the
        # measurement so an unrelated substrate change does not fail this test, but far above
        # the pre-change value so a re-introduced blanket refusal cannot pass it.
        self.assertGreater(ready, 40, f"only {ready} of {len(reg_ids)} capabilities are reachable")


class OnboardingStillRefusesWhatCannotPass(unittest.TestCase):
    """The complement: loosening a precondition must not launder a capability that cannot pass."""

    def test_a_capability_with_no_genuinely_passing_run_is_still_refused(self) -> None:
        cr._CAPABILITY_FEATURE_CACHE.clear()
        with tempfile.TemporaryDirectory(prefix="brain-static-guess-neg-") as td:
            creature = cr.boot(pathlib.Path(td) / "creature", identity="neg", life=120.0)
            res = cr._onboard_typed_capability_inspector("python.symbol.resolve.standalone.v1", creature)
        self.assertFalse(res.get("ok"))
        self.assertIn("NO_GENUINELY_PASSING_RUNS", str(res.get("reason")))


if __name__ == "__main__":
    unittest.main(verbosity=2)

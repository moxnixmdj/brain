from __future__ import annotations

import unittest

from canonical.runtime.root3_single_popen_chokepoint_v1 import (
    SingleChokepointError,
    analyze_run_delegation,
    audit,
)


class Root3SinglePopenChokepointTests(unittest.TestCase):
    def test_current_runtime_reduces_29_sites_to_one(self):
        out = audit()
        self.assertEqual(out["prior_direct_process_call_site_count"], 29)
        self.assertEqual(
            out["new_minimum_structural_chokepoints"],
            ["subprocess.Popen"],
        )
        self.assertGreaterEqual(
            out["stdlib_run_delegation"]["global_popen_load_count"],
            1,
        )
        self.assertEqual(out["wiring_actions_deleted"], 28)
        self.assertEqual(out["accounting"]["acceptance_credit_delta"], 0)

    def test_fake_run_without_global_popen_is_rejected(self):
        def fake_run(*args, **kwargs):
            return None

        with self.assertRaises(SingleChokepointError):
            analyze_run_delegation(fake_run, fake_run.__globals__)

    def test_open_residuals_are_preserved(self):
        out = audit()
        self.assertIn(
            "PROVE_CHILD_PROGRAM_INTERNAL_EFFECTS_ARE_SANDBOXED_OR_SEPARATELY_MEDIATED",
            out["remaining_after_single_chokepoint"],
        )
        self.assertIn(
            "NO_CLAIM_NATIVE_EXTENSION_PROCESS_CREATION_IS_INTERCEPTED",
            out["hard_nonclaims"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

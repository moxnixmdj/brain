import ast
import unittest

from canonical.runtime import composition_cross_step_channel_audit_v3 as audit


class ChannelAuditV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = audit.evaluate()

    def test_current_audit_passes_on_exact_bytes(self):
        self.assertTrue(self.out["status"].startswith("PASS__EXHAUSTIVE"), self.out["errors"])
        self.assertEqual(self.out["errors"], [])
        self.assertEqual(len(self.out["runtime_git_blob_sha"]), 40)

    def test_eight_channels_enumerated_with_four_quarantined(self):
        self.assertEqual(len(self.out["channels"]), 8)
        self.assertEqual(
            self.out["quarantined_channels"],
            [
                "NETWORK_AND_EXTERNAL_SYSTEMS",
                "PROCESS_AND_PORT_STATE",
                "SHARED_CWD_FILESYSTEM",
                "SYSTEM_PACKAGE_STATE",
            ],
        )
        self.assertEqual(
            self.out["declared_or_constant_channels"],
            [
                "EXTERNAL_TOOL_BRIDGE",
                "PARENT_ENV_COPY",
                "RUNTIME_OUTPUT_AND_STATE_FILES",
                "SHELL_ENV_PROJECTION",
            ],
        )

    def test_declared_channels_name_their_exact_binding(self):
        for name in ("SHELL_ENV_PROJECTION", "EXTERNAL_TOOL_BRIDGE"):
            self.assertTrue(self.out["channels"][name]["binding"])
        for name in ("SHARED_CWD_FILESYSTEM", "PROCESS_AND_PORT_STATE"):
            self.assertIsNone(self.out["channels"][name]["binding"])
            self.assertTrue(self.out["channels"][name]["note"])

    def test_shared_filesystem_quarantine_names_login_shell_amplifier(self):
        amplifiers = self.out["channels"]["SHARED_CWD_FILESYSTEM"]["amplifiers"]
        self.assertTrue(any("LOGIN_SHELL_PROFILE" in a for a in amplifiers))

    def test_completeness_flags_stay_unverified(self):
        self.assertEqual(self.out["semantic_declaration_completeness"], "UNVERIFIED")
        self.assertEqual(self.out["external_evidence_channel_completeness"], "UNVERIFIED")
        self.assertEqual(
            self.out["preserved_unverified"],
            {
                "semantic_declaration_completeness": "UNVERIFIED",
                "external_evidence_channel_completeness": "UNVERIFIED",
            },
        )

    def test_zero_credit_and_hard_nonclaims(self):
        accounting = self.out["accounting"]
        for key in (
            "incremental_spend_usd",
            "composition_acceptance_credit_delta",
            "family_credit_delta",
            "capability_credit_delta",
            "ownership_credit_delta",
            "terminal_credit_delta",
        ):
            self.assertEqual(accounting[key], 0)
        joined = " ".join(self.out["hard_nonclaims"])
        self.assertIn("NO_COMPOSITION_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT", joined)

    def test_unknown_channel_function_fails_closed(self):
        tree = ast.parse(
            "def _sneaky_helper():\n"
            "    import subprocess\n"
            "    subprocess.run(['x'])\n"
        )
        inventory = audit.derive_inventory(tree)
        errors = audit.diff_inventory(inventory, {"subprocess": {}})
        self.assertTrue(any("CHANNEL_SITE_DRIFT:subprocess:_sneaky_helper" in e for e in errors))

    def test_channel_count_drift_fails_closed(self):
        errors = audit.diff_inventory(
            {"subprocess": {"run_shell": 2}},
            {"subprocess": {"run_shell": 1}},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("expected=1:actual=2", errors[0])

    def test_removed_channel_function_fails_closed(self):
        errors = audit.diff_inventory(
            {"subprocess": {}},
            {"subprocess": {"run_shell": 1}},
        )
        self.assertTrue(any("run_shell" in e for e in errors))

    def test_exact_inventory_match_has_no_errors(self):
        errors = audit.diff_inventory(audit.EXPECTED_INVENTORY, audit.EXPECTED_INVENTORY)
        self.assertEqual(errors, [])

    def test_live_inventory_matches_expected_exactly(self):
        source = audit.RUNTIME.read_text(encoding="utf-8")
        inventory = audit.derive_inventory(ast.parse(source))
        self.assertEqual(audit.diff_inventory(inventory, audit.EXPECTED_INVENTORY), [])

    def test_expected_inventory_drift_forces_fail_closed_evaluate(self):
        original = dict(audit.EXPECTED_INVENTORY["subprocess"])
        try:
            audit.EXPECTED_INVENTORY["subprocess"] = {
                **original,
                "run_shell": 99,
            }
            out = audit.evaluate()
        finally:
            audit.EXPECTED_INVENTORY["subprocess"] = original
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("CHANNEL_SITE_DRIFT" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main()

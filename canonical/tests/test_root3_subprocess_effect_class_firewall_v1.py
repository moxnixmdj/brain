from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import root3_subprocess_effect_class_firewall_v1 as fw


class Root3EffectClassFirewallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in [
            "canonical/runtime/astra_runtime.py",
            "canonical/runtime/bound_capabilities/cli_command.py",
            "canonical/runtime/capability_discovery.py",
        ]:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# fixture\n")

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, rel, line, function="f"):
        return {
            "filename": str(self.root / rel),
            "lineno": line,
            "function": function,
        }

    def request(self, api="subprocess.run"):
        return {"api": api, "schema": "test"}

    def test_astra_generic_shell_is_exactly_arbitrary(self):
        site = fw.resolve_effect_site(
            "subprocess.run",
            [self.row("canonical/runtime/astra_runtime.py", 263, "run_shell")],
            repo_root=self.root,
        )
        self.assertEqual(site["effect_class"], "ARBITRARY_COMMAND_EXECUTION")

    def test_generic_cli_adapter_is_exactly_arbitrary(self):
        site = fw.resolve_effect_site(
            "subprocess.run",
            [self.row("canonical/runtime/bound_capabilities/cli_command.py", 27, "run")],
            repo_root=self.root,
        )
        self.assertEqual(site["effect_class"], "ARBITRARY_COMMAND_EXECUTION")

    def test_arbitrary_class_denies_before_downstream_lookup(self):
        calls = []
        authorizer = fw.make_effect_class_firewall(
            lambda req: calls.append(dict(req)) or {
                "allowed": True,
                "authorization_sha256": "a" * 64,
            },
            repo_root=self.root,
        )
        rows = [self.row("canonical/runtime/astra_runtime.py", 263, "run_shell")]
        with patch.object(fw, "_live_frame_rows", return_value=rows):
            out = authorizer(self.request())
        self.assertFalse(out["allowed"])
        self.assertIn("EFFECT_CLASS_FORBIDDEN", out["reason"])
        self.assertEqual(calls, [])
        self.assertFalse(out["downstream_authorizer_called"])

    def test_known_nonarbitrary_class_delegates_once(self):
        calls = []
        authorizer = fw.make_effect_class_firewall(
            lambda req: calls.append(dict(req)) or {
                "allowed": True,
                "authorization_sha256": "b" * 64,
            },
            repo_root=self.root,
        )
        rows = [
            self.row(
                "canonical/runtime/capability_discovery.py",
                267,
                "probe",
            )
        ]
        with patch.object(fw, "_live_frame_rows", return_value=rows):
            out = authorizer(self.request())
        self.assertTrue(out["allowed"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["root3_effect_class"], "READ_ONLY_DECLARED_QUERY")
        self.assertEqual(
            out["root3_process_site"]["module_path"],
            "canonical/runtime/capability_discovery.py",
        )

    def test_unknown_site_fails_closed_before_downstream(self):
        calls = []
        authorizer = fw.make_effect_class_firewall(
            lambda req: calls.append(dict(req)) or {"allowed": True},
            repo_root=self.root,
        )
        rows = [self.row("canonical/runtime/capability_discovery.py", 9999)]
        with patch.object(fw, "_live_frame_rows", return_value=rows):
            out = authorizer(self.request())
        self.assertFalse(out["allowed"])
        self.assertIn("PROCESS_SITE_NOT_IN_FROZEN_EFFECT_REGISTRY", out["reason"])
        self.assertEqual(calls, [])

    def test_wrong_api_does_not_match_a_known_site(self):
        calls = []
        authorizer = fw.make_effect_class_firewall(
            lambda req: calls.append(dict(req)) or {"allowed": True},
            repo_root=self.root,
        )
        rows = [self.row("canonical/runtime/astra_runtime.py", 263)]
        with patch.object(fw, "_live_frame_rows", return_value=rows):
            out = authorizer(self.request("os.system"))
        self.assertFalse(out["allowed"])
        self.assertIn("SUBPROCESS_API_UNSUPPORTED", out["reason"])
        self.assertEqual(calls, [])

    def test_ambiguous_registry_sites_fail_closed(self):
        rows = [
            self.row("canonical/runtime/astra_runtime.py", 263),
            self.row("canonical/runtime/bound_capabilities/cli_command.py", 27),
        ]
        with self.assertRaisesRegex(
            fw.EffectClassFirewallError, "PROCESS_SITE_AMBIGUOUS"
        ):
            fw.resolve_effect_site(
                "subprocess.run",
                rows,
                repo_root=self.root,
            )

    def test_path_outside_repo_cannot_launder_known_line_number(self):
        outside = Path(self.tmp.name).parent / "astra_runtime.py"
        with self.assertRaisesRegex(
            fw.EffectClassFirewallError,
            "PROCESS_SITE_NOT_IN_FROZEN_EFFECT_REGISTRY",
        ):
            fw.resolve_effect_site(
                "subprocess.run",
                [{"filename": str(outside), "lineno": 263, "function": "run_shell"}],
                repo_root=self.root,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

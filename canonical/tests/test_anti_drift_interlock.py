#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

import anti_drift_interlock as a


class AntiDriftInterlockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        p = self.root / "canonical" / "governance"
        p.mkdir(parents=True)
        self.hierarchy = {
            "status": "CANONICAL_FAIL_CLOSED",
            "active_capability_target": "CAP",
            "current_parent_blocker": "BLOCK",
            "next_required_action_class": "DO_ONLY_THIS",
            "active_probe": "PROBE",
            "antidrift_interlock": {
                "schema": a.POLICY_SCHEMA,
                "mode": "FAIL_CLOSED",
                "deny_unknown_authority": True,
                "denied_action_classes": ["PROVIDER_SEARCH", "LAPTOP_EXECUTION"],
            },
        }
        self.path = p / "ACTIVE_GOAL_HIERARCHY_V1.json"
        self._write_hierarchy()
        self.binding = self._binding()

    def tearDown(self):
        os.environ.pop(a.ENV_REQUIRED, None)
        os.environ.pop(a.ENV_BINDING, None)
        self.tmp.cleanup()

    def _write_hierarchy(self):
        self.path.write_text(json.dumps(self.hierarchy, indent=2) + "\n", encoding="utf-8")

    def _sha(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def _binding(self):
        return {
            "schema": a.BINDING_SCHEMA,
            "hierarchy_sha256": self._sha(),
            "capability_target": "CAP",
            "causal_blocker": "BLOCK",
            "action_class": "DO_ONLY_THIS",
            "active_probe": "PROBE",
            "allowed_adapters": ["goal", "shell", "http"],
            "allowed_action_types": ["read_file", "http_get", "finish"],
            "allowed_repo_prefixes": ["canonical/allowed"],
            "allowed_url_hosts": ["example.org"],
            "allowed_shell_sha256": [hashlib.sha256(b"printf ok").hexdigest()],
            "allowed_capability_ids": [],
        }

    def _env(self):
        os.environ.update(a.binding_environment(self.binding))

    def test_valid_task_is_admitted(self):
        got = a.authorize_task(self.root, {"incremental_spend_usd": 0, "antidrift": self.binding})
        self.assertEqual(got["causal_blocker"], "BLOCK")

    def test_missing_binding_fails_closed(self):
        with self.assertRaisesRegex(a.DriftDenied, "TASK_BINDING_MISSING"):
            a.authorize_task(self.root, {"incremental_spend_usd": 0})

    def test_stale_parent_blocker_is_denied(self):
        bad = dict(self.binding)
        bad["causal_blocker"] = "OLD_BLOCK"
        with self.assertRaisesRegex(a.DriftDenied, "BINDING_MISMATCH:causal_blocker"):
            a.validate_binding(self.root, bad)

    def test_hierarchy_change_invalidates_live_binding(self):
        self._env()
        self.hierarchy["current_parent_blocker"] = "NEW_BLOCK"
        self._write_hierarchy()
        with self.assertRaisesRegex(a.DriftDenied, "HIERARCHY_HASH_MISMATCH"):
            a.authorize_action_from_env(self.root, {"type": "finish", "args": {}})

    def test_provider_style_action_not_allowlisted(self):
        self._env()
        with self.assertRaisesRegex(a.DriftDenied, "ACTION_TYPE_DENIED"):
            a.authorize_action_from_env(self.root, {"type": "provider_search", "args": {}})

    def test_repo_scope_is_enforced(self):
        self._env()
        with self.assertRaisesRegex(a.DriftDenied, "REPO_SCOPE_DENIED"):
            a.authorize_action_from_env(
                self.root, {"type": "read_file", "args": {"path": "canonical/elsewhere/x.json"}}
            )

    def test_url_host_is_enforced(self):
        self._env()
        with self.assertRaisesRegex(a.DriftDenied, "URL_SCOPE_DENIED"):
            a.authorize_action_from_env(
                self.root, {"type": "http_get", "args": {"url": "https://replit.com/anything"}}
            )

    def test_shell_requires_exact_hash(self):
        self._env()
        with self.assertRaisesRegex(a.DriftDenied, "SHELL_COMMAND_DENIED"):
            a.authorize_step_from_env(self.root, {"adapter": "shell", "command": "curl somewhere"})

    def test_exact_shell_hash_is_admitted(self):
        self._env()
        a.authorize_step_from_env(self.root, {"adapter": "shell", "command": "printf ok"})

    def test_runtime_context_missing_fails_closed(self):
        with self.assertRaisesRegex(a.DriftDenied, "RUNTIME_CONTEXT_MISSING"):
            a.require_runtime_context(self.root)


if __name__ == "__main__":
    unittest.main()

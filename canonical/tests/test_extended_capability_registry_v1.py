from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import live_integrated_brain_v1 as brain
from canonical.runtime.autonomous_capability_inventory_v1 import SCHEMA, build_inventory


class ExtendedRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / "BOUND_CAPABILITY_REGISTRY_V1.json"
        self.entry = {"status": "VERIFIED_BOUND_CAPABILITY", "incremental_spend_usd": 0, "verification": {"verified": True}}
        self.registry.write_text(json.dumps({"schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1", "capabilities": {"base": self.entry}}))
        patcher = patch.object(brain, "REGISTRY", self.registry)
        patcher.start()
        self.addCleanup(patcher.stop)

    def extended(self, entries):
        (self.root / "AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json").write_text(json.dumps({"schema": SCHEMA, "capabilities": entries}))

    def test_missing_optional_registry(self):
        self.assertEqual(brain.load_verified_registry(), {"base": self.entry})

    def test_merge_opt_out_and_canonical_precedence(self):
        self.extended({"new": self.entry, "base": dict(self.entry, marker="extended")})
        self.assertEqual(set(brain.load_verified_registry()), {"base", "new"})
        self.assertEqual(brain.load_verified_registry()["base"], self.entry)
        self.assertEqual(set(brain.load_verified_registry(False)), {"base"})

    def test_unverified_unknown_cost_and_nonzero_excluded(self):
        entries = {"inventory": {"status": "UNVERIFIED_INVENTORY"}, "unchecked": dict(self.entry, verification={})}
        for i, cost in enumerate([None, True, "0", 1, -1, float("nan"), float("inf")]):
            entries[str(i)] = dict(self.entry, incremental_spend_usd=cost)
        self.extended(entries)
        self.assertEqual(set(brain.load_verified_registry()), {"base"})

    def test_malformed_registry_fails_closed(self):
        path = self.root / "AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
        for payload in ["{", "[]", '{"schema":"wrong"}', json.dumps({"schema": SCHEMA, "capabilities": []}), json.dumps({"schema": SCHEMA, "capabilities": {"bad": None}})]:
            with self.subTest(payload=payload):
                path.write_text(payload)
                with self.assertRaisesRegex(brain.LiveBrainError, "EXTENDED_CAPABILITY_REGISTRY_INVALID"):
                    brain.load_verified_registry()
                self.assertEqual(set(brain.load_verified_registry(False)), {"base"})

    def test_inventory_is_deterministic_collision_free_and_nonexecuting(self):
        for relative in ["canonical/a/same.py", "canonical/b/same.py", "canonical/tests/test_x.py", "canonical/runtime/bound_capabilities/x.py"]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('raise RuntimeError("must not import")')
        inventory = build_inventory(self.root)
        self.assertEqual(inventory, build_inventory(self.root))
        self.assertEqual(len(inventory["capabilities"]), 2)
        for entry in inventory["capabilities"].values():
            self.assertEqual(entry["status"], "UNVERIFIED_INVENTORY")
            self.assertFalse(entry["verification"]["verified"])
            self.assertIsNone(entry["incremental_spend_usd"])

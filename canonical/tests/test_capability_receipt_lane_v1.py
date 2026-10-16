#!/usr/bin/env python3
"""Capability execution receipts: prove the mechanism by running it.

These tests execute real inventory modules.  They assert the *mechanism*, not
that any particular capability is correct — a receipt records what was observed,
nothing more.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import _receipt_admits, load_verified_registry  # noqa: E402

EXPECTED_SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"


class ContractShapeTests(unittest.TestCase):
    def test_recognises_the_executor_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args, root):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertEqual(lane.contract_shape(mod), ("run", "root"))

    def test_rejects_wrong_first_parameter(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(normal_form, matrix):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertIsNone(lane.contract_shape(mod))

    def test_rejects_one_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertIsNone(lane.contract_shape(mod))

    def test_rejects_syntax_error_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args, root:\n", encoding="utf-8")
            self.assertIsNone(lane.contract_shape(mod))


class ReceiptTests(unittest.TestCase):
    def test_receipt_is_content_addressed_and_records_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/qr_probe_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text(
                "def run(args, root):\n    return {'status': 'PROBE_OK', 'pass': True}\n",
                encoding="utf-8",
            )
            rel = "canonical/runtime/bound_capabilities/qr_probe_v1.py"
            receipt = lane.execute_and_receipt("probe.v1", rel, "run", str(tmp_path), "test-identity")
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["schema"], EXPECTED_SCHEMA)
            self.assertEqual(receipt["module_sha256"], lane.sha256_file(module))
            self.assertEqual(receipt["observed"], {"status": "PROBE_OK", "pass": True})
            self.assertEqual(receipt["model_dependency_count"], 0)
            self.assertIsNone(receipt["independent_verifier"])

    def test_a_module_that_raises_yields_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/bad_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text(
                "def run(args, root):\n    raise RuntimeError('boom')\n", encoding="utf-8"
            )
            rel = "canonical/runtime/bound_capabilities/bad_v1.py"
            self.assertIsNone(lane.execute_and_receipt("bad.v1", rel, "run", str(tmp_path), "test"))

    def test_receipt_hash_is_order_independent(self):
        self.assertEqual(lane.sha256_canonical({"a": 1, "b": 2}), lane.sha256_canonical({"b": 2, "a": 1}))


class LoaderGateTests(unittest.TestCase):
    """The gate must be ADDITIVE: it admits on evidence and demotes nothing."""

    def test_status_alone_cannot_admit(self):
        entry = {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "verification": {"verified": True},
            "source": {"path": "canonical/runtime/capability_receipt_lane_v1.py"},
        }
        self.assertFalse(_receipt_admits(entry, ROOT))

    def test_receipt_for_a_different_module_body_does_not_admit(self):
        entry = {
            "status": "UNVERIFIED_INVENTORY",
            "verification": {"receipt_path": "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json"},
            "source": {"path": "canonical/runtime/capability_receipt_lane_v1.py"},
        }
        self.assertFalse(_receipt_admits(entry, ROOT))

    def test_existing_capabilities_are_preserved(self):
        """67 live capabilities before this change must still be 67 after it."""
        registry = load_verified_registry(include_extended=True)
        self.assertGreaterEqual(len(registry), 67)

    def test_no_receipt_backed_entry_is_a_status_flip(self):
        """Anything admitted on a receipt must still carry its inventory status."""
        registry = load_verified_registry(include_extended=True)
        for cid, entry in registry.items():
            if entry.get("receipt_backed"):
                self.assertNotEqual(entry.get("status"), "VERIFIED_BOUND_CAPABILITY", cid)


class LaneRunTests(unittest.TestCase):
    def test_discover_finds_contract_shaped_inventory_only(self):
        candidates = lane.discover(str(ROOT))
        self.assertGreater(len(candidates), 100)
        bound = json.loads((ROOT / lane.BOUND).read_text(encoding="utf-8"))["capabilities"]
        for cid, _path, _entrypoint in candidates:
            self.assertNotIn(cid, bound)

    def test_lane_never_claims_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/ok_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text("def run(args, root):\n    return {'status': 'S'}\n", encoding="utf-8")
            receipt = lane.execute_and_receipt(
                "ok.v1", "canonical/runtime/bound_capabilities/ok_v1.py", "run", str(tmp_path), "me"
            )
            self.assertIsNone(receipt["independent_verifier"])
            self.assertIsNone(receipt["independent_run_reference"])


if __name__ == "__main__":
    unittest.main()

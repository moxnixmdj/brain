from __future__ import annotations

import base64
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.root3_broker_rpc_v1 import make_request
from canonical.runtime.root3_parent_driver_registry_v1 import (
    ADMIN_DRIVER_ID,
    REGISTRY,
    ParentDriverRegistryError,
    dispatch,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = REGISTRY[ADMIN_DRIVER_ID]


class Root3ParentDriverRegistryV1Tests(unittest.TestCase):
    def _temp_repo(self):
        td = tempfile.TemporaryDirectory(prefix="root3-parent-driver-")
        root = Path(td.name)
        for rel in (
            SPEC["contract_path"],
            SPEC["implementation_path"],
        ):
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        (root / "canonical/astra_runtime/state").mkdir(parents=True, exist_ok=True)
        (root / "canonical/astra_runtime/evidence").mkdir(parents=True, exist_ok=True)
        return td, root

    def _request(self, typed_args, **overrides):
        return make_request(
            driver_id=overrides.get("driver_id", ADMIN_DRIVER_ID),
            driver_contract_git_blob_sha=overrides.get(
                "contract_sha", SPEC["contract_git_blob_sha"]
            ),
            driver_implementation_git_blob_sha=overrides.get(
                "implementation_sha", SPEC["implementation_git_blob_sha"]
            ),
            typed_args=typed_args,
        )

    def test_exact_admin_state_replace_commits(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        payload = (json.dumps({"status": "RUNNING"}, sort_keys=True) + "\n").encode()
        path = "canonical/astra_runtime/state/MISSION-1.json"
        req = self._request({
            "destination_class": "ASTRA_STATE_JSON",
            "operation": "REPLACE",
            "path": path,
            "expected_pre_sha256": "ABSENT",
            "payload_b64": base64.b64encode(payload).decode("ascii"),
        })
        out = dispatch(root, req)
        self.assertEqual(out["driver_id"], ADMIN_DRIVER_ID)
        self.assertTrue(out["closed_registry"])
        self.assertFalse(out["generic_fallback"])
        self.assertEqual((root / path).read_bytes(), payload)
        self.assertEqual(out["result"]["status"], "COMMITTED")
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_unknown_driver_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        req = self._request({}, driver_id="GENERIC_SHELL_V1")
        with self.assertRaisesRegex(ParentDriverRegistryError, "UNKNOWN_DRIVER_DENY"):
            dispatch(root, req)

    def test_implementation_binding_tamper_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        req = self._request({}, implementation_sha="c" * 40)
        with self.assertRaisesRegex(
            ParentDriverRegistryError, "DRIVER_IMPLEMENTATION_BINDING_MISMATCH"
        ):
            dispatch(root, req)

    def test_contract_binding_tamper_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        req = self._request({}, contract_sha="c" * 40)
        with self.assertRaisesRegex(
            ParentDriverRegistryError, "DRIVER_CONTRACT_BINDING_MISMATCH"
        ):
            dispatch(root, req)

    def test_bound_implementation_file_drift_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        p = root / SPEC["implementation_path"]
        p.write_text(p.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        req = self._request({})
        with self.assertRaisesRegex(
            ParentDriverRegistryError, "DRIVER_BOUND_FILE_DRIFT"
        ):
            dispatch(root, req)

    def test_illegal_persistence_path_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        payload = b'{"x":1}\n'
        req = self._request({
            "destination_class": "ASTRA_STATE_JSON",
            "operation": "REPLACE",
            "path": "canonical/governance/SHOULD_NOT_WRITE.json",
            "expected_pre_sha256": "ABSENT",
            "payload_b64": base64.b64encode(payload).decode("ascii"),
        })
        with self.assertRaisesRegex(Exception, "PATH_NOT_ALLOWED"):
            dispatch(root, req)

    def test_extra_typed_arg_denies(self):
        td, root = self._temp_repo()
        self.addCleanup(td.cleanup)
        payload = b'{"x":1}\n'
        req = self._request({
            "destination_class": "ASTRA_STATE_JSON",
            "operation": "REPLACE",
            "path": "canonical/astra_runtime/state/MISSION-1.json",
            "expected_pre_sha256": "ABSENT",
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "extra": "no",
        })
        with self.assertRaisesRegex(Exception, "TYPED_ARGS_FIELDS_INVALID"):
            dispatch(root, req)


if __name__ == "__main__":
    unittest.main(verbosity=2)

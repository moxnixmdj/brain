from __future__ import annotations

import base64
import json
import socket
import threading
import unittest
import uuid
from pathlib import Path

from canonical.runtime.root3_broker_rpc_v1 import child_roundtrip
from canonical.runtime.root3_parent_broker_server_v1 import serve_fd
from canonical.runtime.root3_parent_driver_registry_v1 import (
    ADMIN_DRIVER_ID,
    REGISTRY,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = REGISTRY[ADMIN_DRIVER_ID]


class Root3ParentBrokerServerV1Tests(unittest.TestCase):
    def test_end_to_end_admin_persistence_roundtrip(self):
        parent, child = socket.socketpair()
        server = []
        name = "ROOT3-BROKER-E2E-" + uuid.uuid4().hex + ".json"
        mission_id = name[:-5]
        rel = "canonical/astra_runtime/state/" + name
        target = ROOT / rel
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        payload = (json.dumps({"status": "RUNNING"}, sort_keys=True) + "\n").encode()

        def run_server():
            server.append(
                serve_fd(
                    parent.fileno(),
                    repo_root=ROOT,
                    authority_context={
                        "mission_id": mission_id,
                        "mission_sha256": "a" * 64,
                        "mission_rel": (
                            "canonical/astra_runtime/missions/"
                            + mission_id
                            + ".json"
                        ),
                    },
                    max_requests=4,
                )
            )

        th = threading.Thread(target=run_server)
        th.start()
        try:
            out = child_roundtrip(
                child.fileno(),
                driver_id=ADMIN_DRIVER_ID,
                driver_contract_git_blob_sha=SPEC["contract_git_blob_sha"],
                driver_implementation_git_blob_sha=SPEC[
                    "implementation_git_blob_sha"
                ],
                typed_args={
                    "destination_class": "ASTRA_STATE_JSON",
                    "operation": "REPLACE",
                    "path": rel,
                    "expected_pre_sha256": "ABSENT",
                    "payload_b64": base64.b64encode(payload).decode("ascii"),
                },
            )
            child.shutdown(socket.SHUT_RDWR)
        finally:
            child.close()
            th.join(timeout=3)
            parent.close()

        self.assertEqual(target.read_bytes(), payload)
        self.assertEqual(out["result"]["status"], "COMMITTED")
        self.assertEqual(
            server,
            [{
                "schema": "PROJECT_BRAIN_ROOT3_PARENT_BROKER_SERVER_V1",
                "status": "CLEAN_EOF",
                "requests_served": 1,
                "closed_driver_registry": True,
                "generic_effect_fallback": False,
                "terminal_credit_delta": 0,
            }],
        )
        self.assertFalse(th.is_alive())

    def test_unknown_driver_is_returned_as_denial(self):
        parent, child = socket.socketpair()
        server = []

        def run_server():
            server.append(
                serve_fd(
                    parent.fileno(),
                    repo_root=ROOT,
                    max_requests=2,
                )
            )

        th = threading.Thread(target=run_server)
        th.start()
        try:
            with self.assertRaisesRegex(Exception, "PARENT_DENIED"):
                child_roundtrip(
                    child.fileno(),
                    driver_id="GENERIC_SHELL_V1",
                    driver_contract_git_blob_sha="a" * 40,
                    driver_implementation_git_blob_sha="b" * 40,
                    typed_args={"command": "echo forbidden"},
                )
            child.shutdown(socket.SHUT_RDWR)
        finally:
            child.close()
            th.join(timeout=3)
            parent.close()

        self.assertEqual(server[0]["status"], "CLEAN_EOF")
        self.assertEqual(server[0]["requests_served"], 1)
        self.assertFalse(th.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)

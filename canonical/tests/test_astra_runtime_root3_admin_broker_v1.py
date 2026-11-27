from __future__ import annotations

import base64
import socket
import threading
import unittest
import uuid
from pathlib import Path
from unittest import mock

from canonical.runtime import astra_runtime as runtime
from canonical.runtime.root3_broker_rpc_v1 import serve_once


class AstraRoot3AdminBrokerV1Tests(unittest.TestCase):
    def test_typed_admin_commit_uses_broker_when_fd_is_present(self):
        parent, child = socket.socketpair()
        seen = []
        target = (
            runtime.ROOT
            / "canonical"
            / "astra_runtime"
            / "state"
            / ("ROOT3-BROKER-BIND-" + uuid.uuid4().hex + ".json")
        )
        self.assertFalse(target.exists())
        payload = b'{"status":"RUNNING"}\n'

        def run_parent():
            serve_once(
                parent,
                lambda request: (
                    seen.append(request)
                    or {
                        "driver_id": request["driver_id"],
                        "status": "COMMITTED_BY_PARENT_TEST",
                    }
                ),
            )

        th = threading.Thread(target=run_parent)
        th.start()
        try:
            with mock.patch.dict(
                runtime.os.environ,
                {"PROJECT_BRAIN_BROKER_FD": str(child.fileno())},
                clear=False,
            ):
                out = runtime._typed_admin_commit(
                    target,
                    payload,
                    "ASTRA_STATE_JSON",
                    "REPLACE",
                )
        finally:
            child.close()
            th.join(timeout=2)
            parent.close()

        self.assertFalse(target.exists())
        self.assertEqual(out["status"], "COMMITTED_BY_PARENT_TEST")
        self.assertEqual(len(seen), 1)
        req = seen[0]
        self.assertEqual(req["driver_id"], "ASTRA_ADMIN_PERSISTENCE_V1")
        self.assertEqual(
            req["driver_contract_git_blob_sha"],
            runtime._ROOT3_ADMIN_DRIVER_CONTRACT_GIT_BLOB_SHA,
        )
        self.assertEqual(
            req["driver_implementation_git_blob_sha"],
            runtime._ROOT3_ADMIN_DRIVER_IMPLEMENTATION_GIT_BLOB_SHA,
        )
        self.assertEqual(
            req["typed_args"],
            {
                "destination_class": "ASTRA_STATE_JSON",
                "operation": "REPLACE",
                "path": target.relative_to(runtime.ROOT).as_posix(),
                "expected_pre_sha256": "ABSENT",
                "payload_b64": base64.b64encode(payload).decode("ascii"),
            },
        )
        self.assertFalse(th.is_alive())

    def test_invalid_broker_fd_fails_closed(self):
        with mock.patch.dict(
            runtime.os.environ,
            {"PROJECT_BRAIN_BROKER_FD": "not-an-int"},
            clear=False,
        ):
            with self.assertRaisesRegex(runtime.Blocker, "ROOT3_BROKER_FD_INVALID"):
                runtime._root3_broker_fd()


if __name__ == "__main__":
    unittest.main(verbosity=2)

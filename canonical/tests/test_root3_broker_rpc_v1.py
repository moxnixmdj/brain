from __future__ import annotations

import socket
import struct
import threading
import unittest

from canonical.runtime.root3_broker_rpc_v1 import (
    BrokerRPCError,
    child_roundtrip,
    make_request,
    make_response,
    recv_frame,
    send_frame,
    serve_once,
    verify_request,
    verify_response,
)


class Root3BrokerRPCV1Tests(unittest.TestCase):
    def test_request_and_response_hash_binding(self):
        req = make_request(driver_id="ADMIN_DURABLE_WRITE_V1", typed_args={"x": 1})
        self.assertEqual(verify_request(req), req)
        resp = make_response(
            request_sha256=req["request_sha256"],
            ok=True,
            result={"status": "ok"},
        )
        self.assertEqual(
            verify_response(resp, expected_request_sha256=req["request_sha256"]),
            resp,
        )

    def test_request_tamper_fails_closed(self):
        req = make_request(driver_id="D", typed_args={"x": 1})
        req["typed_args"]["x"] = 2
        with self.assertRaisesRegex(BrokerRPCError, "REQUEST_CONTENT_OR_HASH_MISMATCH"):
            verify_request(req)

    def test_response_request_mismatch_fails_closed(self):
        req = make_request(driver_id="D", typed_args={})
        resp = make_response(
            request_sha256="a" * 64,
            ok=True,
            result={"x": 1},
        )
        with self.assertRaisesRegex(BrokerRPCError, "RESPONSE_REQUEST_MISMATCH"):
            verify_response(resp, expected_request_sha256=req["request_sha256"])

    def test_bidirectional_roundtrip_over_single_socketpair(self):
        parent, child = socket.socketpair()
        result = {}

        def parent_thread():
            result["response"] = serve_once(
                parent,
                lambda request: {
                    "driver_id": request["driver_id"],
                    "echo": request["typed_args"],
                },
            )

        th = threading.Thread(target=parent_thread)
        th.start()
        try:
            out = child_roundtrip(
                child.fileno(),
                driver_id="INFORMATION_READ_V1",
                typed_args={"url": "https://example.invalid/"},
            )
        finally:
            child.close()
            th.join(timeout=2)
            parent.close()

        self.assertEqual(
            out,
            {
                "driver_id": "INFORMATION_READ_V1",
                "echo": {"url": "https://example.invalid/"},
            },
        )
        self.assertTrue(result["response"]["ok"])
        self.assertFalse(th.is_alive())

    def test_parent_handler_failure_is_returned_as_denial(self):
        parent, child = socket.socketpair()

        def fail(_request):
            raise RuntimeError("no")

        th = threading.Thread(target=lambda: serve_once(parent, fail))
        th.start()
        try:
            with self.assertRaisesRegex(BrokerRPCError, "PARENT_DENIED:RuntimeError:no"):
                child_roundtrip(child.fileno(), driver_id="D", typed_args={})
        finally:
            child.close()
            th.join(timeout=2)
            parent.close()

    def test_oversize_send_fails_closed(self):
        parent, child = socket.socketpair()
        try:
            with self.assertRaisesRegex(BrokerRPCError, "FRAME_TOO_LARGE"):
                send_frame(child, {"x": "123456"}, max_frame_bytes=4)
        finally:
            parent.close()
            child.close()

    def test_oversize_declared_receive_fails_before_payload_read(self):
        parent, child = socket.socketpair()
        try:
            child.sendall(struct.pack("!I", 999))
            with self.assertRaisesRegex(BrokerRPCError, "FRAME_LENGTH_INVALID"):
                recv_frame(parent, max_frame_bytes=10)
        finally:
            parent.close()
            child.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

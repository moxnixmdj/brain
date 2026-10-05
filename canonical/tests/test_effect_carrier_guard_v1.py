import unittest
from unittest.mock import patch

from canonical.runtime.effect_carrier_guard_v1 import execute_authorized_effect

REQ = {
    "request_sha256": "r",
    "effect_kind": "REPO_WRITE",
    "resource": "x",
    "operation": "create",
    "payload_sha256": "p",
}
GRANT = {"grant_sha256": "g"}


def denied():
    return {"allowed": False, "status": "DENY_FAIL_CLOSED", "reason": "no"}


def allowed():
    return {
        "allowed": True,
        "status": "ALLOW_FINAL_AUTHORIZATION",
        "request_sha256": "r",
        "grant_sha256": "g",
        "effect_kind": "REPO_WRITE",
        "resource": "x",
        "operation": "create",
        "payload_sha256": "p",
    }


class CarrierGuardTests(unittest.TestCase):
    def test_deny_never_invokes_carrier(self):
        calls = []

        def carrier(req):
            calls.append(req)
            return {"ok": True}

        with patch(
            "canonical.runtime.effect_carrier_guard_v1.authorize_effect",
            return_value=denied(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=carrier,
            )
        self.assertFalse(out["effect_executed"])
        self.assertEqual(calls, [])

    def test_nonfinal_allow_never_invokes_carrier(self):
        calls = []
        fake = {"allowed": True, "status": "ALLOW_PRECOMMIT"}
        with patch(
            "canonical.runtime.effect_carrier_guard_v1.authorize_effect",
            return_value=fake,
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=lambda r: calls.append(r),
            )
        self.assertFalse(out["effect_executed"])
        self.assertEqual(calls, [])

    def test_final_allow_invokes_carrier_once(self):
        calls = []

        def carrier(req):
            calls.append(req)
            return {"ok": True, "id": "receipt-1"}

        with patch(
            "canonical.runtime.effect_carrier_guard_v1.authorize_effect",
            return_value=allowed(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=carrier,
            )
        self.assertTrue(out["effect_executed"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["request_sha256"], "r")
        self.assertEqual(out["grant_sha256"], "g")
        self.assertEqual(len(out["carrier_result_sha256"]), 64)

    def test_authorization_happens_before_carrier(self):
        order = []

        def auth(*args, **kwargs):
            order.append("authorize")
            return allowed()

        def carrier(req):
            order.append("carrier")
            return None

        with patch(
            "canonical.runtime.effect_carrier_guard_v1.authorize_effect",
            side_effect=auth,
        ):
            execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=carrier,
            )
        self.assertEqual(order, ["authorize", "carrier"])


if __name__ == "__main__":
    unittest.main()

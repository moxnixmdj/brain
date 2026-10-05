import unittest
from unittest.mock import patch

from canonical.runtime.effect_carrier_guard_v2 import execute_authorized_effect

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


class CarrierGuardV2Tests(unittest.TestCase):
    def test_denial_never_invokes_carrier(self):
        calls = []
        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
            return_value=denied(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=lambda r: calls.append(r),
            )
        self.assertEqual(calls, [])
        self.assertFalse(out["carrier_invoked"])
        self.assertEqual(out["effect_completion"], "NOT_ATTEMPTED")

    def test_nonfinal_allow_never_invokes_carrier(self):
        calls = []
        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
            return_value={"allowed": True, "status": "ALLOW_PRECOMMIT"},
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=lambda r: calls.append(r),
            )
        self.assertEqual(calls, [])
        self.assertFalse(out["carrier_invoked"])

    def test_carrier_exception_preserves_uncertainty(self):
        def boom(req):
            raise RuntimeError("after possible mutation")

        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
            return_value=allowed(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=boom,
            )
        self.assertTrue(out["carrier_invoked"])
        self.assertFalse(out["carrier_returned"])
        self.assertEqual(
            out["effect_completion"],
            "UNKNOWN_MAY_HAVE_PARTIALLY_OCCURRED",
        )
        self.assertTrue(
            out["manual_or_domain_specific_reconciliation_required"]
        )

    def test_unserializable_return_does_not_erase_invocation(self):
        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
            return_value=allowed(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=lambda r: {1, 2, 3},
            )
        self.assertTrue(out["carrier_invoked"])
        self.assertTrue(out["carrier_returned"])
        self.assertEqual(
            out["status"],
            "CARRIER_RETURNED_RESULT_BINDING_FAILED",
        )

    def test_bound_return_records_hash(self):
        calls = []

        def carrier(req):
            calls.append(req)
            return {"ok": True, "id": "x"}

        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
            return_value=allowed(),
        ):
            out = execute_authorized_effect(
                REQ,
                GRANT,
                repo_root=".",
                carrier=carrier,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            out["status"],
            "CARRIER_RETURNED_WITH_BOUND_RESULT",
        )
        self.assertEqual(len(out["carrier_result_sha256"]), 64)
        self.assertGreater(out["carrier_result_bytes"], 0)
        self.assertTrue(
            out["domain_specific_postcondition_verification_still_required"]
        )

    def test_authorization_precedes_carrier(self):
        order = []

        def auth(*args, **kwargs):
            order.append("authorize")
            return allowed()

        def carrier(req):
            order.append("carrier")
            return None

        with patch(
            "canonical.runtime.effect_carrier_guard_v2.authorize_effect",
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

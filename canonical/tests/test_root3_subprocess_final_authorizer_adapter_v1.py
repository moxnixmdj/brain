from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.root3_subprocess_final_authorizer_adapter_v1 import (
    make_authorizer,
)


def canon(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def mediator_request():
    core = {
        "schema": "PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V1",
        "api": "subprocess.run",
        "command": {"kind": "ARGV", "items": [{"kind": "STRING", "value": "tool"}]},
        "cwd": None,
        "env": None,
        "stdin": None,
        "stdout": "PIPE",
        "stderr": "PIPE",
        "input": None,
        "shell": False,
        "text": True,
        "capture_output": True,
        "timeout": None,
        "encoding": None,
        "errors": None,
        "close_fds": None,
    }
    return {
        **core,
        "request_sha256": hashlib.sha256(canon(core)).hexdigest(),
    }


class SubprocessFinalAuthorizerAdapterTests(unittest.TestCase):
    def authorizer(self, grant_provider):
        return make_authorizer(
            mission_id="m1",
            capsule_head_sha256="c" * 64,
            action_ref_prefix="root3-subprocess",
            repo_root=".",
            grant_provider=grant_provider,
        )

    def test_tampered_mediator_request_denies_before_grant_provider(self):
        calls = []
        auth = self.authorizer(lambda req: calls.append(req))
        req = mediator_request()
        req["shell"] = True
        out = auth(req)
        self.assertFalse(out["allowed"])
        self.assertIn("CONTENT_HASH_MISMATCH", out["reason"])
        self.assertEqual(calls, [])

    def test_extra_hashed_field_still_fails_closed(self):
        calls = []
        auth = self.authorizer(lambda req: calls.append(req))
        req = mediator_request()
        req["unexpected"] = "x"
        core = dict(req)
        core.pop("request_sha256")
        req["request_sha256"] = hashlib.sha256(canon(core)).hexdigest()
        out = auth(req)
        self.assertFalse(out["allowed"])
        self.assertIn("FIELD_SET_INVALID", out["reason"])
        self.assertEqual(calls, [])

    def test_grant_provider_exception_fails_closed(self):
        def boom(req):
            raise RuntimeError("no grant")

        out = self.authorizer(boom)(mediator_request())
        self.assertFalse(out["allowed"])
        self.assertIn("RuntimeError:no grant", out["reason"])

    def test_nonfinal_allow_is_rejected(self):
        grants = []

        def provider(req):
            grants.append(req)
            return {"placeholder": True}

        with patch(
            "canonical.runtime.root3_subprocess_final_authorizer_adapter_v1.authorize_effect",
            return_value={"allowed": True, "status": "ALLOW_PRECOMMIT"},
        ):
            out = self.authorizer(provider)(mediator_request())
        self.assertFalse(out["allowed"])
        self.assertIn("FINAL_AUTHORIZATION_DENIED", out["reason"])
        self.assertEqual(len(grants), 1)

    def test_final_allow_returns_content_bound_digest(self):
        seen = {}

        def provider(req):
            seen["request"] = dict(req)
            return {"placeholder": True}

        final = {
            "allowed": True,
            "status": "ALLOW_FINAL_AUTHORIZATION",
            "grant_sha256": "g" * 64,
            "authority_receipt_git_blob_sha": "a" * 40,
            "composition_receipt_git_blob_sha": "b" * 40,
            "authority_proof_digest": "authority-proof",
            "composition_proof_digest": "composition-proof",
        }
        with patch(
            "canonical.runtime.root3_subprocess_final_authorizer_adapter_v1.authorize_effect",
            return_value=final,
        ):
            out = self.authorizer(provider)(mediator_request())

        self.assertTrue(out["allowed"])
        self.assertEqual(len(out["authorization_sha256"]), 64)
        self.assertEqual(
            out["canonical_request_sha256"],
            seen["request"]["request_sha256"],
        )
        self.assertEqual(seen["request"]["effect_kind"], "EXTERNAL_MUTATION")
        self.assertEqual(seen["request"]["resource"], "python:subprocess.run")
        self.assertEqual(seen["request"]["operation"], "invoke")
        self.assertEqual(
            seen["request"]["payload"]["request_sha256"],
            mediator_request()["request_sha256"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

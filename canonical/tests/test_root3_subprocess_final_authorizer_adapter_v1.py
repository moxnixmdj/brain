from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from canonical.runtime.effect_broker_contract_v1 import make_grant
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
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

    def test_real_final_authorizer_remains_denied_with_empty_semantic_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req_holder = {}

            def write_receipt(rel, schema):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                data = (json.dumps({"schema": schema}, sort_keys=True) + "\n").encode()
                path.write_bytes(data)
                return {
                    "path": rel,
                    "git_blob_sha": git_blob_id(data, object_format="sha1"),
                }

            authority_ref = write_receipt("canonical/verification/a.json", "AUTH_UNBOUND_V1")
            composition_ref = write_receipt("canonical/verification/c.json", "COMP_UNBOUND_V1")
            authority_ref.update({
                "scope_complete": True,
                "allow_implies_zero_critical_authority_violation": True,
                "independent_or_objective": True,
            })
            composition_ref.update({
                "scope_complete": True,
                "state_and_provenance_invariants_hold": True,
                "independent_or_objective": True,
            })

            def provider(canonical_request):
                req_holder["request"] = canonical_request
                return make_grant(
                    request=canonical_request,
                    authority_receipt=authority_ref,
                    composition_receipt=composition_ref,
                    max_payload_bytes=100000,
                )

            auth = make_authorizer(
                mission_id="m1",
                capsule_head_sha256="c" * 64,
                action_ref_prefix="root3-subprocess",
                repo_root=root,
                grant_provider=provider,
            )
            out = auth(mediator_request())
            self.assertFalse(out["allowed"])
            self.assertIn("SEMANTIC_VERIFICATION", out["reason"])
            self.assertIn("request", req_holder)

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

"""Bridge Root3 subprocess mediation requests into the canonical final effect authorizer.

This adapter grants no authority by itself. It validates the mediator request,
wraps the exact mediator request as the payload of a canonical proof-carrying
effect request, asks a caller-supplied grant provider for a grant bound to that
exact request, and then calls the canonical final authorizer.

Any malformed input, grant-provider error, non-final verdict, or semantic
verification failure returns DENY. No subprocess is invoked here.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_contract_v1 import make_request
from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect
from canonical.runtime.root3_subprocess_mediator_v1 import SCHEMA as MEDIATOR_SCHEMA

SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_FINAL_AUTHORIZER_ADAPTER_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AdapterError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, label: str, max_len: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > max_len
        or "\x00" in value
    ):
        raise AdapterError(label + "_INVALID")
    return value.strip()


MEDIATOR_REQUEST_KEYS = {
    "schema",
    "api",
    "command",
    "cwd",
    "env",
    "stdin",
    "stdout",
    "stderr",
    "input",
    "shell",
    "text",
    "capture_output",
    "timeout",
    "encoding",
    "errors",
    "close_fds",
    "request_sha256",
}


def verify_mediator_request(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != MEDIATOR_SCHEMA:
        raise AdapterError("MEDIATOR_REQUEST_SCHEMA_INVALID")
    if set(value) != MEDIATOR_REQUEST_KEYS:
        raise AdapterError("MEDIATOR_REQUEST_FIELD_SET_INVALID")
    request_sha = value.get("request_sha256")
    if not isinstance(request_sha, str) or not SHA256_RE.fullmatch(request_sha):
        raise AdapterError("MEDIATOR_REQUEST_SHA256_INVALID")
    core = dict(value)
    core.pop("request_sha256", None)
    if _sha(core) != request_sha:
        raise AdapterError("MEDIATOR_REQUEST_CONTENT_HASH_MISMATCH")
    api = _token(value.get("api"), "MEDIATOR_API", 128)
    if api not in {"subprocess.run", "subprocess.Popen"}:
        raise AdapterError("MEDIATOR_API_UNSUPPORTED")
    return dict(value)


def make_authorizer(
    *,
    mission_id: str,
    capsule_head_sha256: str,
    action_ref_prefix: str,
    repo_root: str | Path,
    grant_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    mission = _token(mission_id, "MISSION_ID", 256)
    head = _token(capsule_head_sha256, "CAPSULE_HEAD_SHA256", 64)
    if not SHA256_RE.fullmatch(head):
        raise AdapterError("CAPSULE_HEAD_SHA256_INVALID")
    prefix = _token(action_ref_prefix, "ACTION_REF_PREFIX", 256)
    if not callable(grant_provider):
        raise AdapterError("GRANT_PROVIDER_NOT_CALLABLE")
    root = str(Path(repo_root))

    def authorize_process(mediator_request: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            mreq = verify_mediator_request(mediator_request)
            canonical_request = make_request(
                mission_id=mission,
                capsule_head_sha256=head,
                action_ref=prefix + ":" + mreq["request_sha256"][:16],
                effect_kind="EXTERNAL_MUTATION",
                resource="python:" + mreq["api"],
                operation="invoke",
                payload=mreq,
            )
            grant = grant_provider(canonical_request)
            if not isinstance(grant, Mapping):
                raise AdapterError("GRANT_PROVIDER_RESULT_INVALID")
            verdict = authorize_effect(
                canonical_request,
                grant,
                repo_root=root,
            )
            if (
                not isinstance(verdict, Mapping)
                or verdict.get("allowed") is not True
                or verdict.get("status") != "ALLOW_FINAL_AUTHORIZATION"
            ):
                return {
                    "schema": SCHEMA,
                    "allowed": False,
                    "reason": "FINAL_AUTHORIZATION_DENIED:"
                    + str(
                        verdict.get("failed_stage")
                        or verdict.get("reason")
                        or verdict.get("status")
                        or "UNKNOWN"
                    ),
                    "acceptance_credit_delta": 0,
                }
            proof = {
                "schema": SCHEMA,
                "mediator_request_sha256": mreq["request_sha256"],
                "canonical_request_sha256": canonical_request["request_sha256"],
                "final_grant_sha256": verdict.get("grant_sha256"),
                "authority_receipt_git_blob_sha": verdict.get(
                    "authority_receipt_git_blob_sha"
                ),
                "composition_receipt_git_blob_sha": verdict.get(
                    "composition_receipt_git_blob_sha"
                ),
                "authority_proof_digest": verdict.get("authority_proof_digest"),
                "composition_proof_digest": verdict.get(
                    "composition_proof_digest"
                ),
            }
            return {
                "schema": SCHEMA,
                "allowed": True,
                "authorization_sha256": _sha(proof),
                "canonical_request_sha256": canonical_request["request_sha256"],
                "acceptance_credit_delta": 0,
            }
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "allowed": False,
                "reason": type(exc).__name__ + ":" + str(exc),
                "acceptance_credit_delta": 0,
            }

    return authorize_process

"""Semantic authorizer for the currently closed Root3 read-only process class.

Only exact current READ_ONLY_DECLARED_QUERY mediator requests may be authorized.
The authorization is additionally bound to the independently verified read-only
executor, namespace substrate, effect registry, callsite classifier, mediator,
and adapter bytes. All other process classes fail closed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace
from canonical.runtime import root3_subprocess_effect_class_registry_v1 as registry
from canonical.runtime import root3_subprocess_callsite_classifier_v1 as classifier
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_subprocess_final_authorizer_adapter_v2 as adapter

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_PROCESS_AUTHORIZER_V1"
POLICY_ID = "ROOT3_READ_ONLY_DECLARED_QUERY_CURRENT_V1"
EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"

EXPECTED_BLOBS = {
    "read_only_executor": "74166a80c47ed8ddce7bae7b61a3a3610ac2ef8a",
    "namespace_launcher": "6e687527e9c4da82fb5d974a729aaa263ee73ea8",
    "effect_registry": "24e00a3e6b70d0879cab664a8512f243973c6196",
    "callsite_classifier": "e654b264096dba724d82f04e5adef0dc6d6c90f7",
    "mediator": "80560cdfa91c11a4b47b9ee2161af726b2f9bccf",
    "adapter": "14182a4a5112c7d585cdcac68f2eca1dfcf6c17d",
}


def _git_blob_sha(path: str) -> str:
    raw = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _current_blobs() -> dict[str, str]:
    return {
        "read_only_executor": _git_blob_sha(read_only.__file__),
        "namespace_launcher": _git_blob_sha(namespace.__file__),
        "effect_registry": _git_blob_sha(registry.__file__),
        "callsite_classifier": _git_blob_sha(classifier.__file__),
        "mediator": _git_blob_sha(mediator.__file__),
        "adapter": _git_blob_sha(adapter.__file__),
    }


def _sha(value: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def make_authorizer():
    def authorize(request: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            checked = adapter.verify_mediator_request(request)
            current = _current_blobs()
            if current != EXPECTED_BLOBS:
                return {
                    "schema": SCHEMA,
                    "allowed": False,
                    "reason": "READ_ONLY_AUTHORITY_BOUND_BLOB_DRIFT",
                    "acceptance_credit_delta": 0,
                }
            callsite = checked["callsite"]
            if callsite.get("effect_class") != EFFECT_CLASS:
                return {
                    "schema": SCHEMA,
                    "allowed": False,
                    "reason": "EFFECT_CLASS_NOT_READ_ONLY_DECLARED_QUERY",
                    "acceptance_credit_delta": 0,
                }
            key = (
                str(callsite.get("module_path")),
                int(callsite.get("lineno")),
                str(callsite.get("process_api")),
            )
            if key not in read_only.SUPPORTED:
                return {
                    "schema": SCHEMA,
                    "allowed": False,
                    "reason": "READ_ONLY_CALLSITE_NOT_IN_VERIFIED_EXECUTOR_SET",
                    "acceptance_credit_delta": 0,
                }
            proof = {
                "schema": SCHEMA,
                "policy_id": POLICY_ID,
                "mediator_request_sha256": checked["request_sha256"],
                "effect_class": EFFECT_CLASS,
                "callsite": list(key),
                "bound_blobs": current,
                "zero_material_effect_executor": True,
            }
            return {
                "schema": SCHEMA,
                "allowed": True,
                "authorization_sha256": _sha(proof),
                "policy_id": POLICY_ID,
                "effect_class": EFFECT_CLASS,
                "acceptance_credit_delta": 0,
            }
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "allowed": False,
                "reason": type(exc).__name__ + ":" + str(exc),
                "acceptance_credit_delta": 0,
            }
    return authorize

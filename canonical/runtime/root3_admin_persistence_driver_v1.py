from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_typed_durable_admin_write_v1 as durable

DRIVER_ID = "ASTRA_ADMIN_PERSISTENCE_V1"
CONTRACT_PATH = (
    "canonical/governance/"
    "ROOT3_ADMIN_PERSISTENCE_DRIVER_CONTRACT_20261007_V1.json"
)
IMPLEMENTATION_PATH = "canonical/runtime/root3_admin_persistence_driver_v1.py"

_REQUIRED_FIELDS = {
    "destination_class",
    "operation",
    "path",
    "expected_pre_sha256",
    "payload_b64",
}


class AdminPersistenceDriverError(RuntimeError):
    pass


def _decode_payload(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise AdminPersistenceDriverError("PAYLOAD_B64_INVALID")
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise AdminPersistenceDriverError("PAYLOAD_B64_INVALID") from exc
    if not raw:
        raise AdminPersistenceDriverError("PAYLOAD_EMPTY")
    return raw


def execute(repo_root: str, typed_args: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(typed_args, Mapping):
        raise AdminPersistenceDriverError("TYPED_ARGS_NOT_OBJECT")
    if set(typed_args) != _REQUIRED_FIELDS:
        raise AdminPersistenceDriverError("TYPED_ARGS_FIELDS_INVALID")

    destination_class = str(typed_args["destination_class"])
    operation = str(typed_args["operation"])
    path = str(typed_args["path"])
    expected_pre = str(typed_args["expected_pre_sha256"])
    payload = _decode_payload(typed_args["payload_b64"])

    plan = durable.build_plan(
        operation=operation,
        destination_class=destination_class,
        path=path,
        payload=payload,
        expected_pre_sha256=expected_pre,
    )
    receipt = durable.commit(repo_root, plan, payload)
    return {
        "driver_id": DRIVER_ID,
        "status": "COMMITTED",
        "plan_sha256": receipt["plan_sha256"],
        "operation": receipt["operation"],
        "destination_class": receipt["destination_class"],
        "path": receipt["path"],
        "pre_sha256": receipt["pre_sha256"],
        "payload_sha256": receipt["payload_sha256"],
        "post_sha256": receipt["post_sha256"],
        "post_bytes": receipt["post_bytes"],
        "atomic_replace": receipt["atomic_replace"],
        "compare_and_append": receipt["compare_and_append"],
        "acceptance_credit_delta": 0,
    }

from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any


CAPSULE_SCHEMA = "PROJECT_BRAIN_JSON_VALUE_CAPSULE_V1"


class JsonValueCapsuleError(ValueError):
    pass


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(value: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise JsonValueCapsuleError("INVALID_BASE64") from exc


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _encode_json_value(value: Any, active: set[int]) -> dict[str, Any]:
    if value is None:
        return {"t": "null"}

    if isinstance(value, bool):
        return {"t": "bool", "v": value}

    if isinstance(value, int):
        return {"t": "int", "v": str(value)}

    if isinstance(value, float):
        if not math.isfinite(value):
            raise JsonValueCapsuleError("NON_JSON_FLOAT")
        return {"t": "float", "hex": value.hex()}

    if isinstance(value, str):
        return {"t": "str", "utf8_b64": _b64encode(value.encode("utf-8"))}

    if isinstance(value, (list, dict)):
        object_id = id(value)
        if object_id in active:
            raise JsonValueCapsuleError("CYCLIC_VALUE_NOT_JSON")
        active.add(object_id)
        try:
            if isinstance(value, list):
                return {
                    "t": "array",
                    "items": [_encode_json_value(item, active) for item in value],
                }

            entries: list[list[Any]] = []
            for key, item in value.items():
                if not isinstance(key, str):
                    raise JsonValueCapsuleError("JSON_OBJECT_KEY_MUST_BE_STRING")
                entries.append(
                    [
                        _b64encode(key.encode("utf-8")),
                        _encode_json_value(item, active),
                    ]
                )
            return {"t": "object", "entries": entries}
        finally:
            active.remove(object_id)

    raise JsonValueCapsuleError(
        f"UNSUPPORTED_NON_JSON_VALUE_TYPE {type(value).__name__}"
    )


def encode_json_value(value: Any) -> dict[str, Any]:
    """Losslessly encode one finite acyclic JSON-semantic value.

    Scalar type is explicit, object field presence is preserved, object entry order is
    preserved, arrays preserve order, strings preserve exact UTF-8 code points, integers
    preserve arbitrary precision, and finite floats preserve their exact binary64 value.
    """

    return _encode_json_value(value, set())


def decode_json_value(node: dict[str, Any]) -> Any:
    tag = node.get("t")

    if tag == "null":
        return None
    if tag == "bool":
        return bool(node["v"])
    if tag == "int":
        return int(node["v"])
    if tag == "float":
        value = float.fromhex(node["hex"])
        if not math.isfinite(value):
            raise JsonValueCapsuleError("NON_JSON_FLOAT")
        return value
    if tag == "str":
        try:
            return _b64decode(node["utf8_b64"]).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise JsonValueCapsuleError("INVALID_UTF8_STRING") from exc
    if tag == "array":
        return [decode_json_value(item) for item in node["items"]]
    if tag == "object":
        result: dict[str, Any] = {}
        for encoded_key, encoded_value in node["entries"]:
            try:
                key = _b64decode(encoded_key).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise JsonValueCapsuleError("INVALID_UTF8_OBJECT_KEY") from exc
            if key in result:
                raise JsonValueCapsuleError("DUPLICATE_OBJECT_KEY_IN_CAPSULE")
            result[key] = decode_json_value(encoded_value)
        return result

    raise JsonValueCapsuleError(f"UNKNOWN_VALUE_TAG {tag!r}")


def make_capsule(
    value: Any,
    *,
    schema_path: str,
    actor: str,
    channel: str,
    raw_wire_bytes: bytes | None = None,
) -> dict[str, Any]:
    if not schema_path:
        raise JsonValueCapsuleError("EMPTY_SCHEMA_PATH")
    if not actor:
        raise JsonValueCapsuleError("EMPTY_ACTOR")
    if not channel:
        raise JsonValueCapsuleError("EMPTY_CHANNEL")

    body: dict[str, Any] = {
        "schema": CAPSULE_SCHEMA,
        "schema_path": schema_path,
        "actor": actor,
        "channel": channel,
        "value": encode_json_value(value),
    }

    if raw_wire_bytes is not None:
        body["raw_wire_b64"] = _b64encode(raw_wire_bytes)
        body["raw_wire_sha256"] = hashlib.sha256(raw_wire_bytes).hexdigest()

    body["capsule_sha256"] = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
    return body


def verify_and_decode_capsule(capsule: dict[str, Any]) -> Any:
    if capsule.get("schema") != CAPSULE_SCHEMA:
        raise JsonValueCapsuleError("WRONG_CAPSULE_SCHEMA")

    unsigned = dict(capsule)
    claimed_hash = unsigned.pop("capsule_sha256", None)
    if not isinstance(claimed_hash, str):
        raise JsonValueCapsuleError("MISSING_CAPSULE_HASH")

    actual_hash = hashlib.sha256(_canonical_json_bytes(unsigned)).hexdigest()
    if actual_hash != claimed_hash:
        raise JsonValueCapsuleError(
            f"CAPSULE_HASH_MISMATCH {actual_hash} != {claimed_hash}"
        )

    raw_b64 = unsigned.get("raw_wire_b64")
    raw_sha = unsigned.get("raw_wire_sha256")
    if (raw_b64 is None) != (raw_sha is None):
        raise JsonValueCapsuleError("PARTIAL_RAW_WIRE_BINDING")
    if raw_b64 is not None:
        raw = _b64decode(raw_b64)
        actual_raw_sha = hashlib.sha256(raw).hexdigest()
        if actual_raw_sha != raw_sha:
            raise JsonValueCapsuleError(
                f"RAW_WIRE_HASH_MISMATCH {actual_raw_sha} != {raw_sha}"
            )

    for required in ("schema_path", "actor", "channel", "value"):
        if required not in unsigned:
            raise JsonValueCapsuleError(f"MISSING_FIELD {required}")

    return decode_json_value(unsigned["value"])

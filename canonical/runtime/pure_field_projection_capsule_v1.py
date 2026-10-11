"""Deterministic semantic capsule for pure field-scoped zero-reality work.

The capsule combines:
- exact RFC-6901 projections from declared authority documents; and
- a statically restricted pure consumer that can observe only that projection.

Its semantic identity is intentionally independent of undeclared fields in the
source documents. Any declared field change or consumer-source change changes
the capsule identity. It grants no execution, promotion, acceptance, capability,
ownership, fresh-reality, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.pure_projection_consumer_guard_v1 import (
    evaluate_pure_consumer,
)
from canonical.runtime.sealed_field_projection_consumer_v1 import (
    prepare_projection_bundle,
)

SCHEMA = "PROJECT_BRAIN_PURE_FIELD_PROJECTION_CAPSULE_V1"


class PureFieldProjectionCapsuleError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compile_capsule(
    *,
    source_documents: Mapping[str, Mapping[str, Any]],
    field_dependencies: Mapping[str, Sequence[str]],
    consumer_source: str,
) -> dict[str, Any]:
    """Compile one zero-authority semantic capsule from exact projected inputs."""
    try:
        bundle = prepare_projection_bundle(
            source_documents=source_documents,
            field_dependencies=field_dependencies,
        )
        consumer = evaluate_pure_consumer(
            source=consumer_source,
            projection=bundle,
        )
        if consumer.get("pass") is not True:
            raise PureFieldProjectionCapsuleError(
                "PURE_CONSUMER_FAILED:" + str(consumer.get("error") or "")
            )

        selected_sources = []
        for row in bundle["sources"]:
            manifest = row["dependency_manifest"]
            selected_sources.append(
                {
                    "source_path": row["source_path"],
                    "manifest_sha256": manifest["manifest_sha256"],
                    "projection_sha256": manifest["projection_sha256"],
                    "dependencies": [
                        {
                            "pointer": dep["pointer"],
                            "value_sha256": dep["value_sha256"],
                        }
                        for dep in manifest["dependencies"]
                    ],
                }
            )

        result = consumer["consumer_result"]
        result_bytes = _canon(result)
        semantic_core = {
            "schema": SCHEMA,
            "projection_bundle_sha256": bundle["projection_bundle_sha256"],
            "consumer_source_sha256": consumer["consumer_source_sha256"],
            "consumer_result_sha256": _sha256(result_bytes),
            "selected_sources": selected_sources,
            "consumer_result": result,
        }
        semantic_identity = _sha256(_canon(semantic_core))

        return {
            **semantic_core,
            "semantic_identity_sha256": semantic_identity,
            "source_count": bundle["source_count"],
            "selected_field_count": sum(
                len(row["dependencies"]) for row in selected_sources
            ),
            "consumer_static_verification": consumer["static_verification"],
            "ambient_repository_access_available": False,
            "filesystem_access_available": False,
            "network_access_available": False,
            "process_access_available": False,
            "undeclared_source_fields_material_to_identity": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "rule": (
                "CAPSULE_IDENTITY_IS_A_FUNCTION_ONLY_OF_DECLARED_FIELD_VALUES_"
                "AND_THE_VERIFIED_PURE_CONSUMER__UNDECLARED_SAME_FILE_CHURN_"
                "CANNOT_CHANGE_THE_SEMANTIC_IDENTITY"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "error": type(exc).__name__ + ":" + str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }


def semantic_equivalent(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    """Exact semantic-identity equality only; malformed capsules never match."""
    a = left.get("semantic_identity_sha256") if isinstance(left, Mapping) else None
    b = right.get("semantic_identity_sha256") if isinstance(right, Mapping) else None
    return (
        isinstance(a, str)
        and len(a) == 64
        and isinstance(b, str)
        and len(b) == 64
        and a == b
    )

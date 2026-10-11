"""Compose the pure projection guard with the sealed field projection runner.

A qualifying consumer must satisfy both properties:
1. its source belongs to the statically verified pure projection subset; and
2. it executes from exactly one consumer file plus the sealed projection and runner.

No helper files are accepted. This prevents a verified pure entrypoint from
delegating to an unverified helper inside the sealed input tree.

This module grants zero execution, promotion, acceptance, capability, ownership,
fresh-reality, or terminal authority.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.pure_projection_consumer_guard_v1 import (
    PureProjectionConsumerError,
    verify_source,
)
from canonical.runtime.sealed_field_projection_consumer_v1 import (
    SealedFieldProjectionError,
    run_sealed_consumer,
)
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined

SCHEMA = "PROJECT_BRAIN_PURE_SEALED_PROJECTION_CONSUMER_V1"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        **extra,
    }


def run_pure_sealed_consumer(
    *,
    source_documents: Mapping[str, Mapping[str, Any]],
    field_dependencies: Mapping[str, Sequence[str]],
    consumer_source: str,
    consumer_module: str = "consumer.py",
    launcher: Callable[[Mapping[str, Any]], Mapping[str, Any]] = run_confined,
    limits: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    try:
        static = verify_source(consumer_source)
        if "evaluate" not in static["local_call_graph"]:
            raise PureProjectionConsumerError("EVALUATE_ENTRY_REQUIRED")

        sealed = run_sealed_consumer(
            source_documents=source_documents,
            field_dependencies=field_dependencies,
            consumer_files={consumer_module: consumer_source},
            consumer_module=consumer_module,
            consumer_entrypoint="evaluate",
            launcher=launcher,
            limits=limits,
        )
        if sealed.get("pass") is not True:
            raise SealedFieldProjectionError(
                "SEALED_EXECUTION_FAILED:" + str(sealed.get("error"))
            )

        # With helper files forbidden, the sealed tree must contain exactly:
        # projection JSON, generated runner, and the one verified consumer.
        if sealed.get("closed_world_input_entry_count") != 3:
            raise SealedFieldProjectionError(
                "UNEXPECTED_SEALED_INPUT_ENTRY_COUNT:"
                + str(sealed.get("closed_world_input_entry_count"))
            )

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__PURE_AND_SEALED_FIELD_PROJECTION_CONSUMER",
            "consumer_source_sha256": static["consumer_source_sha256"],
            "static_guard_status": static["status"],
            "projection_bundle_sha256": sealed["projection_bundle_sha256"],
            "closed_world_input_manifest_sha256": sealed[
                "closed_world_input_manifest_sha256"
            ],
            "closed_world_input_entry_count": sealed[
                "closed_world_input_entry_count"
            ],
            "launcher_policy_sha256": sealed.get("launcher_policy_sha256"),
            "consumer_result": sealed["consumer_result"],
            "imports_allowed": False,
            "attribute_access_allowed": False,
            "ambient_io_calls_allowed": False,
            "helper_files_allowed": False,
            "undeclared_host_repository_reads_available": False,
            "network_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "rule": (
                "LIVE_FIELD_SCOPED_REUSE_REQUIRES_BOTH_STATIC_PURITY_AND_"
                "PHYSICAL_CLOSED_WORLD_SEALING"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

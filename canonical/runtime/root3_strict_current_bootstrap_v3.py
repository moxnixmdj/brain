"""Strict production-capable Root3 bootstrap V3 over whole-runtime registry.

Only the two effect classes with verified confined executors are bound.
All other current classes, including all newly discovered default-deny sites,
are unbound and therefore denied before child execution.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v3 as mediator
from canonical.runtime import root3_subprocess_callsite_classifier_v2 as classifier
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_transform
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import CLASSES

SCHEMA = "PROJECT_BRAIN_ROOT3_STRICT_CURRENT_BOOTSTRAP_V3"
BOUND_EFFECT_CLASSES = frozenset({
    "READ_ONLY_DECLARED_QUERY",
    "TEMPORARY_FILESYSTEM_TRANSFORM",
})
DENIED_EFFECT_CLASSES = frozenset(CLASSES - BOUND_EFFECT_CLASSES)


class BootstrapV3Error(RuntimeError):
    pass


def install_current(
    authorizer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    authority_id: str,
) -> dict[str, Any]:
    reg = classifier.registry_status()
    if int(reg.get("registry_site_count", 0)) <= 18:
        raise BootstrapV3Error("WHOLE_RUNTIME_REGISTRY_NOT_ACTIVE")
    if not reg.get("registry_sha256"):
        raise BootstrapV3Error("REGISTRY_SHA256_MISSING")

    executors = {
        "READ_ONLY_DECLARED_QUERY": read_only.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
        "TEMPORARY_FILESYSTEM_TRANSFORM": temp_transform.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
    }
    status = mediator.install(
        authorizer,
        authority_id=authority_id,
        class_executors=executors,
    )
    bound = frozenset(status.get("bound_effect_class_executors") or [])
    unbound = frozenset(status.get("unbound_effect_classes") or [])
    if bound != BOUND_EFFECT_CLASSES:
        raise BootstrapV3Error("BOUND_EFFECT_CLASS_SET_MISMATCH")
    if unbound != DENIED_EFFECT_CLASSES:
        raise BootstrapV3Error("UNBOUND_EFFECT_CLASS_SET_MISMATCH")
    if (
        status.get("run_guard_active") is not True
        or status.get("popen_guard_active") is not True
    ):
        raise BootstrapV3Error("GLOBAL_SUBPROCESS_GUARD_NOT_ACTIVE")
    if (status.get("registry") or {}).get("registry_sha256") != reg["registry_sha256"]:
        raise BootstrapV3Error("MEDIATOR_REGISTRY_BINDING_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "INSTALLED_FAIL_CLOSED_BEFORE_CREDITED_RUNTIME_IMPORT",
        "process_site_count": reg["registry_site_count"],
        "registry_sha256": reg["registry_sha256"],
        "bound_effect_classes": sorted(bound),
        "denied_effect_classes": sorted(unbound),
        "run_guard_active": True,
        "popen_guard_active": True,
        "authority_widening": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }

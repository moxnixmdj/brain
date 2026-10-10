"""Strict current Root3 subprocess bootstrap V2.

Binds every effect class that already has a current independently verified class
executor. All other classes remain unbound and therefore deny before child
execution in root3_subprocess_mediator_v2.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_transform
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import CLASSES, EXPECTED

SCHEMA="PROJECT_BRAIN_ROOT3_STRICT_CURRENT_BOOTSTRAP_V2"
CURRENT_PROCESS_SITE_COUNT=18
BOUND_EFFECT_CLASSES=frozenset({
    "READ_ONLY_DECLARED_QUERY",
    "TEMPORARY_FILESYSTEM_TRANSFORM",
})
DENIED_EFFECT_CLASSES=frozenset(CLASSES-BOUND_EFFECT_CLASSES)

class BootstrapError(RuntimeError):
    pass

def install_current(
    authorizer: Callable[[Mapping[str,Any]],Mapping[str,Any]],
    *,
    authority_id: str,
)->dict[str,Any]:
    if len(EXPECTED)!=CURRENT_PROCESS_SITE_COUNT:
        raise BootstrapError(
            "PROCESS_UNIVERSE_DRIFT:"+str(len(EXPECTED))+"!="+str(CURRENT_PROCESS_SITE_COUNT)
        )
    executors={
        "READ_ONLY_DECLARED_QUERY": read_only.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
        "TEMPORARY_FILESYSTEM_TRANSFORM": temp_transform.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
    }
    status=mediator.install(
        authorizer,
        authority_id=authority_id,
        class_executors=executors,
    )
    bound=frozenset(status.get("bound_effect_class_executors") or [])
    unbound=frozenset(status.get("unbound_effect_classes") or [])
    if bound!=BOUND_EFFECT_CLASSES:
        raise BootstrapError("BOUND_EFFECT_CLASS_SET_MISMATCH")
    if unbound!=DENIED_EFFECT_CLASSES:
        raise BootstrapError("UNBOUND_EFFECT_CLASS_SET_MISMATCH")
    if status.get("run_guard_active") is not True or status.get("popen_guard_active") is not True:
        raise BootstrapError("GLOBAL_SUBPROCESS_GUARD_NOT_ACTIVE")
    return {
        "schema":SCHEMA,
        "status":"INSTALLED_FAIL_CLOSED",
        "process_site_count":CURRENT_PROCESS_SITE_COUNT,
        "bound_effect_classes":sorted(bound),
        "denied_effect_classes":sorted(unbound),
        "run_guard_active":True,
        "popen_guard_active":True,
        "read_only_executor":"canonical/runtime/root3_read_only_local_file_query_executor_v1.py",
        "temporary_transform_executor":"canonical/runtime/root3_pdf_raster_temp_executor_v1.py",
        "namespace_backend":"canonical/runtime/zero_ambient_namespace_launcher_v1.py",
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }

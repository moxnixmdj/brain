"""Strict current Root3 subprocess bootstrap V3.

Extends the verified V2 bootstrap with the bound codec child channel:
READ_ONLY_DECLARED_QUERY and TEMPORARY_FILESYSTEM_TRANSFORM mappings keep
their exact semantics while callsite identity and provenance now re-pin to
the V2 live registry compilation (semantic-twin narrowed where verified),
and BOUND_CHILD_CODE_EXECUTION is bound for the content-bound codec probe
profiles via root3_bound_codec_child_executor_v1.

All other classes stay unbound and deny before child execution in
root3_subprocess_mediator_v2.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_transform
from canonical.runtime import root3_bound_codec_child_executor_v1 as codec_child
from canonical.runtime import root3_confined_shell_executor_v1 as confined_shell
from canonical.runtime.root3_subprocess_effect_class_registry_v2 import (
    CLASSES,
    ROOT,
    compile_effect_classes,
)

SCHEMA = "PROJECT_BRAIN_ROOT3_STRICT_CURRENT_BOOTSTRAP_V3"
BOUND_EFFECT_CLASSES = frozenset({
    "READ_ONLY_DECLARED_QUERY",
    "TEMPORARY_FILESYSTEM_TRANSFORM",
    "BOUND_CHILD_CODE_EXECUTION",
    "ARBITRARY_COMMAND_EXECUTION",
})
DENIED_EFFECT_CLASSES = frozenset(CLASSES - BOUND_EFFECT_CLASSES)


class BootstrapError(RuntimeError):
    pass


def install_current(
    authorizer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    authority_id: str,
) -> dict[str, Any]:
    registry = compile_effect_classes(ROOT)
    if registry["status"].startswith("PASS__") is not True:
        raise BootstrapError("PROCESS_EFFECT_CLASS_REGISTRY_NOT_PASS")
    executors = {
        "READ_ONLY_DECLARED_QUERY": read_only.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
        "TEMPORARY_FILESYSTEM_TRANSFORM": temp_transform.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
        "BOUND_CHILD_CODE_EXECUTION": codec_child.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
        "ARBITRARY_COMMAND_EXECUTION": confined_shell.make_executor(
            popen_impl=mediator._ORIGINAL_POPEN
        ),
    }
    status = mediator.install(
        authorizer,
        authority_id=authority_id,
        class_executors=executors,
    )
    bound = frozenset(status.get("bound_effect_class_executors") or [])
    if bound != BOUND_EFFECT_CLASSES:
        raise BootstrapError(
            "EFFECT_CLASS_EXECUTOR_BINDING_MISMATCH:"
            + ",".join(sorted(BOUND_EFFECT_CLASSES ^ bound))
        )
    return status

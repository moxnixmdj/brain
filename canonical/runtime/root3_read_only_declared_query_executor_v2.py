from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as local_file
from canonical.runtime import root3_read_only_package_metadata_executor_v1 as package_metadata

EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"

_OVERLAP = set(local_file.SUPPORTED) & set(package_metadata.SUPPORTED)
if _OVERLAP:
    raise RuntimeError("READ_ONLY_EXECUTOR_ROUTE_OVERLAP:" + repr(sorted(_OVERLAP)))

SUPPORTED = {**local_file.SUPPORTED, **package_metadata.SUPPORTED}

class ReadOnlyDeclaredQueryDenied(PermissionError):
    pass

def _key(context: Mapping[str, Any]) -> tuple[str, int, str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise ReadOnlyDeclaredQueryDenied("EFFECT_CLASS_MISMATCH")
    cs = context.get("callsite")
    if not isinstance(cs, Mapping):
        raise ReadOnlyDeclaredQueryDenied("CALLSITE_MISSING")
    return (
        str(cs.get("module_path") or ""),
        int(cs.get("lineno") or 0),
        str(cs.get("process_api") or ""),
    )

def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")
    local_exec = local_file.make_executor(popen_impl=popen_impl)
    package_exec = package_metadata.make_executor(popen_impl=popen_impl)

    def execute(context: Mapping[str, Any]) -> Any:
        key = _key(context)
        if key in local_file.SUPPORTED:
            return local_exec(context)
        if key in package_metadata.SUPPORTED:
            return package_exec(context)
        raise ReadOnlyDeclaredQueryDenied(
            "READ_ONLY_DECLARED_QUERY_CALLSITE_NOT_SUPPORTED:" + repr(key)
        )

    return execute

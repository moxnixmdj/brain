from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

SCHEMA="PROJECT_BRAIN_ROOT3_PARENT_DRIVER_REGISTRY_V1"
KINDS=("PING","EXTERNAL_TOOL","DURABLE_ADMIN_WRITE")

class ParentDriverRegistryError(RuntimeError):
    pass

def validate_registry(drivers:Mapping[str,Callable[...,Any]])->dict[str,Any]:
    if not isinstance(drivers,Mapping):
        raise ParentDriverRegistryError("DRIVERS_NOT_MAPPING")
    keys=tuple(sorted(str(x) for x in drivers))
    expected=tuple(sorted(KINDS))
    if keys!=expected:
        missing=sorted(set(expected)-set(keys))
        extra=sorted(set(keys)-set(expected))
        raise ParentDriverRegistryError(
            "DRIVER_KIND_SET_MISMATCH:missing="+",".join(missing)+";extra="+",".join(extra)
        )
    if any(not callable(drivers[k]) for k in KINDS):
        raise ParentDriverRegistryError("DRIVER_NOT_CALLABLE")
    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_THREE_PARENT_DRIVER_CLASSES",
        "kinds":list(KINDS),
        "driver_count":3,
        "terminal_credit_delta":0,
    }

def dispatch(
    drivers:Mapping[str,Callable[[Mapping[str,Any]],Mapping[str,Any]]],
    kind:str,
    payload:Mapping[str,Any],
)->dict[str,Any]:
    validate_registry(drivers)
    name=str(kind or "")
    if name not in KINDS:
        raise ParentDriverRegistryError("BROKER_KIND_DENIED:"+name)
    if not isinstance(payload,Mapping):
        raise ParentDriverRegistryError("BROKER_PAYLOAD_INVALID")
    out=drivers[name](payload)
    if not isinstance(out,Mapping):
        raise ParentDriverRegistryError("DRIVER_RESULT_NOT_MAPPING:"+name)
    return dict(out)

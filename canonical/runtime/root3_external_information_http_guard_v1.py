from __future__ import annotations

from typing import Any


class ExternalInformationHTTPGuardError(RuntimeError):
    pass


_ALLOWED_METHODS = frozenset({"GET", "HEAD"})


def _request_shape(request: Any) -> tuple[str, bool]:
    # Match urllib.request.Request semantics without importing or replacing
    # transport objects here. Plain string URLs are GET with no body.
    get_method = getattr(request, "get_method", None)
    if callable(get_method):
        method = str(get_method()).upper()
        data = getattr(request, "data", None)
    else:
        method = "GET"
        data = None
    return method, data is not None


def validate_information_request(request: Any) -> None:
    method, has_body = _request_shape(request)
    if method not in _ALLOWED_METHODS:
        raise ExternalInformationHTTPGuardError(
            "EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:" + method
        )
    if has_body:
        raise ExternalInformationHTTPGuardError(
            "EXTERNAL_INFORMATION_HTTP_BODY_FORBIDDEN"
        )


def install(astra: Any) -> dict[str, Any]:
    original = getattr(astra, "_bridge_aware_urlopen", None)
    if not callable(original):
        raise ExternalInformationHTTPGuardError(
            "ASTRA_BRIDGE_AWARE_URLOPEN_MISSING"
        )

    if getattr(original, "_project_brain_information_guard_v1", False):
        return {
            "status": "ALREADY_INSTALLED",
            "allowed_methods": sorted(_ALLOWED_METHODS),
            "request_body_allowed": False,
        }

    def guarded(request: Any, timeout: float = 20, *args: Any, **kwargs: Any):
        validate_information_request(request)
        return original(request, timeout, *args, **kwargs)

    guarded._project_brain_information_guard_v1 = True
    guarded.__name__ = getattr(original, "__name__", "_bridge_aware_urlopen")
    guarded.__doc__ = getattr(original, "__doc__", None)

    astra._bridge_aware_urlopen = guarded

    # Astra's activation function rebinds urllib.request.urlopen from the
    # module-level _bridge_aware_urlopen symbol. Activate once now and future
    # activations will continue to install this guarded function.
    activate = getattr(astra, "_activate_external_http_bridge", None)
    if not callable(activate):
        raise ExternalInformationHTTPGuardError(
            "ASTRA_HTTP_BRIDGE_ACTIVATOR_MISSING"
        )
    activate()

    urllib_mod = getattr(astra, "urllib", None)
    request_mod = getattr(urllib_mod, "request", None)
    if request_mod is None or getattr(request_mod, "urlopen", None) is not guarded:
        raise ExternalInformationHTTPGuardError(
            "ASTRA_HTTP_GUARD_NOT_ACTIVE"
        )

    return {
        "status": "PASS__PRODUCTION_INFORMATION_HTTP_GUARD_ACTIVE",
        "allowed_methods": sorted(_ALLOWED_METHODS),
        "request_body_allowed": False,
    }

"""Strict product-native web application operations for OSWorld 2.1.

Requests are issued through Playwright's BrowserContext.request object, which
shares the live benchmark Chrome context's cookie jar. The policy can select only
frozen app/operation pairs from the adjacent registry. Generic /api/state,
arbitrary URLs, raw JavaScript, raw Python, and raw shell are not exposed.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote, urlsplit

REGISTRY_PATH = Path(__file__).with_name("osworld_v21_web_app_ops_registry_v1.json")
MAX_ERROR = 3000
MAX_RESULT = 120000
MAX_DEPTH = 8
MAX_ARGS_BYTES = 100000
PROTECTED_PATHS = (
    "/evaluation_examples",
    "/benchmark_releases",
    "/root",
    "/proc",
    "/sys",
    "/dev",
    "/run/secrets",
)


class WebAppOpsError(RuntimeError):
    pass


def _registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    apps = raw.get("apps")
    if not isinstance(apps, dict) or not apps:
        raise WebAppOpsError("WEB_APP_REGISTRY_INVALID")
    return raw


def _validate_data(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise WebAppOpsError("WEB_APP_ARGUMENT_DEPTH_EXCEEDED")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if len(value) > 40000:
            raise WebAppOpsError("WEB_APP_STRING_TOO_LONG")
        if value.startswith("/"):
            p = str(Path(value))
            if any(p == x or p.startswith(x + "/") for x in PROTECTED_PATHS):
                raise WebAppOpsError("WEB_APP_PROTECTED_PATH")
        return
    if isinstance(value, list):
        if len(value) > 512:
            raise WebAppOpsError("WEB_APP_LIST_TOO_LONG")
        for item in value:
            _validate_data(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 128 or any(not isinstance(k, str) or not k for k in value):
            raise WebAppOpsError("WEB_APP_OBJECT_INVALID")
        for item in value.values():
            _validate_data(item, depth + 1)
        return
    raise WebAppOpsError("WEB_APP_ARGUMENT_TYPE_UNSUPPORTED")


@dataclass
class OSWorldHostWebAppOps:
    remote_debugging_url: str | None = None

    def bind_environment(self, environment: Any) -> None:
        vm_ip = getattr(environment, "vm_ip", None)
        port = getattr(environment, "chromium_port", None)
        if not vm_ip or port is None:
            raise WebAppOpsError("DESKTOP_ENV_CDP_ENDPOINT_MISSING")
        self.remote_debugging_url = f"http://{vm_ip}:{int(port)}"

    def _connect(self):
        if not self.remote_debugging_url:
            raise WebAppOpsError("WEB_APP_ENVIRONMENT_NOT_BOUND")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise WebAppOpsError("PLAYWRIGHT_UNAVAILABLE") from exc
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(self.remote_debugging_url)
        except Exception as exc:
            pw.stop()
            raise WebAppOpsError(
                "CDP_CONNECT_FAILED:" + type(exc).__name__ + ":" + str(exc)[:MAX_ERROR]
            ) from exc
        return pw, browser

    @staticmethod
    def _select_page(browser: Any, hints: list[str]):
        if not browser.contexts:
            raise WebAppOpsError("NO_BROWSER_CONTEXT")
        pages = browser.contexts[0].pages
        if not pages:
            raise WebAppOpsError("NO_BROWSER_PAGE")
        wanted = [str(x).casefold() for x in hints if isinstance(x, str) and x]
        matches = [p for p in pages if any(h in str(p.url).casefold() for h in wanted)]
        if not matches:
            raise WebAppOpsError("WEB_APP_PAGE_NOT_FOUND")
        return matches[-1]

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise WebAppOpsError("WEB_APP_OP_NOT_OBJECT")
        if set(payload) - {"app", "operation", "args"}:
            raise WebAppOpsError("WEB_APP_OP_UNSUPPORTED_FIELDS")

        app = str(payload.get("app") or "").strip()
        operation = str(payload.get("operation") or "").strip()
        args = payload.get("args", {})
        if not isinstance(args, dict):
            raise WebAppOpsError("WEB_APP_ARGS_NOT_OBJECT")
        _validate_data(args)
        if len(json.dumps(args, ensure_ascii=False).encode("utf-8")) > MAX_ARGS_BYTES:
            raise WebAppOpsError("WEB_APP_ARGUMENTS_TOO_LARGE")

        registry = _registry()
        app_spec = registry["apps"].get(app)
        if not isinstance(app_spec, dict):
            raise WebAppOpsError("WEB_APP_NOT_ALLOWED:" + app)
        op_spec = (app_spec.get("operations") or {}).get(operation)
        if not isinstance(op_spec, dict):
            raise WebAppOpsError("WEB_APP_OPERATION_NOT_ALLOWED:" + app + ":" + operation)

        required = list(op_spec.get("required") or [])
        optional = list(op_spec.get("optional") or [])
        allowed = set(required) | set(optional)
        missing = [name for name in required if name not in args]
        extra = sorted(set(args) - allowed)
        if missing:
            raise WebAppOpsError("WEB_APP_REQUIRED_ARGUMENT_MISSING:" + ",".join(sorted(missing)))
        if extra:
            raise WebAppOpsError("WEB_APP_ARGUMENT_NOT_ALLOWED:" + ",".join(extra))

        path = str(op_spec.get("path") or "")
        for name in op_spec.get("path_params") or []:
            value = args.get(name)
            if not isinstance(value, str) or not value or "/" in value or ".." in value:
                raise WebAppOpsError("WEB_APP_PATH_ARGUMENT_INVALID:" + str(name))
            path = path.replace("{" + str(name) + "}", quote(value, safe="-_.~"))
        if "{" in path or "}" in path or not path.startswith("/api/"):
            raise WebAppOpsError("WEB_APP_PATH_INVALID")
        if path == "/api/state" or path.startswith("/api/state/"):
            raise WebAppOpsError("CONTROL_PLANE_STATE_FORBIDDEN")

        body_mode = str(op_spec.get("body_mode") or "")
        path_params = set(op_spec.get("path_params") or [])
        body = None
        if body_mode == "none":
            body = None
        elif body_mode == "fields":
            body = {k: v for k, v in args.items() if k not in path_params}
        elif body_mode == "object_arg":
            name = str(op_spec.get("body_arg") or "")
            value = args.get(name)
            if not isinstance(value, dict):
                raise WebAppOpsError("WEB_APP_BODY_OBJECT_REQUIRED:" + name)
            body = value
        else:
            raise WebAppOpsError("WEB_APP_BODY_MODE_INVALID")

        method = str(op_spec.get("method") or "").upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise WebAppOpsError("WEB_APP_METHOD_INVALID")

        pw, browser = self._connect()
        try:
            page = self._select_page(browser, list(app_spec.get("url_hints") or []))
            parsed = urlsplit(page.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise WebAppOpsError("WEB_APP_ORIGIN_INVALID")
            origin = parsed.scheme + "://" + parsed.netloc
            url = origin + path
            context = browser.contexts[0]
            kwargs: dict[str, Any] = {"method": method, "timeout": 30000}
            if body is not None:
                kwargs["data"] = body
                kwargs["headers"] = {"Content-Type": "application/json"}
            response = context.request.fetch(url, **kwargs)
            raw = response.text()
            if not response.ok:
                raise WebAppOpsError(
                    "WEB_APP_HTTP_FAILED:"
                    + str(response.status)
                    + ":"
                    + raw[:MAX_ERROR]
                )
            try:
                result = response.json()
            except Exception:
                result = {"text": raw[:MAX_RESULT]}
            encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"), default=str)
            if len(encoded) > MAX_RESULT:
                result = {
                    "truncated": True,
                    "json_prefix": encoded[:MAX_RESULT],
                    "original_chars": len(encoded),
                }
            return {
                "type": "WEB_APP_OP",
                "ok": True,
                "app": app,
                "operation": operation,
                "method": method,
                "path": path,
                "origin": origin,
                "result": result,
            }
        except WebAppOpsError:
            raise
        except Exception as exc:
            raise WebAppOpsError(
                "WEB_APP_EXECUTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:MAX_ERROR]
            ) from exc
        finally:
            # CDP-attached benchmark Chrome must remain alive.
            pw.stop()

"""Typed host-to-guest application operations for OSWorld 2.1.

Only app/method pairs frozen in osworld_v21_app_ops_registry_v1.json are callable.
Arguments are serialized as data; raw Python, shell, task source and evaluator
paths are not exposed to the policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

REGISTRY_PATH = Path(__file__).with_name("osworld_v21_app_ops_registry_v1.json")
MAX_ARGS_BYTES = 20000
MAX_OUTPUT = 8000
MAX_ERROR = 3000
MAX_DEPTH = 6
PROTECTED = (
    "/evaluation_examples",
    "/benchmark_releases",
    "/root",
    "/proc",
    "/sys",
    "/dev",
    "/run/secrets",
)


class AppOpsError(RuntimeError):
    pass


def _registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    apps = raw.get("apps")
    if not isinstance(apps, dict) or not apps:
        raise AppOpsError("APP_OP_REGISTRY_INVALID")
    return raw


def _validate_data(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise AppOpsError("APP_OP_ARGUMENT_DEPTH_EXCEEDED")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if len(value) > 10000:
            raise AppOpsError("APP_OP_STRING_TOO_LONG")
        if value.startswith("/"):
            normalized = str(Path(value))
            if any(normalized == p or normalized.startswith(p + "/") for p in PROTECTED):
                raise AppOpsError("APP_OP_PROTECTED_PATH")
        return
    if isinstance(value, list):
        if len(value) > 256:
            raise AppOpsError("APP_OP_LIST_TOO_LONG")
        for item in value:
            _validate_data(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 64 or any(not isinstance(k, str) or not k for k in value):
            raise AppOpsError("APP_OP_OBJECT_INVALID")
        for item in value.values():
            _validate_data(item, depth + 1)
        return
    raise AppOpsError("APP_OP_ARGUMENT_TYPE_UNSUPPORTED")


@dataclass
class OSWorldHostAppOps:
    environment: Any | None = None

    def bind_environment(self, environment: Any) -> None:
        controller = getattr(environment, "controller", None)
        if controller is None or not callable(getattr(controller, "execute_python_command", None)):
            raise AppOpsError("DESKTOP_ENV_PYTHON_CONTROLLER_MISSING")
        self.environment = environment

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.environment is None:
            raise AppOpsError("APP_ENVIRONMENT_NOT_BOUND")
        if not isinstance(payload, Mapping):
            raise AppOpsError("APP_OP_NOT_OBJECT")

        app = str(payload.get("app") or "").strip()
        operation = str(payload.get("operation") or "").strip()
        args = payload.get("args", {})
        if not isinstance(args, dict):
            raise AppOpsError("APP_OP_ARGS_NOT_OBJECT")
        _validate_data(args)

        registry = _registry()
        app_spec = registry["apps"].get(app)
        if not isinstance(app_spec, dict):
            raise AppOpsError("APP_NOT_ALLOWED:" + app)
        op_spec = (app_spec.get("operations") or {}).get(operation)
        if not isinstance(op_spec, dict):
            raise AppOpsError("APP_OPERATION_NOT_ALLOWED:" + app + ":" + operation)

        required = op_spec.get("required") or []
        missing = [name for name in required if name not in args]
        if missing:
            raise AppOpsError("APP_OP_REQUIRED_ARGUMENT_MISSING:" + ",".join(sorted(missing)))
        if any(not isinstance(k, str) or not k.isidentifier() for k in args):
            raise AppOpsError("APP_OP_ARGUMENT_NAME_INVALID")

        args_json = json.dumps(args, ensure_ascii=False, separators=(",", ":"))
        if len(args_json.encode("utf-8")) > MAX_ARGS_BYTES:
            raise AppOpsError("APP_OP_ARGUMENTS_TOO_LARGE")

        cls = str(app_spec.get("class_name") or "")
        if not cls.isidentifier() or not operation.isidentifier() or not app.isidentifier():
            raise AppOpsError("APP_OP_IDENTIFIER_INVALID")

        # repr() makes the JSON blob data, never executable source supplied by policy.
        program = (
            "import json; "
            f"from {app} import *; "
            f"_a=json.loads({args_json!r}); "
            f"_r={cls}.{operation}(**_a); "
            "print(json.dumps({'result':_r},ensure_ascii=False,default=str))"
        )

        try:
            result = self.environment.controller.execute_python_command(program)
        except Exception as exc:
            raise AppOpsError(
                "APP_OP_EXECUTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:MAX_ERROR]
            ) from exc
        if not isinstance(result, Mapping):
            raise AppOpsError("APP_OP_NO_RECEIPT")
        status = str(result.get("status") or "").strip().lower()
        error = result.get("error")
        if error or status in {"error", "failed", "failure"}:
            raise AppOpsError("APP_OP_EXECUTION_FAILED:" + str(error or status)[:MAX_ERROR])
        output = str(result.get("output") or "")
        return {
            "type": "APP_OP",
            "ok": True,
            "app": app,
            "operation": operation,
            "status": status or "ok",
            "output": output[:MAX_OUTPUT],
        }

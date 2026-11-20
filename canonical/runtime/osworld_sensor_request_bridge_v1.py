"""Admit a computed sensor request into OSWorld-compatible guest state ops.

This is an adapter, not a fork. Three OSWorld kernels in this tree are byte-pinned by verification
receipts (`osworld_v21_state_ops_v1`, `osworld_v21_host_guest_ops_v1`,
`osworld_v21_brain_agent_adapter_v1`), so none is edited here. The existing adapter already accepts
an injected `guest_controller`; this module supplies one that can compile one additional read-only
assertion while delegating every ordinary state op to the pinned bridge unchanged.

The assertion's field and value may come only from a fresh re-measurement of the external sensor
request store. A policy cannot supply or override them. A stale store, a changed field, a bad path
or a wrong observed value fails closed before or during real guest execution.

Authority: NONE__PRODUCER_RUN_SANDBOX. A benchmark-compatible harness integration, not a
benchmark result, capability credit or independent verification of the agent.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Any, Mapping, Sequence

from canonical.runtime.osworld_v21_host_guest_ops_v1 import GuestOpsError, OSWorldHostGuestOps
from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError, _path
from canonical.tools import a_sensor_request_is_computable_v1 as SR

SCHEMA = "BRAIN_OSWORLD_SENSOR_REQUEST_BRIDGE_V1"
DEFAULT_STORE = pathlib.Path("canonical/state/SENSOR_REQUEST_STORE_20261120_V1.json")
SENSOR_OP = "ASSERT_SENSOR_REQUEST"
OP_FIELDS = frozenset({"type", "path"})
MAX_OUTPUT = 8000
MAX_ERROR = 4000


class AdmissionError(RuntimeError):
    """The store or the request failed the fresh-execution admission check."""


def load_relation(store: pathlib.Path | None = None) -> dict[str, Any]:
    """Read the external store. No value here is trusted until `readmit` runs."""
    source = pathlib.Path(store) if store is not None else DEFAULT_STORE
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AdmissionError("SENSOR_STORE_UNREADABLE:" + type(exc).__name__) from exc
    if data.get("schema") != "BRAIN_SENSOR_REQUEST_STORE_V1":
        raise AdmissionError("SENSOR_STORE_SCHEMA_MISMATCH")
    if data.get("removable") is not True or data.get("parameters") != 0 or data.get("model_calls") != 0:
        raise AdmissionError("SENSOR_STORE_NOT_EXTERNAL_OR_NOT_MODEL_FREE")
    relation = data.get("learned_relation")
    if not isinstance(relation, Mapping):
        raise AdmissionError("SENSOR_RELATION_MISSING")
    out = dict(relation)
    if out.get("kind") != "new_path_field_value":
        raise AdmissionError("SENSOR_RELATION_KIND_UNSUPPORTED")
    field = out.get("field")
    value = out.get("value")
    if field not in SR.FIELDS or isinstance(value, bool) or not isinstance(value, int):
        raise AdmissionError("SENSOR_RELATION_FIELD_OR_VALUE_INVALID")
    return out


def readmit(store: pathlib.Path | None = None) -> dict[str, Any]:
    """Re-compute the request on a fresh real machine; never trust the stored row alone."""
    claimed = load_relation(store)
    with tempfile.TemporaryDirectory(prefix="brain-sensor-readmit-") as temporary:
        report = SR.measure(pathlib.Path(temporary) / "readmit")
    if report.get("met") is not True:
        raise AdmissionError("FRESH_SENSOR_MEASUREMENT_FAILED")
    fresh = report.get("sensor_request")
    if not isinstance(fresh, Mapping):
        raise AdmissionError("FRESH_SENSOR_REQUEST_MISSING")
    if {k: fresh.get(k) for k in ("kind", "field", "value")} != {
            k: claimed.get(k) for k in ("kind", "field", "value")}:
        raise AdmissionError("STORED_REQUEST_DISAGREES_WITH_FRESH_EXECUTION")
    return claimed


def compile_assertion(op: Mapping[str, Any], relation: Mapping[str, Any]) -> str:
    """Compile one read-only stat-field assertion from an already admitted relation."""
    if not isinstance(op, Mapping):
        raise StateOpsError("SENSOR_OP_NOT_OBJECT")
    extra = set(op) - OP_FIELDS
    if extra:
        raise StateOpsError("SENSOR_OP_FIELD_NOT_ALLOWED:" + sorted(extra)[0])
    path = _path(op.get("path"))
    field = str(relation["field"])
    value = int(relation["value"])
    if field not in SR.FIELDS:
        raise StateOpsError("SENSOR_FIELD_NOT_AVAILABLE")
    return (
        "import pathlib; "
        f"_p=pathlib.Path({path!r}); "
        f"assert _p.exists(), 'SENSOR_PATH_MISSING:{field}'; "
        f"_v=getattr(_p.lstat(), {field!r}); "
        f"assert _v == {value!r}, 'SENSOR_VALUE_MISMATCH:{field}:'+str(_v); "
        f"print('SENSOR_REQUEST:PASS:{field}:'+str(_v))"
    )


class AdmittedSensorGuestOps:
    """Drop-in guest controller for the existing BrainOSWorldAgent injection point."""

    def __init__(self, store: pathlib.Path | None = None,
                 delegate: OSWorldHostGuestOps | None = None) -> None:
        self.store = pathlib.Path(store) if store is not None else pathlib.Path(DEFAULT_STORE)
        self.delegate = delegate if delegate is not None else OSWorldHostGuestOps()
        self.environment: Any | None = None

    def bind_environment(self, environment: Any) -> None:
        controller = getattr(environment, "controller", None)
        if controller is None or not callable(getattr(controller, "execute_python_command", None)):
            raise GuestOpsError("DESKTOP_ENV_PYTHON_CONTROLLER_MISSING")
        self.environment = environment
        binder = getattr(self.delegate, "bind_environment", None)
        if callable(binder):
            binder(environment)

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.environment is None:
            raise GuestOpsError("GUEST_ENVIRONMENT_NOT_BOUND")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("ops"), Sequence):
            raise StateOpsError("PAYLOAD_NOT_OBJECT")
        ops = list(payload["ops"])
        if any(not isinstance(op, Mapping) for op in ops):
            raise StateOpsError("OP_NOT_OBJECT")
        sensor_ops = [op for op in ops if str(op.get("type") or "").strip().upper() == SENSOR_OP]
        ordinary = [op for op in ops if op not in sensor_ops]
        if not sensor_ops:
            return self.delegate.run(payload)
        if len(sensor_ops) != 1:
            raise StateOpsError("ONE_SENSOR_ASSERTION_PER_PAYLOAD")

        relation = readmit(self.store)
        program = compile_assertion(sensor_ops[0], relation)
        output = ""
        if ordinary:
            prior = self.delegate.run({"ops": ordinary})
            output += str(prior.get("output") or "")
        try:
            result = self.environment.controller.execute_python_command(program)
        except Exception as exc:
            raise GuestOpsError(
                "GUEST_STATE_EXECUTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:MAX_ERROR]
            ) from exc
        if not isinstance(result, Mapping):
            raise GuestOpsError("GUEST_STATE_EXECUTION_NO_RECEIPT")
        status = str(result.get("status") or "").strip().lower()
        error = result.get("error")
        if error or status in {"error", "failed", "failure"}:
            raise GuestOpsError("GUEST_STATE_EXECUTION_FAILED:" + str(error or status)[:MAX_ERROR])
        output += str(result.get("output") or "")
        return {"type": "STATE_OPS", "ok": True, "status": status or "ok",
                "output": output[:MAX_OUTPUT],
                "admission": {"field": relation["field"], "value": relation["value"],
                              "source": "fresh_measurement"}}


def run_with_real_controller(payload: Mapping[str, Any], root: pathlib.Path,
                             store: pathlib.Path | None = None) -> dict[str, Any]:
    """Execute the exact compiled program in this sandbox through a real subprocess."""
    import subprocess
    import sys

    class Controller:
        def execute_python_command(self, program: str) -> dict[str, Any]:
            done = subprocess.run([sys.executable, "-c", program], cwd=str(root),
                                  capture_output=True, text=True, timeout=120)
            return {"status": "success" if done.returncode == 0 else "error",
                    "output": done.stdout,
                    "error": done.stderr or None}

    class Environment:
        controller = Controller()

    bridge = AdmittedSensorGuestOps(store=store)
    bridge.bind_environment(Environment())
    return bridge.run(payload)

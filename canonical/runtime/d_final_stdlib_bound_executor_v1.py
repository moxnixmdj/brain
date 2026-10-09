"""D-final stdlib bound capability executor V1.

A deliberately small promoted-capability execution kernel for registry rows whose
source type is exactly python_stdlib.

It preserves the load-bearing semantics of the existing promoted bound adapter:
- exact verified registry admission
- zero incremental spend
- frozen action-template rendering
- caller-supplied registry/entry/rendered-action pins
- declared stdlib dependency probing
- repository-root-confined adapter loading
- declared expectation enforcement
- independent execution-trace verification

It intentionally does NOT support apt, npm, PyPI, system tools, runtime-native
actions, git source trees, arbitrary subprocesses, or network acquisition.
Those require separate D-final provider theorems.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

from canonical.runtime.bound_capability_execution_verifier_v1 import verify as verify_execution
from canonical.runtime.capability_planner import plan_actions
from canonical.runtime import d_finality_execution_epoch_v1 as d_finality

SCHEMA = "PROJECT_BRAIN_D_FINAL_STDLIB_BOUND_EXECUTOR_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class DFinalStdlibBoundError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _load_registry() -> tuple[bytes, Mapping[str, Any], Mapping[str, Any]]:
    raw = REGISTRY_PATH.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_REGISTRY_CAPABILITIES_INVALID")
    return raw, doc, caps


def _render(value: Any, inputs: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        return {k: _render(v, inputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, inputs) for v in value]
    if isinstance(value, str):
        if value.startswith("${input.") and value.endswith("}") and value.count("${") == 1:
            key = value[len("${input."):-1]
            if key not in inputs:
                raise DFinalStdlibBoundError("BOUND_CAPABILITY_INPUT_MISSING:" + key)
            return inputs[key]
        out = value
        for key, val in inputs.items():
            out = out.replace("${input." + str(key) + "}", str(val))
        if "${input." in out:
            raise DFinalStdlibBoundError("BOUND_CAPABILITY_INPUT_MISSING")
        return out
    return value


def _verify_stdlib_source(source: Mapping[str, Any]) -> dict[str, Any]:
    if source.get("type") != "python_stdlib":
        raise DFinalStdlibBoundError("NON_STDLIB_SOURCE_REJECTED:" + str(source.get("type")))
    raw_modules = source.get("modules")
    if raw_modules is None:
        one = str(source.get("module") or "").strip()
        modules = [one] if one else []
    elif isinstance(raw_modules, list):
        modules = [str(x or "").strip() for x in raw_modules]
    else:
        raise DFinalStdlibBoundError("BOUND_PYTHON_STDLIB_MODULES_INVALID")
    modules = [m for m in modules if m]
    if not modules:
        raise DFinalStdlibBoundError("BOUND_PYTHON_STDLIB_MODULE_REQUIRED")
    if len(modules) != len(set(modules)):
        raise DFinalStdlibBoundError("BOUND_PYTHON_STDLIB_MODULES_DUPLICATE")
    verified: list[str] = []
    for module in modules:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", module):
            raise DFinalStdlibBoundError("BOUND_PYTHON_STDLIB_MODULE_INVALID:" + module)
        try:
            spec = importlib.util.find_spec(module)
        except Exception as exc:
            raise DFinalStdlibBoundError(
                "BOUND_PYTHON_STDLIB_PROBE_FAILED:" + module + ":" + type(exc).__name__
            ) from exc
        if spec is None:
            raise DFinalStdlibBoundError("BOUND_PYTHON_STDLIB_MODULE_MISSING:" + module)
        verified.append(module)
    return {
        "status": "LOCAL_VERIFIED",
        "type": "python_stdlib",
        "modules": verified,
        "python_version": sys.version.split()[0],
    }


def inspect(capability_id: str) -> dict[str, Any]:
    cid = str(capability_id or "").strip()
    if not cid:
        raise DFinalStdlibBoundError("CAPABILITY_ID_REQUIRED")
    raw, _, caps = _load_registry()
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_NONZERO_COST:" + cid)
    source = entry.get("source")
    if not isinstance(source, Mapping):
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_SOURCE_INVALID:" + cid)
    dependency = _verify_stdlib_source(source)
    verification = entry.get("verification")
    if not isinstance(verification, Mapping) or not verification:
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_VERIFICATION_MISSING:" + cid)
    independently_verified = (
        verification.get("independent_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )
    if not independently_verified:
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:" + cid)
    action_template = entry.get("action_template")
    if not isinstance(action_template, Mapping) or action_template.get("type") != "invoke_capability":
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID:" + cid)
    return {
        "capability_id": cid,
        "entry": deepcopy(dict(entry)),
        "registry_file_sha256": sha256(raw).hexdigest(),
        "registry_entry_sha256": _sha(entry),
        "dependency": dependency,
    }


def prepare(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(inputs, Mapping):
        raise DFinalStdlibBoundError("INPUTS_NOT_OBJECT")
    inspected = inspect(capability_id)
    cid = inspected["capability_id"]
    entry = inspected["entry"]
    rendered = _render(entry["action_template"], dict(inputs))
    if not isinstance(rendered, Mapping) or rendered.get("type") != "invoke_capability":
        raise DFinalStdlibBoundError("RENDERED_BOUND_ACTION_INVALID")
    args = rendered.get("args")
    if not isinstance(args, Mapping) or args.get("capability_id") != cid:
        raise DFinalStdlibBoundError("RENDERED_BOUND_ACTION_CAPABILITY_ID_MISMATCH")
    iid = str(instance_id or cid).strip()
    if not iid:
        raise DFinalStdlibBoundError("INSTANCE_ID_INVALID")
    req = list(entry.get("requires") or []) if requires is None else list(requires)
    prov = list(entry.get("provides") or []) if provides is None else list(provides)
    fields = list(entry.get("result_fields") or []) if result_fields is None else list(result_fields)
    if not prov:
        raise DFinalStdlibBoundError("INSTANCE_PROVIDES_EMPTY")
    return {
        "schema": SCHEMA,
        "status": "PREPARED__D_FINAL_STDLIB_BOUND_CAPABILITY",
        "capability_id": cid,
        "instance_id": iid,
        "requires": req,
        "provides": prov,
        "result_fields": fields,
        "inputs": deepcopy(dict(inputs)),
        "inputs_sha256": _sha(inputs),
        "registry_file_sha256": inspected["registry_file_sha256"],
        "registry_entry_sha256": inspected["registry_entry_sha256"],
        "rendered_action": deepcopy(dict(rendered)),
        "rendered_action_sha256": _sha(rendered),
        "dependency": deepcopy(inspected["dependency"]),
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "terminal_authority": False,
    }


def _load_adapter(entry: Mapping[str, Any]):
    module_name = str(entry.get("adapter_module") or "")
    if not module_name or any(
        ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        for ch in module_name
    ):
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_ADAPTER_INVALID")
    path = ROOT / "canonical/runtime/bound_capabilities" / (module_name + ".py")
    if not path.is_file():
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_ADAPTER_MISSING")
    runtime_name = "project_brain_d_final_bound_" + module_name
    if d_finality.has_active_epoch():
        d_finality.require_material_file_if_active(path, repo_root=ROOT)
        raw = path.read_bytes()
        rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
        expected = dict(d_finality.current_epoch().material_bindings).get(rel)
        if expected is None or d_finality.git_blob_sha_bytes(raw) != expected:
            raise DFinalStdlibBoundError(
                "BOUND_CAPABILITY_ADAPTER_CHANGED_AFTER_EPOCH_CHECK:" + rel
            )
        module = type(sys)(runtime_name)
        module.__file__ = str(path)
        module.__package__ = ""
        sys.modules[runtime_name] = module
        exec(compile(raw, str(path), "exec"), module.__dict__)
    else:
        spec = importlib.util.spec_from_file_location(runtime_name, path)
        if spec is None or spec.loader is None:
            raise DFinalStdlibBoundError("BOUND_CAPABILITY_ADAPTER_LOAD_FAILED")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
    if not callable(fn):
        raise DFinalStdlibBoundError("BOUND_CAPABILITY_ENTRYPOINT_MISSING")
    return fn


def _verify_expectation(action: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    expect = action.get("expect")
    if expect is None:
        return
    if not isinstance(expect, Mapping):
        raise DFinalStdlibBoundError("ACTION_EXPECTATION_INVALID")
    field = str(expect.get("field") or "").strip()
    if not field:
        raise DFinalStdlibBoundError("ACTION_EXPECTATION_FIELD_REQUIRED")
    value = result.get(field)
    typ = expect.get("type", "field_nonempty")
    if typ == "field_nonempty":
        ok = value not in (None, "", [], {})
    elif typ == "field_contains":
        ok = str(expect.get("value", "")) in str(value or "")
    elif typ == "field_equals":
        ok = value == expect.get("value")
    else:
        raise DFinalStdlibBoundError("ACTION_EXPECTATION_TYPE_UNKNOWN:" + str(typ))
    if not ok:
        raise DFinalStdlibBoundError("ACTION_EXPECTATION_FAILED:" + field)


def execute(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
    expected_registry_file_sha256: str | None = None,
    expected_registry_entry_sha256: str | None = None,
    expected_rendered_action_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        prepared = prepare(
            capability_id,
            inputs=inputs,
            instance_id=instance_id,
            requires=requires,
            provides=provides,
            result_fields=result_fields,
        )
        inspected = inspect(prepared["capability_id"])
        if inspected["registry_file_sha256"] != prepared["registry_file_sha256"]:
            raise DFinalStdlibBoundError("REGISTRY_FILE_CHANGED_AFTER_PREPARATION")
        if inspected["registry_entry_sha256"] != prepared["registry_entry_sha256"]:
            raise DFinalStdlibBoundError("REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION")
        entry = inspected["entry"]
        if (
            expected_registry_file_sha256 is not None
            and prepared["registry_file_sha256"] != expected_registry_file_sha256
        ):
            raise DFinalStdlibBoundError("REGISTRY_FILE_CHANGED_AFTER_PREPARATION")
        if (
            expected_registry_entry_sha256 is not None
            and prepared["registry_entry_sha256"] != expected_registry_entry_sha256
        ):
            raise DFinalStdlibBoundError("REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION")
        if (
            expected_rendered_action_sha256 is not None
            and prepared["rendered_action_sha256"] != expected_rendered_action_sha256
        ):
            raise DFinalStdlibBoundError("RENDERED_ACTION_CHANGED_AFTER_PREPARATION")

        rendered = prepared["rendered_action"]
        args = dict(rendered["args"])
        args.pop("capability_id", None)
        fn = _load_adapter(entry)
        result = fn(args, ROOT)
        if not isinstance(result, Mapping):
            raise DFinalStdlibBoundError("BOUND_CAPABILITY_RESULT_INVALID")
        result = dict(result)
        result.setdefault("capability_id", prepared["capability_id"])
        result["dependency"] = deepcopy(prepared["dependency"])
        _verify_expectation(rendered, result)

        iid = prepared["instance_id"]
        req = list(prepared["requires"])
        prov = list(prepared["provides"])
        fields = list(prepared["result_fields"])
        problem = {
            "initial_facts": list(req),
            "target_effects": list(prov),
            "capabilities": [{
                "id": iid,
                "requires": list(req),
                "provides": list(prov),
                "cost": float(entry.get("cost", 1)),
                "action": deepcopy(dict(rendered)),
                "result_fields": fields,
            }],
            "finish_summary": "verified D-final stdlib bound capability execution",
        }
        planned = plan_actions(problem)
        actions = planned["actions"]
        if len(actions) != 2:
            raise DFinalStdlibBoundError("SINGLE_CAPABILITY_PLAN_ACTION_COUNT_INVALID")
        execution = {
            "trace": [
                {"cycle": 0, "plan": deepcopy(actions[0]), "result": deepcopy(result)},
                {
                    "cycle": 1,
                    "plan": deepcopy(actions[1]),
                    "result": {"summary": "verified D-final stdlib bound capability execution"},
                },
            ]
        }
        verdict = verify_execution({"problem": problem}, {"execution": execution})
        if verdict.get("pass") is not True:
            raise DFinalStdlibBoundError(
                "BOUND_CAPABILITY_EXECUTION_TRACE_NOT_VERIFIED:" + str(verdict.get("reason"))
            )
        return {
            "schema": SCHEMA,
            "status": "PASS__D_FINAL_STDLIB_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
            "pass": True,
            "capability_id": prepared["capability_id"],
            "instance_id": iid,
            "requires": req,
            "provides": prov,
            "result_fields": fields,
            "inputs_sha256": prepared["inputs_sha256"],
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "rendered_action": deepcopy(dict(rendered)),
            "result_sha256": _sha(result),
            "result": deepcopy(result),
            "execution_trace": execution,
            "execution_verification": verdict,
            "composition_capsule_head_hash": (
                verdict.get("verified_output") or {}
            ).get("capsule_head_hash"),
            "dependency": deepcopy(prepared["dependency"]),
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "source_class": "python_stdlib",
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

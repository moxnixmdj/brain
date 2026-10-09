"""Minimal D-final executor for promoted python-stdlib bound capabilities.

This is a deliberately narrow ownership route. It executes only already-promoted
BOUND_CAPABILITY_REGISTRY_V1 rows whose declared source type is python_stdlib.

Why it exists:
- the general Astra runtime is a large multi-purpose execution substrate;
- static whole-module closure of that substrate over-approximates many unrelated
  acquisition/planning/dynamic-loader branches;
- D-finality needs the exact operative route, not every dormant branch in a
  monolithic module.

The executor preserves the promoted row's action-template semantics, invokes the
same exact adapter entrypoint, checks the same declared expectation operators,
and rejects any capability outside the active D epoch.

It grants no D-finality by itself. A member certificate must still bind this
executor, the registry row, exact adapter/material closure, substrate contract,
fresh replay, independent replay, donor-zero authority, and zero undeclared
dependencies.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import sysconfig
from typing import Any, Mapping, Sequence

from canonical.runtime import d_finality_execution_epoch_v1 as d_finality

SCHEMA = "PROJECT_BRAIN_D_FINALITY_STDLIB_BOUND_EXECUTOR_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class DStdlibBoundExecutionError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _safe_repo_file(root: Path, rel: str) -> Path:
    raw = str(rel or "").strip()
    p = Path(raw)
    if not raw or p.is_absolute() or ".." in p.parts:
        raise DStdlibBoundExecutionError("NONCANONICAL_PATH:" + raw)
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise DStdlibBoundExecutionError("PATH_OUTSIDE_REPO:" + raw) from exc
    if not full.is_file():
        raise DStdlibBoundExecutionError("FILE_MISSING:" + raw)
    return full


def _load_registry(root: Path) -> tuple[bytes, Mapping[str, Any]]:
    path = _safe_repo_file(root, REGISTRY_REL)
    d_finality.require_material_file_if_active(path, repo_root=root)
    raw = path.read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise DStdlibBoundExecutionError("BOUND_REGISTRY_INVALID_JSON") from exc
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1"
        or not isinstance(doc.get("capabilities"), Mapping)
    ):
        raise DStdlibBoundExecutionError("BOUND_REGISTRY_INVALID")
    return raw, doc["capabilities"]


def _independently_verified(entry: Mapping[str, Any]) -> bool:
    verification = entry.get("verification")
    if not isinstance(verification, Mapping) or not verification:
        return False
    return bool(
        verification.get("independent_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )


def _inspect_entry(
    capability_id: str,
    *,
    repo_root: Path,
) -> tuple[bytes, Mapping[str, Any]]:
    cid = str(capability_id or "").strip()
    if not cid:
        raise DStdlibBoundExecutionError("CAPABILITY_ID_REQUIRED")
    raw, caps = _load_registry(repo_root)
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise DStdlibBoundExecutionError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise DStdlibBoundExecutionError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise DStdlibBoundExecutionError("BOUND_CAPABILITY_NONZERO_COST:" + cid)
    if not _independently_verified(entry):
        raise DStdlibBoundExecutionError(
            "BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:" + cid
        )
    source = entry.get("source")
    if not isinstance(source, Mapping) or source.get("type") != "python_stdlib":
        raise DStdlibBoundExecutionError(
            "D_STDLIB_EXECUTOR_SOURCE_TYPE_FORBIDDEN:"
            + str((source or {}).get("type") if isinstance(source, Mapping) else "")
        )
    template = entry.get("action_template")
    if not isinstance(template, Mapping) or template.get("type") != "invoke_capability":
        raise DStdlibBoundExecutionError("BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID:" + cid)
    return raw, deepcopy(dict(entry))


def _render_template(value: Any, inputs: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        return {k: _render_template(v, inputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_template(v, inputs) for v in value]
    if isinstance(value, str):
        if value.startswith("${input.") and value.endswith("}") and value.count("${") == 1:
            key = value[len("${input."):-1]
            if key not in inputs:
                raise DStdlibBoundExecutionError(
                    "BOUND_CAPABILITY_INPUT_MISSING:" + key
                )
            return deepcopy(inputs[key])
        out = value
        for key, val in inputs.items():
            out = out.replace("${input." + str(key) + "}", str(val))
        if "${input." in out:
            raise DStdlibBoundExecutionError("BOUND_CAPABILITY_INPUT_MISSING")
        return out
    return deepcopy(value)


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _declared_stdlib_modules(source: Mapping[str, Any]) -> list[str]:
    raw_modules = source.get("modules")
    if raw_modules is None:
        one = str(source.get("module") or "").strip()
        modules = [one] if one else []
    elif isinstance(raw_modules, Sequence) and not isinstance(raw_modules, (str, bytes)):
        modules = [str(x or "").strip() for x in raw_modules]
    else:
        raise DStdlibBoundExecutionError("BOUND_PYTHON_STDLIB_MODULES_INVALID")
    modules = [m for m in modules if m]
    if not modules or len(modules) != len(set(modules)):
        raise DStdlibBoundExecutionError("BOUND_PYTHON_STDLIB_MODULES_INVALID")
    return sorted(modules)


def _verified_stdlib_spec(module: str) -> dict[str, str]:
    name = str(module or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name):
        raise DStdlibBoundExecutionError(
            "BOUND_PYTHON_STDLIB_MODULE_INVALID:" + name
        )
    top = name.split(".", 1)[0]
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if not isinstance(stdlib_names, frozenset) or top not in stdlib_names:
        raise DStdlibBoundExecutionError(
            "BOUND_PYTHON_STDLIB_TOPLEVEL_NOT_DECLARED_STDLIB:" + top
        )

    stdlib_root = Path(sysconfig.get_path("stdlib")).resolve()
    excluded = []
    for key in ("purelib", "platlib"):
        raw = sysconfig.get_path(key)
        if raw:
            excluded.append(Path(raw).resolve())

    def check(label: str, spec: Any) -> dict[str, str]:
        if spec is None:
            raise DStdlibBoundExecutionError(
                "BOUND_PYTHON_STDLIB_MODULE_MISSING:" + label
            )
        origin = str(getattr(spec, "origin", None) or "")
        if origin in {"built-in", "frozen"}:
            return {"module": label, "origin": origin, "origin_kind": origin}
        if not origin:
            raise DStdlibBoundExecutionError(
                "BOUND_PYTHON_STDLIB_ORIGIN_MISSING:" + label
            )
        p = Path(origin).resolve()
        if not _path_is_within(p, stdlib_root):
            raise DStdlibBoundExecutionError(
                "BOUND_PYTHON_STDLIB_ORIGIN_OUTSIDE_STDLIB:" + label + ":" + str(p)
            )
        if any(_path_is_within(p, x) for x in excluded):
            raise DStdlibBoundExecutionError(
                "BOUND_PYTHON_STDLIB_ORIGIN_IN_SITE_PACKAGES:" + label + ":" + str(p)
            )
        return {"module": label, "origin": str(p), "origin_kind": "stdlib_file"}

    try:
        top_spec = importlib.util.find_spec(top)
    except Exception as exc:
        raise DStdlibBoundExecutionError(
            "BOUND_PYTHON_STDLIB_TOPLEVEL_PROBE_FAILED:" + top
        ) from exc
    top_binding = check(top, top_spec)
    if name == top:
        return top_binding
    try:
        spec = importlib.util.find_spec(name)
    except Exception as exc:
        raise DStdlibBoundExecutionError(
            "BOUND_PYTHON_STDLIB_PROBE_FAILED:" + name
        ) from exc
    return check(name, spec)


def _verify_substrate_contract(
    source: Mapping[str, Any],
    bindings: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    epoch = d_finality.current_epoch()
    try:
        declared = json.loads(epoch.substrate_contract_canonical_json)
    except Exception as exc:
        raise DStdlibBoundExecutionError(
            "D_SUBSTRATE_CONTRACT_INVALID_CANONICAL_JSON"
        ) from exc
    if not isinstance(declared, Mapping):
        raise DStdlibBoundExecutionError("D_SUBSTRATE_CONTRACT_NOT_OBJECT")
    if declared.get("kind") != "CPYTHON_STDLIB":
        raise DStdlibBoundExecutionError("D_SUBSTRATE_KIND_NOT_CPYTHON_STDLIB")
    if declared.get("implementation") != sys.implementation.name:
        raise DStdlibBoundExecutionError("D_SUBSTRATE_IMPLEMENTATION_MISMATCH")
    actual_version = sys.version.split()[0]
    if declared.get("python_version") != actual_version:
        raise DStdlibBoundExecutionError("D_SUBSTRATE_PYTHON_VERSION_MISMATCH")
    if declared.get("sys_platform") != sys.platform:
        raise DStdlibBoundExecutionError("D_SUBSTRATE_PLATFORM_MISMATCH")
    declared_modules = sorted(str(x) for x in declared.get("stdlib_modules", []))
    actual_modules = _declared_stdlib_modules(source)
    if declared_modules != actual_modules:
        raise DStdlibBoundExecutionError("D_SUBSTRATE_STDLIB_MODULE_SET_MISMATCH")
    return {
        "kind": "CPYTHON_STDLIB",
        "implementation": sys.implementation.name,
        "python_version": actual_version,
        "sys_platform": sys.platform,
        "stdlib_modules": actual_modules,
        "module_bindings": [dict(x) for x in bindings],
    }


def _verify_expectation(action: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    expect = action.get("expect")
    if expect is None:
        return
    if not isinstance(expect, Mapping):
        raise DStdlibBoundExecutionError("ACTION_EXPECTATION_INVALID")
    field = str(expect.get("field") or "").strip()
    if not field:
        raise DStdlibBoundExecutionError("ACTION_EXPECTATION_FIELD_REQUIRED")
    value = result.get(field)
    typ = expect.get("type", "field_nonempty")
    if typ == "field_nonempty":
        ok = value not in (None, "", [], {})
    elif typ == "field_contains":
        ok = str(expect.get("value", "")) in str(value or "")
    elif typ == "field_equals":
        ok = value == expect.get("value")
    else:
        raise DStdlibBoundExecutionError(
            "ACTION_EXPECTATION_TYPE_UNKNOWN:" + str(typ)
        )
    if not ok:
        raise DStdlibBoundExecutionError(
            "ACTION_EXPECTATION_FAILED:" + field + ":" + _canon(value)[:800]
        )


def _adapter_path(entry: Mapping[str, Any], root: Path) -> Path:
    module_name = str(entry.get("adapter_module") or "").strip()
    if not module_name or not re.fullmatch(r"[A-Za-z0-9_]+", module_name):
        raise DStdlibBoundExecutionError("BOUND_CAPABILITY_ADAPTER_INVALID")
    return _safe_repo_file(
        root, "canonical/runtime/bound_capabilities/" + module_name + ".py"
    )


def prepare(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(inputs, Mapping):
        raise DStdlibBoundExecutionError("INPUTS_NOT_OBJECT")
    root = Path(repo_root).resolve()
    raw_registry, entry = _inspect_entry(capability_id, repo_root=root)
    rendered = _render_template(entry["action_template"], dict(inputs))
    if (
        not isinstance(rendered, Mapping)
        or rendered.get("type") != "invoke_capability"
        or not isinstance(rendered.get("args"), Mapping)
        or rendered["args"].get("capability_id") != capability_id
    ):
        raise DStdlibBoundExecutionError("RENDERED_BOUND_ACTION_INVALID")
    adapter = _adapter_path(entry, root)
    return {
        "schema": SCHEMA,
        "status": "PREPARED__D_STDLIB_BOUND_CAPABILITY",
        "capability_id": capability_id,
        "registry_file_sha256": hashlib.sha256(raw_registry).hexdigest(),
        "registry_entry_sha256": _sha(entry),
        "adapter_path": adapter.relative_to(root).as_posix(),
        "adapter_git_blob_sha": _git_blob_sha(adapter),
        "rendered_action": deepcopy(dict(rendered)),
        "rendered_action_sha256": _sha(rendered),
        "inputs_sha256": _sha(inputs),
        "execution_authority": False,
        "ownership_credit_delta": 0,
    }


def execute(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    try:
        if not d_finality.has_active_epoch():
            raise DStdlibBoundExecutionError("ACTIVE_D_EPOCH_REQUIRED")
        d_finality.require_capability("bound:" + str(capability_id or "").strip())

        root = Path(repo_root).resolve()
        prepared = prepare(capability_id, inputs=inputs, repo_root=root)
        _raw_registry, entry = _inspect_entry(capability_id, repo_root=root)
        source = entry["source"]
        modules = _declared_stdlib_modules(source)
        bindings = [_verified_stdlib_spec(module) for module in modules]
        substrate = _verify_substrate_contract(source, bindings)

        adapter = _adapter_path(entry, root)
        d_finality.require_material_file_if_active(adapter, repo_root=root)
        module_name = str(entry.get("adapter_module"))
        spec = importlib.util.spec_from_file_location(
            "project_brain_d_final_stdlib_" + module_name + "_" + prepared["adapter_git_blob_sha"],
            adapter,
        )
        if spec is None or spec.loader is None:
            raise DStdlibBoundExecutionError("BOUND_CAPABILITY_ADAPTER_LOAD_FAILED")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
        if not callable(fn):
            raise DStdlibBoundExecutionError("BOUND_CAPABILITY_ENTRYPOINT_MISSING")

        rendered = prepared["rendered_action"]
        args = dict(rendered["args"])
        args.pop("capability_id", None)
        result = fn(args, root)
        if not isinstance(result, Mapping):
            raise DStdlibBoundExecutionError("BOUND_CAPABILITY_RESULT_INVALID")
        result = deepcopy(dict(result))
        result.setdefault("capability_id", capability_id)
        _verify_expectation(rendered, result)

        return {
            "schema": SCHEMA,
            "status": "PASS__D_FINAL_STDLIB_BOUND_CAPABILITY_EXECUTED",
            "pass": True,
            "capability_id": capability_id,
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "adapter_path": prepared["adapter_path"],
            "adapter_git_blob_sha": prepared["adapter_git_blob_sha"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "inputs_sha256": prepared["inputs_sha256"],
            "result_sha256": _sha(result),
            "result": result,
            "substrate_observation": substrate,
            "epoch_sha256": d_finality.current_epoch().epoch_sha256,
            "donor_capability_calls": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

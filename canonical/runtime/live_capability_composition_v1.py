"""Universal heterogeneous live-capability composition V1.

Compose already-selected live-owned capabilities without inventing semantics.

Each graph node names one exact live capability identity. Payload values may
reference composition inputs or prior node results. Native capability verification
remains authoritative; this layer adds only deterministic dependency/value-flow
and composition-contract checks.

Semantic selection of which capabilities should be used remains R2.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVE_CAPABILITY_COMPOSITION_V1"
MAX_STEPS = 128
MAX_DEPTH = 32
SELF_CAPABILITY_ID = "engine:LIVE_COMPOSITION"


class LiveCompositionError(ValueError):
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


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _step_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise LiveCompositionError("STEP_ID_REQUIRED")
    if "." in text:
        raise LiveCompositionError("STEP_ID_DOT_FORBIDDEN:" + text)
    return text


def _refs(value: Any, *, depth: int = 0) -> list[str]:
    if depth > MAX_DEPTH:
        raise LiveCompositionError("VALUE_NESTING_TOO_DEEP")
    if isinstance(value, Mapping):
        if set(value) == {"$ref"}:
            ref = value.get("$ref")
            if not isinstance(ref, str) or not ref.strip():
                raise LiveCompositionError("REF_INVALID")
            return [ref.strip()]
        out: list[str] = []
        for item in value.values():
            out.extend(_refs(item, depth=depth + 1))
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        out: list[str] = []
        for item in value:
            out.extend(_refs(item, depth=depth + 1))
        return out
    return []


def _lookup(root: Mapping[str, Any], ref: str) -> Any:
    parts = ref.split(".")
    if not parts or parts[0] not in {"inputs", "steps"}:
        raise LiveCompositionError("REF_ROOT_INVALID:" + ref)
    current: Any = root
    for part in parts:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                index = int(part)
            except ValueError as exc:
                raise LiveCompositionError("REF_INDEX_INVALID:" + ref) from exc
            if index < 0 or index >= len(current):
                raise LiveCompositionError("REF_INDEX_OUT_OF_RANGE:" + ref)
            current = current[index]
            continue
        raise LiveCompositionError("REF_UNRESOLVED:" + ref)
    return deepcopy(current)


def _resolve(value: Any, root: Mapping[str, Any], *, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise LiveCompositionError("VALUE_NESTING_TOO_DEEP")
    if isinstance(value, Mapping):
        if set(value) == {"$ref"}:
            return _lookup(root, str(value["$ref"]))
        return {
            str(key): _resolve(item, root, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_resolve(item, root, depth=depth + 1) for item in value]
    return deepcopy(value)


def _ref_dependency(ref: str) -> str | None:
    parts = ref.split(".")
    if len(parts) >= 2 and parts[0] == "steps":
        return parts[1]
    return None


def _topological_order(
    steps: Sequence[Mapping[str, Any]],
) -> tuple[list[str], dict[str, set[str]], int]:
    order_hint: dict[str, int] = {}
    dependencies: dict[str, set[str]] = {}
    cross_step_refs = 0

    for index, raw in enumerate(steps):
        sid = _step_id(raw.get("step_id"))
        if sid in dependencies:
            raise LiveCompositionError("STEP_ID_DUPLICATE:" + sid)
        order_hint[sid] = index

        explicit = raw.get("depends_on") or []
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise LiveCompositionError("STEP_DEPENDS_ON_NOT_SEQUENCE:" + sid)
        deps = {_step_id(x) for x in explicit}

        payload = raw.get("payload")
        if not isinstance(payload, Mapping):
            raise LiveCompositionError("STEP_PAYLOAD_NOT_OBJECT:" + sid)
        for ref in _refs(payload):
            dep = _ref_dependency(ref)
            if dep is not None:
                deps.add(dep)
                cross_step_refs += 1

        dependencies[sid] = deps

    known = set(dependencies)
    for sid, deps in dependencies.items():
        missing = sorted(deps - known)
        if missing:
            raise LiveCompositionError(
                "STEP_DEPENDENCY_UNKNOWN:" + sid + ":" + ",".join(missing)
            )

    remaining = {sid: set(deps) for sid, deps in dependencies.items()}
    ready = sorted(
        [sid for sid, deps in remaining.items() if not deps],
        key=order_hint.__getitem__,
    )
    ordered: list[str] = []
    while ready:
        sid = ready.pop(0)
        ordered.append(sid)
        for other in sorted(remaining, key=order_hint.__getitem__):
            if sid in remaining[other]:
                remaining[other].remove(sid)
                if not remaining[other] and other not in ordered and other not in ready:
                    ready.append(other)
        ready.sort(key=order_hint.__getitem__)

    if len(ordered) != len(steps):
        cycle = sorted(
            [sid for sid, deps in remaining.items() if deps],
            key=order_hint.__getitem__,
        )
        raise LiveCompositionError("COMPOSITION_CYCLE:" + ",".join(cycle))

    return ordered, dependencies, cross_step_refs


def _path(value: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    text = str(path or "").strip()
    if not text:
        return True, value
    current: Any = value
    for part in text.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                index = int(part)
            except ValueError:
                return False, None
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def _verify_expectations(
    step_id: str,
    result: Mapping[str, Any],
    expectations: Any,
) -> list[str]:
    if expectations is None:
        return []
    rows = expectations if isinstance(expectations, list) else [expectations]
    errors: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"EXPECTATION_NOT_OBJECT:{step_id}:{index}")
            continue
        path = str(row.get("path") or "")
        exists, value = _path(result, path)
        if "exists" in row:
            wanted = row.get("exists") is True
            if exists is not wanted:
                errors.append(f"EXPECTATION_EXISTS_FAILED:{step_id}:{index}:{path}")
        if "equals" in row:
            if not exists or value != row.get("equals"):
                errors.append(f"EXPECTATION_EQUALS_FAILED:{step_id}:{index}:{path}")
        if "exists" not in row and "equals" not in row:
            errors.append(f"EXPECTATION_OPERATOR_MISSING:{step_id}:{index}")
    return errors


def _kind(capability_id: str) -> str:
    if ":" not in capability_id:
        return "UNKNOWN"
    return capability_id.split(":", 1)[0].upper()


def execute(
    manifest: Mapping[str, Any],
    *,
    invoke_capability: Callable[[str, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one explicit heterogeneous live-capability DAG fail closed."""
    try:
        if not isinstance(manifest, Mapping):
            raise LiveCompositionError("MANIFEST_NOT_OBJECT")
        if not callable(invoke_capability):
            raise LiveCompositionError("INVOKER_NOT_CALLABLE")

        raw_steps = manifest.get("composition_steps")
        if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
            raise LiveCompositionError("COMPOSITION_STEPS_NOT_SEQUENCE")
        if not raw_steps:
            raise LiveCompositionError("COMPOSITION_STEPS_EMPTY")
        if len(raw_steps) > MAX_STEPS:
            raise LiveCompositionError("COMPOSITION_STEP_LIMIT_EXCEEDED")
        if any(not isinstance(row, Mapping) for row in raw_steps):
            raise LiveCompositionError("COMPOSITION_STEP_NOT_OBJECT")

        inputs = manifest.get("inputs") or {}
        if not isinstance(inputs, Mapping):
            raise LiveCompositionError("COMPOSITION_INPUTS_NOT_OBJECT")
        final_spec = manifest.get("outputs") or {}
        if not isinstance(final_spec, Mapping):
            raise LiveCompositionError("COMPOSITION_OUTPUTS_NOT_OBJECT")

        steps = [deepcopy(dict(row)) for row in raw_steps]
        ordered, dependencies, cross_step_ref_count = _topological_order(steps)
        by_id = {_step_id(row.get("step_id")): row for row in steps}
        root: dict[str, Any] = {
            "inputs": deepcopy(dict(inputs)),
            "steps": {},
        }
        trace: list[dict[str, Any]] = []
        provider_kinds: set[str] = set()
        global_options = dict(options or {})

        for sid in ordered:
            row = by_id[sid]
            capability_id = str(row.get("capability_id") or "").strip()
            if not capability_id:
                raise LiveCompositionError("STEP_CAPABILITY_ID_REQUIRED:" + sid)
            if capability_id == SELF_CAPABILITY_ID:
                raise LiveCompositionError("SELF_COMPOSITION_RECURSION_FORBIDDEN:" + sid)

            payload = _resolve(row["payload"], root)
            if not isinstance(payload, Mapping):
                raise LiveCompositionError("RESOLVED_STEP_PAYLOAD_NOT_OBJECT:" + sid)

            step_options = row.get("options") or {}
            if not isinstance(step_options, Mapping):
                raise LiveCompositionError("STEP_OPTIONS_NOT_OBJECT:" + sid)
            merged_options = dict(global_options)
            merged_options.update(dict(step_options))

            raw = invoke_capability(capability_id, payload, merged_options)
            if not isinstance(raw, Mapping):
                raise LiveCompositionError("STEP_RESULT_NOT_OBJECT:" + sid)
            result = deepcopy(dict(raw))
            root["steps"][sid] = result
            provider_kinds.add(_kind(capability_id))

            expectation_errors = _verify_expectations(
                sid,
                result,
                row.get("expect"),
            )
            step_pass = result.get("pass") is True and not expectation_errors
            trace.append({
                "step_id": sid,
                "capability_id": capability_id,
                "depends_on": sorted(dependencies[sid]),
                "pass": step_pass,
                "status": result.get("status"),
                "result_sha256": _digest(result),
                "expectation_errors": expectation_errors,
            })

            if not step_pass:
                observation = {
                    "pass": False,
                    "status": "FAIL__LIVE_COMPOSITION_STEP",
                    "failure_class": "LIVE_CAPABILITY_COMPOSITION_STEP_FAILURE",
                    "composition_sha256": _digest(manifest),
                    "step_count": len(steps),
                    "executed_step_count": len(trace),
                    "failed_step_id": sid,
                    "failed_capability_id": capability_id,
                    "trace": deepcopy(trace),
                }
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__LIVE_COMPOSITION_STEP",
                    "pass": False,
                    "composition_id": str(manifest.get("composition_id") or ""),
                    "composition_sha256": observation["composition_sha256"],
                    "failed_step_id": sid,
                    "failed_capability_id": capability_id,
                    "trace": trace,
                    "step_results": deepcopy(root["steps"]),
                    "expectation_errors": expectation_errors,
                    "cross_step_value_flow_count": cross_step_ref_count,
                    "provider_kind_count": len(provider_kinds),
                    "learning_observation": observation,
                    "semantic_selection_authority": False,
                    "terminal_authority": False,
                    "terminal_credit_delta": 0,
                }

        final_outputs = _resolve(final_spec, root)
        composition_sha = _digest(manifest)
        observation = {
            "pass": True,
            "status": "PASS__LIVE_CAPABILITY_COMPOSITION_EXECUTED",
            "composition_sha256": composition_sha,
            "step_count": len(steps),
            "executed_step_count": len(trace),
            "cross_step_value_flow_count": cross_step_ref_count,
            "provider_kind_count": len(provider_kinds),
            "trace": deepcopy(trace),
            "final_outputs_sha256": _digest(final_outputs),
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__LIVE_CAPABILITY_COMPOSITION_EXECUTED",
            "pass": True,
            "composition_id": str(manifest.get("composition_id") or ""),
            "composition_sha256": composition_sha,
            "execution_order": ordered,
            "trace": trace,
            "step_results": deepcopy(root["steps"]),
            "outputs": final_outputs,
            "cross_step_value_flow_count": cross_step_ref_count,
            "provider_kind_count": len(provider_kinds),
            "learning_observation": observation,
            "native_step_verification_preserved": True,
            "semantic_selection_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__LIVE_COMPOSITION",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_selection_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

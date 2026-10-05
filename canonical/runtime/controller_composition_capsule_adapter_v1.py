"""Fail-closed capsule-v2 adapter for deterministic capability-plan execution.

Scope is intentionally narrow: controller action plans produced by Brain's
deterministic capability graph. Within that scope, all cross-cycle values must
flow through explicit $result references and the capsule is the authoritative
state carrier. Durable result artifacts are rebound to their current contents
on every verification.

This module does not claim that unrelated controller modes use the capsule.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import pathlib
import sys
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_CONTROLLER_COMPOSITION_CAPSULE_ADAPTER_V1"
PRODUCER_REF = "astra_runtime.model_independent_capability_controller"
_DURABLE_RESULT_PATH_FIELDS = (
    "output_path",
    "screenshot_path",
    "xlsx_path",
    "result_path",
    "manifest_path",
    "decision_path",
)


class ControllerCapsuleError(RuntimeError):
    pass


def _load_capsule_v2(root: pathlib.Path):
    path = root / "canonical" / "runtime" / "composition_state_capsule_v2.py"
    if not path.is_file():
        raise ControllerCapsuleError("CAPSULE_V2_MODULE_MISSING")
    name = "project_brain_controller_composition_capsule_v2"
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ControllerCapsuleError("CAPSULE_V2_MODULE_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_repo_path(root: pathlib.Path, raw: str) -> pathlib.Path:
    value = str(raw or "").strip()
    if not value:
        raise ControllerCapsuleError("DURABLE_PATH_EMPTY")
    candidate = (root / value).resolve()
    resolved_root = root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ControllerCapsuleError("DURABLE_PATH_ESCAPES_REPO:" + value) from exc
    return candidate


def result_key(cycle: int) -> str:
    cycle = int(cycle)
    if cycle < 0:
        raise ControllerCapsuleError("RESULT_CYCLE_INVALID")
    return "controller.cycle.%d.result" % cycle


def empty_capsule(root: pathlib.Path) -> dict[str, Any]:
    return _load_capsule_v2(root).empty_capsule()


def _collect_result_refs(value: Any) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if set(item) == {"$result"}:
                spec = item["$result"]
                if not isinstance(spec, Mapping):
                    raise ControllerCapsuleError("RESULT_REFERENCE_INVALID")
                try:
                    cycle = int(spec.get("cycle", -1))
                except Exception as exc:
                    raise ControllerCapsuleError("RESULT_REFERENCE_CYCLE_INVALID") from exc
                field = str(spec.get("field") or "").strip()
                if cycle < 0:
                    raise ControllerCapsuleError(
                        "RESULT_REFERENCE_CYCLE_INVALID:" + str(cycle)
                    )
                found.append((cycle, field))
                return
            for child in item.values():
                walk(child)
            return
        if isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return found


def _collect_literal_strings(value: Any) -> set[str]:
    out: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if set(item) == {"$result"}:
                return
            for child in item.values():
                walk(child)
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if isinstance(item, str) and item:
            out.add(item)

    walk(value)
    return out


def _durable_paths_from_result(result: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    for field in _DURABLE_RESULT_PATH_FIELDS:
        raw = result.get(field)
        if isinstance(raw, str) and raw and raw not in paths:
            paths.append(raw)
    return paths


def _durable_evidence(
    root: pathlib.Path,
    result: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_durable_paths_from_result(result)):
        path = _safe_repo_path(root, raw)
        if not path.is_file():
            raise ControllerCapsuleError("DURABLE_RESULT_MISSING:" + raw)
        evidence["durable-%d" % index] = {
            "path": raw,
            "sha256": _sha_file(path),
        }
    return evidence


def _prior_durable_paths(capsule: Mapping[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    records = capsule.get("records")
    if not isinstance(records, list):
        raise ControllerCapsuleError("CAPSULE_RECORDS_INVALID")
    for record in records:
        if not isinstance(record, Mapping):
            raise ControllerCapsuleError("CAPSULE_RECORD_INVALID")
        index = int(record.get("index", -1))
        evidence = record.get("evidence_values")
        if not isinstance(evidence, Mapping):
            raise ControllerCapsuleError("CAPSULE_EVIDENCE_INVALID")
        for payload in evidence.values():
            if not isinstance(payload, Mapping):
                raise ControllerCapsuleError("CAPSULE_EVIDENCE_PAYLOAD_INVALID")
            raw = payload.get("path")
            if isinstance(raw, str) and raw:
                out[raw] = index
    return out


def assert_no_prior_state_bypass(
    raw_action: Mapping[str, Any],
    capsule: Mapping[str, Any],
) -> None:
    """Reject literal reuse of a prior durable result without a $result edge."""
    literals = _collect_literal_strings(raw_action)
    refs = {cycle for cycle, _field in _collect_result_refs(raw_action)}
    for path, producer_cycle in _prior_durable_paths(capsule).items():
        if path in literals and producer_cycle not in refs:
            raise ControllerCapsuleError(
                "CONTROLLER_STATE_PROVENANCE_BYPASS:"
                + path
                + ":PRODUCER_CYCLE="
                + str(producer_cycle)
            )


def resolve_result_refs(
    value: Any,
    capsule: Mapping[str, Any],
    root: pathlib.Path,
) -> Any:
    module = _load_capsule_v2(root)

    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise ControllerCapsuleError("RESULT_REFERENCE_INVALID")
            try:
                cycle = int(spec.get("cycle", -1))
            except Exception as exc:
                raise ControllerCapsuleError("RESULT_REFERENCE_CYCLE_INVALID") from exc
            if cycle < 0:
                raise ControllerCapsuleError(
                    "RESULT_REFERENCE_CYCLE_INVALID:" + str(cycle)
                )
            key = result_key(cycle)
            try:
                context = module.project_context(capsule, [key])
            except Exception as exc:
                raise ControllerCapsuleError(
                    "RESULT_REFERENCE_STATE_UNAVAILABLE:" + str(cycle)
                ) from exc
            current = copy.deepcopy(context["values"][key])
            field = str(spec.get("field") or "").strip()
            if field:
                for part in field.split("."):
                    if not isinstance(current, Mapping) or part not in current:
                        raise ControllerCapsuleError(
                            "RESULT_REFERENCE_FIELD_MISSING:" + field
                        )
                    current = current[part]
            return copy.deepcopy(current)
        return {
            key: resolve_result_refs(child, capsule, root)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [resolve_result_refs(child, capsule, root) for child in value]
    return copy.deepcopy(value)


def append_cycle(
    capsule: Mapping[str, Any],
    *,
    cycle: int,
    raw_action: Mapping[str, Any],
    resolved_action: Mapping[str, Any],
    result: Mapping[str, Any],
    root: pathlib.Path,
) -> dict[str, Any]:
    module = _load_capsule_v2(root)
    cycle = int(cycle)
    if cycle < 0:
        raise ControllerCapsuleError("CONTROLLER_CYCLE_INVALID")
    if not isinstance(raw_action, Mapping) or not isinstance(resolved_action, Mapping):
        raise ControllerCapsuleError("CONTROLLER_ACTION_INVALID")
    if not isinstance(result, Mapping):
        raise ControllerCapsuleError("CONTROLLER_RESULT_INVALID")

    refs = _collect_result_refs(raw_action)
    future = sorted({ref_cycle for ref_cycle, _field in refs if ref_cycle >= cycle})
    if future:
        raise ControllerCapsuleError(
            "RESULT_REFERENCE_NONCAUSAL:" + ",".join(map(str, future))
        )
    required_cycles = sorted({ref_cycle for ref_cycle, _field in refs})
    requires = [result_key(ref_cycle) for ref_cycle in required_cycles]

    runtime_path = root / "canonical" / "runtime" / "astra_runtime.py"
    if not runtime_path.is_file():
        raise ControllerCapsuleError("ASTRA_RUNTIME_MISSING")
    producer_descriptor = {
        "component": "canonical/runtime/astra_runtime.py",
        "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
        "composition_scope": "DETERMINISTIC_CAPABILITY_GRAPH",
        "runtime_sha256": _sha_file(runtime_path),
    }
    action_ref = "controller-cycle-%d" % cycle
    action_descriptor = {
        "cycle": cycle,
        "raw_action": copy.deepcopy(dict(raw_action)),
        "resolved_action": copy.deepcopy(dict(resolved_action)),
    }
    evidence = _durable_evidence(root, result)
    lineage = [
        "producer:" + PRODUCER_REF,
        "action:" + action_ref,
    ]
    lineage.extend("state:" + key for key in requires)
    lineage.extend("evidence:" + key for key in sorted(evidence))

    key = result_key(cycle)
    try:
        return module.append_macrostep(
            capsule,
            producer_ref=PRODUCER_REF,
            producer_descriptor=producer_descriptor,
            action_ref=action_ref,
            action_descriptor=action_descriptor,
            requires=requires,
            provides=[key],
            values={key: copy.deepcopy(dict(result))},
            evidence_values=evidence,
            lineage={key: lineage},
        )
    except Exception as exc:
        raise ControllerCapsuleError(
            "CONTROLLER_CAPSULE_APPEND_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc


def verify_controller_state(
    capsule: Mapping[str, Any],
    trace: list[Mapping[str, Any]],
    root: pathlib.Path,
) -> dict[str, Any]:
    module = _load_capsule_v2(root)
    verdict = module.verify_capsule(capsule)
    if verdict.get("status") != "PASS":
        return {
            "status": "FAIL_CLOSED",
            "reason": "CAPSULE_VERIFY:" + str(verdict.get("reason")),
        }
    records = capsule.get("records")
    if not isinstance(records, list) or len(records) != len(trace):
        return {
            "status": "FAIL_CLOSED",
            "reason": "CAPSULE_TRACE_LENGTH_MISMATCH",
        }

    for cycle, (record, trace_record) in enumerate(zip(records, trace)):
        if not isinstance(record, Mapping) or not isinstance(trace_record, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "reason": "CAPSULE_TRACE_RECORD_INVALID:" + str(cycle),
            }
        if trace_record.get("cycle") != cycle:
            return {
                "status": "FAIL_CLOSED",
                "reason": "TRACE_CYCLE_MISMATCH:" + str(cycle),
            }
        action_descriptor = record.get("action_descriptor")
        if not isinstance(action_descriptor, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "reason": "ACTION_DESCRIPTOR_INVALID:" + str(cycle),
            }
        if action_descriptor.get("resolved_action") != trace_record.get("plan"):
            return {
                "status": "FAIL_CLOSED",
                "reason": "TRACE_ACTION_MISMATCH:" + str(cycle),
            }
        key = result_key(cycle)
        values = record.get("values")
        if not isinstance(values, Mapping) or values.get(key) != trace_record.get("result"):
            return {
                "status": "FAIL_CLOSED",
                "reason": "TRACE_RESULT_MISMATCH:" + str(cycle),
            }
        evidence = record.get("evidence_values")
        if not isinstance(evidence, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "reason": "TRACE_EVIDENCE_INVALID:" + str(cycle),
            }
        for payload in evidence.values():
            if not isinstance(payload, Mapping):
                return {
                    "status": "FAIL_CLOSED",
                    "reason": "TRACE_EVIDENCE_PAYLOAD_INVALID:" + str(cycle),
                }
            raw = payload.get("path")
            expected = payload.get("sha256")
            if not isinstance(raw, str) or not isinstance(expected, str):
                return {
                    "status": "FAIL_CLOSED",
                    "reason": "TRACE_EVIDENCE_BINDING_INVALID:" + str(cycle),
                }
            try:
                path = _safe_repo_path(root, raw)
                actual = _sha_file(path) if path.is_file() else None
            except Exception:
                actual = None
            if actual != expected:
                return {
                    "status": "FAIL_CLOSED",
                    "reason": "DURABLE_EVIDENCE_DRIFT:" + raw,
                }

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "record_count": len(records),
        "head_hash": capsule.get("head_hash"),
        "cross_cycle_state_authority": "COMPOSITION_STATE_CAPSULE_V2",
        "durable_evidence_rebound": True,
        "acceptance_credit_delta": 0,
    }

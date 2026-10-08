"""Pure native specialized capabilities for the unified Universal Solver.

This module removes architectural isolation for Brain-owned, read-only deterministic
mechanisms. It does not expose arbitrary Python calls. Only explicitly registered
operations may execute, every operation is zero incremental spend, and every
compiled node still passes through the Universal Solver verifier and independent
effect-semantics gates.

The verified output is normalized to one top-level field named result. Later V12
capability nodes may consume nested values through the existing content-bound
value-state reference mechanism.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_NATIVE_SPECIALIZED_CAPABILITY_REGISTRY_V1"
VERIFIER_ID = "NATIVE_SPECIALIZED_OPERATION_V1"
SUCCESS_CONDITION = "NATIVE_SPECIALIZED_OPERATION_PASS"


class NativeSpecializedCapabilityError(ValueError):
    pass


OPERATIONS: dict[str, dict[str, Any]] = {
    "H100_REGISTRY_SNAPSHOT_V8": {
        "family": "H100_VERIFIED_REGISTRY",
        "required": (),
        "optional": (),
    },
    "H100_RESOLVE_VERIFIED_CAPABILITY_V8": {
        "family": "H100_VERIFIED_REGISTRY",
        "required": ("rows", "target"),
        "optional": ("input_name", "exact_nrmse"),
    },
    "H100_PREDICT_VERIFIED_CAPABILITY_V8": {
        "family": "H100_VERIFIED_REGISTRY",
        "required": ("resolution", "point"),
        "optional": (),
    },
    "H100_INVOKE_VERIFIED_CAPABILITY_V8": {
        "family": "H100_VERIFIED_REGISTRY",
        "required": ("capability_id", "payload"),
        "optional": (),
    },
    "MYSTERY_SPARSE_PLAN_EXPERIMENTS_V2": {
        "family": "MYSTERYMECHANISM",
        "required": ("bounds",),
        "optional": (),
    },
    "MYSTERY_SPARSE_SOLVE_V2": {
        "family": "MYSTERYMECHANISM",
        "required": ("rows", "bounds"),
        "optional": ("target", "fit_threshold"),
    },
    "MYSTERY_SPARSE_CHOOSE_FINAL_EXPERIMENT_V2": {
        "family": "MYSTERYMECHANISM",
        "required": ("rows", "bounds"),
        "optional": ("target", "grid_levels"),
    },
    "MYSTERY_SPARSE_DISCOVER_V2": {
        "family": "MYSTERYMECHANISM",
        "required": ("rows", "target"),
        "optional": ("inputs", "max_depth", "beam_width", "pair_pool"),
    },
    "MYSTERY_SEPARABLE_DISCOVER_V1": {
        "family": "MYSTERYMECHANISM",
        "required": ("rows", "bounds"),
        "optional": ("target", "validation_index"),
    },
    "MYSTERY_SEPARABLE_PREDICT_V1": {
        "family": "MYSTERYMECHANISM",
        "required": ("candidate", "point"),
        "optional": (),
    },
    "MYSTERY_SEPARABLE_SERIALIZE_V1": {
        "family": "MYSTERYMECHANISM",
        "required": ("candidate",),
        "optional": (),
    },
}


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\\x00" in value:
        raise NativeSpecializedCapabilityError(label + "_INVALID")
    return value.strip()


def _tokens(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise NativeSpecializedCapabilityError(label + "_INVALID")
    out = [_token(x, label) for x in value]
    if not allow_empty and not out:
        raise NativeSpecializedCapabilityError(label + "_EMPTY")
    if len(out) != len(set(out)):
        raise NativeSpecializedCapabilityError(label + "_DUPLICATE")
    return out


def _validated_args(operation_id: str, args: Any) -> dict[str, Any]:
    spec = OPERATIONS.get(operation_id)
    if spec is None:
        raise NativeSpecializedCapabilityError(
            "NATIVE_SPECIALIZED_OPERATION_UNKNOWN:" + operation_id
        )
    if not isinstance(args, Mapping):
        raise NativeSpecializedCapabilityError("NATIVE_SPECIALIZED_ARGS_INVALID")
    required = set(spec["required"])
    optional = set(spec["optional"])
    missing = sorted(required - set(args))
    extra = sorted(set(args) - required - optional)
    if missing:
        raise NativeSpecializedCapabilityError(
            "NATIVE_SPECIALIZED_ARGS_MISSING:" + ",".join(missing)
        )
    if extra:
        raise NativeSpecializedCapabilityError(
            "NATIVE_SPECIALIZED_ARGS_UNSUPPORTED:" + ",".join(extra)
        )
    return deepcopy(dict(args))


def registry_snapshot() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "NATIVE_SPECIALIZED_CAPABILITY_REGISTRY_READY",
        "verifier_id": VERIFIER_ID,
        "operation_count": len(OPERATIONS),
        "operations": [
            {
                "operation_id": operation_id,
                "family": spec["family"],
                "required_args": list(spec["required"]),
                "optional_args": list(spec["optional"]),
                "result_fields": ["result"],
                "read_only": True,
                "incremental_spend_usd": 0,
            }
            for operation_id, spec in sorted(OPERATIONS.items())
        ],
        "arbitrary_python_allowed": False,
        "effectful_operations_allowed": False,
        "terminal_authority": False,
    }


def invoke(operation_id: str, args: Mapping[str, Any]) -> dict[str, Any]:
    operation_id = _token(operation_id, "OPERATION_ID")
    values = _validated_args(operation_id, args)

    if operation_id == "H100_REGISTRY_SNAPSHOT_V8":
        from canonical.runtime import h100_verified_capability_registry_v8 as module
        result = module.registry_snapshot()
    elif operation_id == "H100_RESOLVE_VERIFIED_CAPABILITY_V8":
        from canonical.runtime import h100_verified_capability_registry_v8 as module
        result = module.resolve_verified_capability(
            values["rows"],
            target=str(values["target"]),
            input_name=values.get("input_name"),
            exact_nrmse=float(values.get("exact_nrmse", 1e-8)),
        )
    elif operation_id == "H100_PREDICT_VERIFIED_CAPABILITY_V8":
        from canonical.runtime import h100_verified_capability_registry_v8 as module
        result = module.predict(values["resolution"], values["point"])
    elif operation_id == "H100_INVOKE_VERIFIED_CAPABILITY_V8":
        from canonical.runtime import h100_verified_capability_registry_v8 as module
        result = module.invoke(str(values["capability_id"]), values["payload"])
    elif operation_id == "MYSTERY_SPARSE_PLAN_EXPERIMENTS_V2":
        from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as module
        result = module.plan_experiments(values["bounds"])
    elif operation_id == "MYSTERY_SPARSE_SOLVE_V2":
        from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as module
        result = module.solve(
            values["rows"],
            bounds=values["bounds"],
            target=str(values.get("target", "out")),
            fit_threshold=float(values.get("fit_threshold", 0.05)),
        )
    elif operation_id == "MYSTERY_SPARSE_CHOOSE_FINAL_EXPERIMENT_V2":
        from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as module
        result = module.choose_final_experiment(
            values["rows"],
            bounds=values["bounds"],
            target=str(values.get("target", "out")),
            grid_levels=int(values.get("grid_levels", 5)),
        )
    elif operation_id == "MYSTERY_SPARSE_DISCOVER_V2":
        from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as module
        result = module.sparse_discover(
            values["rows"],
            target=str(values["target"]),
            inputs=values.get("inputs"),
            max_depth=int(values.get("max_depth", 2)),
            beam_width=int(values.get("beam_width", 24)),
            pair_pool=int(values.get("pair_pool", 18)),
        )
    elif operation_id == "MYSTERY_SEPARABLE_DISCOVER_V1":
        from canonical.runtime import mysterymechanism_separable_transform_v1 as module
        result = module.discover(
            values["rows"],
            bounds=values["bounds"],
            target=str(values.get("target", "out")),
            validation_index=int(values.get("validation_index", -1)),
        )
    elif operation_id == "MYSTERY_SEPARABLE_PREDICT_V1":
        from canonical.runtime import mysterymechanism_separable_transform_v1 as module
        result = module.predict(values["candidate"], values["point"])
    elif operation_id == "MYSTERY_SEPARABLE_SERIALIZE_V1":
        from canonical.runtime import mysterymechanism_separable_transform_v1 as module
        result = module.serialize(values["candidate"])
    else:
        raise NativeSpecializedCapabilityError(
            "NATIVE_SPECIALIZED_OPERATION_DISPATCH_MISSING:" + operation_id
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__NATIVE_SPECIALIZED_OPERATION_EXECUTED",
        "pass": True,
        "operation_id": operation_id,
        "result": deepcopy(result),
        "read_only": True,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }


def _referenced_effects(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, Mapping):
        if set(value) == {"$effect_result"}:
            spec = value["$effect_result"]
            if not isinstance(spec, Mapping):
                raise NativeSpecializedCapabilityError("EFFECT_RESULT_REFERENCE_INVALID")
            effect = _token(spec.get("effect"), "EFFECT_RESULT_REFERENCE_EFFECT")
            _token(spec.get("field"), "EFFECT_RESULT_REFERENCE_FIELD")
            out.add(effect)
        else:
            for item in value.values():
                out.update(_referenced_effects(item))
    elif isinstance(value, list):
        for item in value:
            out.update(_referenced_effects(item))
    return out


def compile_into_problem(
    problem: Mapping[str, Any],
    instances: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compile registered native operations into ordinary Universal Solver nodes."""
    if not isinstance(problem, Mapping):
        raise NativeSpecializedCapabilityError("PROBLEM_NOT_OBJECT")
    if not isinstance(instances, Sequence) or isinstance(
        instances, (str, bytes, bytearray)
    ):
        raise NativeSpecializedCapabilityError("NATIVE_INSTANCES_INVALID")

    out = deepcopy(dict(problem))
    raw_caps = out.get("capabilities", [])
    if not isinstance(raw_caps, list):
        raise NativeSpecializedCapabilityError("PROBLEM_CAPABILITIES_INVALID")
    caps = deepcopy(raw_caps)
    seen: set[str] = set()
    for row in caps:
        if not isinstance(row, Mapping):
            raise NativeSpecializedCapabilityError("CAPABILITY_NOT_OBJECT")
        seen.add(_token(row.get("id"), "EXISTING_CAPABILITY_ID"))

    for index, raw in enumerate(instances):
        if not isinstance(raw, Mapping):
            raise NativeSpecializedCapabilityError(
                "NATIVE_INSTANCE_NOT_OBJECT:" + str(index)
            )
        allowed = {
            "instance_id",
            "operation_id",
            "requires",
            "provides",
            "args",
            "cost",
            "effect_semantics_binding",
        }
        extra = sorted(set(raw) - allowed)
        if extra:
            raise NativeSpecializedCapabilityError(
                "NATIVE_INSTANCE_FIELDS_UNSUPPORTED:" + ",".join(extra)
            )
        instance_id = _token(raw.get("instance_id"), "INSTANCE_ID")
        operation_id = _token(raw.get("operation_id"), "OPERATION_ID")
        if operation_id not in OPERATIONS:
            raise NativeSpecializedCapabilityError(
                "NATIVE_SPECIALIZED_OPERATION_UNKNOWN:" + operation_id
            )
        if instance_id in seen:
            raise NativeSpecializedCapabilityError("INSTANCE_ID_DUPLICATE:" + instance_id)
        seen.add(instance_id)
        requires = _tokens(raw.get("requires", []), "REQUIRES")
        provides = _tokens(raw.get("provides", []), "PROVIDES", allow_empty=False)
        args = _validated_args(operation_id, raw.get("args", {}))
        referenced = _referenced_effects(args)
        if not referenced.issubset(set(requires)):
            raise NativeSpecializedCapabilityError(
                "EFFECT_RESULT_REFERENCE_NOT_DECLARED_REQUIREMENT:"
                + ",".join(sorted(referenced - set(requires)))
            )
        try:
            cost = float(raw.get("cost", 1))
        except Exception as exc:
            raise NativeSpecializedCapabilityError("COST_INVALID") from exc
        if cost < 0:
            raise NativeSpecializedCapabilityError("COST_NEGATIVE")

        action = {
            "type": "verified_policy",
            "verifier_id": VERIFIER_ID,
            "verifier_payload": {
                "operation_id": operation_id,
                "args": args,
            },
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": SUCCESS_CONDITION,
            },
        }
        cap = {
            "id": instance_id,
            "native_specialized_operation_id": operation_id,
            "requires": requires,
            "provides": provides,
            "cost": cost,
            "result_fields": ["result"],
            "action": action,
        }
        binding = raw.get("effect_semantics_binding")
        if binding is not None:
            if not isinstance(binding, Mapping):
                raise NativeSpecializedCapabilityError("EFFECT_SEMANTICS_BINDING_INVALID")
            cap["effect_semantics_binding"] = deepcopy(dict(binding))
        caps.append(cap)

    out["capabilities"] = caps
    return out

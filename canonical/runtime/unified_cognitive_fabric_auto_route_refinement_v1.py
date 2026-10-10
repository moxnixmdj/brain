"""Executable refinement verifier for Unified Cognitive Fabric AUTO routing.

Scope is deliberately narrow: prove that unified_cognitive_fabric_v1._auto_mode
matches the independently declared finite structural route model over all
98,304 states in that model. Direct imported collaborators are replaced only
for module loading; _auto_mode itself is the exact concrete executable under
test.

This verifier grants zero authority or credit outside that bounded classifier
claim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any, Mapping

CERT_SCHEMA = "PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_AUTO_ROUTE_REFINEMENT_CERTIFICATE_V1"
MODEL_SCHEMA = "PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_AUTO_ROUTE_ABSTRACT_MODEL_V1"
SUBJECT_ID = "CURRENT_UNIFIED_COGNITIVE_FABRIC_AUTO_ROUTE_CLASSIFIER"

SIGNALS = (
    "OEWN_DECISION_SENSE",
    "SEMANTIC_AMBIGUITY",
    "SEMANTIC_RELATION",
    "LIVE_COMPOSITION",
    "LIVE_CAPABILITY",
    "BOUND_CAPABILITY",
    "CAPABILITY_SCHEDULER",
    "REPAIR",
    "UNIVERSAL_ESCAPE",
    "COMPILED_TASK",
    "ADAPTIVE_SOLVER_BASE",
    "ADEQUATE_DECISION",
)
OPERATION_CLASSES = ("NONE", "H100_SUPPORTED", "OTHER_TRUTHY")
EXPECTED_STATE_COUNT = (2 ** len(SIGNALS)) * len(OPERATION_CLASSES) * 2 * 2 * 2

DIRECT_MODULES = (
    "live_integrated_brain_v1",
    "p3_real_context_v3_admission_v12",
    "autonomous_verified_self_improvement_v1",
    "r3_improvement_queue_driver_v1",
    "live_brain_runtime_v1",
    "h100_verified_capability_registry_v8",
    "exact_linear_parameter_polytope_v1",
    "interval_information_frontier_v1",
    "capability_first_scheduler_v1",
    "brain_owned_python_closure_census_v1",
    "current_authority_runtime_census_v1",
    "live_capability_ownership_v1",
    "live_capability_invoker_v1",
    "live_capability_composition_v1",
    "r1_live_architecture_closure_gate_v1",
    "universal_escape_resolver_v1",
    "certificate_gated_selected_route_runtime_entrypoint_v5",
    "terminal_autopilot_v1",
    "terminal_root_decision_gate_v1",
    "terminal_closure_reducer",
    "verified_bound_capability_execution_adapter_v1",
    "semantic_ambiguity_control_v1",
    "semantic_relation_control_v2",
    "oewn_decision_sense_control_v1",
    "finance_bounded_concept_registry_verify_v1",
    "one_shot_reality_closure_v2",
    "reached_escape_repair_cycle_v1",
)


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _safe_path(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        return None
    p = Path(rel)
    if ".." in p.parts:
        return None
    out = (root / p).resolve()
    try:
        out.relative_to(root.resolve())
    except ValueError:
        return None
    return out


def _fail(*errors: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "subject_id": SUBJECT_ID,
        "certificate_subject_id": SUBJECT_ID,
        "errors": sorted(set(errors)),
        "liveness_preserved": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        **extra,
    }


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _stub_module(fullname: str) -> types.ModuleType:
    module = types.ModuleType(fullname)
    module.census = lambda *args, **kwargs: {}
    module.run = lambda *args, **kwargs: {}
    module.execute = lambda *args, **kwargs: {}
    return module


def _load_concrete_auto_mode(path: Path):
    import canonical.runtime as runtime_pkg

    prior_modules: dict[str, Any] = {}
    prior_attrs: dict[str, Any] = {}
    missing = object()
    try:
        for name in DIRECT_MODULES:
            fullname = "canonical.runtime." + name
            prior_modules[fullname] = sys.modules.get(fullname, missing)
            prior_attrs[name] = getattr(runtime_pkg, name, missing)
            stub = _stub_module(fullname)
            sys.modules[fullname] = stub
            setattr(runtime_pkg, name, stub)

        spec = importlib.util.spec_from_file_location(
            "project_brain_unified_fabric_auto_route_refinement_subject",
            path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("CONCRETE_LOAD_SPEC_FAILED")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "_auto_mode", None)
        error_type = getattr(module, "CognitiveFabricError", None)
        if not callable(fn) or not isinstance(error_type, type):
            raise RuntimeError("CONCRETE_AUTO_MODE_ENTRYPOINT_INVALID")
        return fn, error_type
    finally:
        for name in DIRECT_MODULES:
            fullname = "canonical.runtime." + name
            old_module = prior_modules.get(fullname, missing)
            if old_module is missing:
                sys.modules.pop(fullname, None)
            else:
                sys.modules[fullname] = old_module
            old_attr = prior_attrs.get(name, missing)
            if old_attr is missing:
                try:
                    delattr(runtime_pkg, name)
                except AttributeError:
                    pass
            else:
                setattr(runtime_pkg, name, old_attr)


def _signal_map(mask: int) -> dict[str, bool]:
    return {
        signal: bool(mask & (1 << index))
        for index, signal in enumerate(SIGNALS)
    }


def _build_payload(
    signal: Mapping[str, bool],
    *,
    operation_class: str,
    problem_mapping: bool,
    repair_has_executable: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if signal["OEWN_DECISION_SENSE"]:
        payload.update({"sense_universe": [], "decision_manifest": {}})
    if signal["SEMANTIC_AMBIGUITY"]:
        payload.update({
            "ambiguity_owner": "SYSTEM_MODEL",
            "hypothesis_set_complete": True,
            "worlds": [],
            "observations": [],
        })
    if signal["SEMANTIC_RELATION"]:
        payload.update({
            "left_id": "left",
            "right_id": "right",
            "scope_id": "scope",
            "required_relation": "ENTAILS",
        })
    if signal["LIVE_COMPOSITION"]:
        payload["composition_steps"] = []
    if signal["LIVE_CAPABILITY"]:
        payload.update({"capability_id": "cap", "capability_payload": {}})
    if signal["BOUND_CAPABILITY"]:
        payload.update({"capability_id": "cap", "inputs": {}})
    if signal["CAPABILITY_SCHEDULER"]:
        payload["work"] = []
    if signal["REPAIR"]:
        payload["failure_fingerprint"] = "failure"
        payload["components"] = (
            [{"executable_capability": {}}]
            if repair_has_executable
            else []
        )
    if operation_class == "H100_SUPPORTED":
        payload["operation"] = "SNAPSHOT"
    elif operation_class == "OTHER_TRUTHY":
        payload["operation"] = "CUSTOM"
    if problem_mapping:
        payload["problem"] = {}
    if signal["UNIVERSAL_ESCAPE"]:
        payload.update({
            "escape_cell_id": "cell",
            "escape_membership_bound": {},
            "admission_candidates": [],
            "v9_args": {},
        })
    if signal["COMPILED_TASK"]:
        payload.update({
            "task_id": "task",
            "initial_facts": [],
            "target_effects": ["effect"],
            "capability_inputs": {},
        })
    if signal["ADAPTIVE_SOLVER_BASE"]:
        payload.update({
            "task_id": "task",
            "capabilities": [],
            "target_effects": ["effect"],
        })
    if signal["ADEQUATE_DECISION"]:
        payload.update({"task_id": "task", "goal": "goal"})
    return payload


def _expected_mode(
    signal: Mapping[str, bool],
    *,
    operation_class: str,
    problem_mapping: bool,
    repair_has_executable: bool,
    learning_option_present: bool,
) -> str | None:
    if signal["OEWN_DECISION_SENSE"]:
        return "OEWN_DECISION_SENSE"
    if signal["SEMANTIC_AMBIGUITY"]:
        return "SEMANTIC_AMBIGUITY"
    if signal["SEMANTIC_RELATION"]:
        return "SEMANTIC_RELATION"
    if signal["LIVE_COMPOSITION"]:
        return "LIVE_COMPOSITION"
    if signal["LIVE_CAPABILITY"]:
        return "LIVE_CAPABILITY"
    if signal["BOUND_CAPABILITY"]:
        return "BOUND_CAPABILITY"
    if signal["CAPABILITY_SCHEDULER"]:
        return "CAPABILITY_SCHEDULER"
    if signal["REPAIR"]:
        return "REPAIR_CYCLE" if repair_has_executable else "REPAIR_SYNTHESIS"
    if operation_class != "NONE" and problem_mapping:
        return "MYSTERY_INFERENCE"
    if operation_class == "H100_SUPPORTED":
        return "H100_INFERENCE"
    if signal["UNIVERSAL_ESCAPE"]:
        return "UNIVERSAL_ESCAPE"
    if signal["COMPILED_TASK"]:
        return "COMPILED_TASK"
    if signal["ADAPTIVE_SOLVER_BASE"]:
        return "LEARNING_EPISODE" if learning_option_present else "ADAPTIVE_SOLVER"
    if signal["ADEQUATE_DECISION"]:
        return "ADEQUATE_DECISION"
    return None


def verify_refinement(
    *,
    root: Path,
    certificate_path: Path,
    subject_id: str,
) -> dict[str, Any]:
    root = root.resolve()
    certificate_path = certificate_path.resolve()
    if subject_id != SUBJECT_ID:
        return _fail("SUBJECT_ID_INVALID")

    cert = _read_json(certificate_path)
    if cert is None:
        return _fail("CERTIFICATE_JSON_INVALID")
    if cert.get("schema") != CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID")
    if cert.get("subject_id") != SUBJECT_ID:
        return _fail("CERTIFICATE_SUBJECT_MISMATCH")
    for field in (
        "acceptance_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
        "terminal_credit_delta",
    ):
        if cert.get(field, 0) != 0:
            return _fail("CERTIFICATE_NONZERO_CREDIT:" + field)

    abstract_ref = cert.get("abstract_spec")
    concrete_ref = cert.get("concrete_implementation")
    if not isinstance(abstract_ref, Mapping):
        return _fail("ABSTRACT_SPEC_REF_MISSING")
    if not isinstance(concrete_ref, Mapping):
        return _fail("CONCRETE_IMPLEMENTATION_REF_MISSING")

    abstract_path = _safe_path(root, abstract_ref.get("path"))
    concrete_path = _safe_path(root, concrete_ref.get("path"))
    if abstract_path is None:
        return _fail("ABSTRACT_SPEC_PATH_INVALID")
    if concrete_path is None:
        return _fail("CONCRETE_IMPLEMENTATION_PATH_INVALID")
    if not abstract_path.is_file():
        return _fail("ABSTRACT_SPEC_FILE_MISSING")
    if not concrete_path.is_file():
        return _fail("CONCRETE_IMPLEMENTATION_FILE_MISSING")
    if _blob_sha(abstract_path) != abstract_ref.get("git_blob_sha"):
        return _fail("ABSTRACT_SPEC_BLOB_SHA_MISMATCH")
    if _blob_sha(concrete_path) != concrete_ref.get("git_blob_sha"):
        return _fail("CONCRETE_IMPLEMENTATION_BLOB_SHA_MISMATCH")
    if concrete_ref.get("entrypoint") != "_auto_mode":
        return _fail("CONCRETE_ENTRYPOINT_INVALID")

    model = _read_json(abstract_path)
    if model is None:
        return _fail("ABSTRACT_MODEL_JSON_INVALID")
    checks = (
        (model.get("schema") == MODEL_SCHEMA, "ABSTRACT_MODEL_SCHEMA_INVALID"),
        (model.get("subject_id") == SUBJECT_ID, "ABSTRACT_MODEL_SUBJECT_MISMATCH"),
        (tuple(model.get("boolean_route_signals") or ()) == SIGNALS, "ABSTRACT_MODEL_SIGNALS_INVALID"),
        (
            tuple((model.get("modifiers") or {}).get("operation_class") or ())
            == OPERATION_CLASSES,
            "ABSTRACT_MODEL_OPERATION_CLASSES_INVALID",
        ),
        (
            model.get("exhaustive_state_count") == EXPECTED_STATE_COUNT,
            "ABSTRACT_MODEL_STATE_COUNT_INVALID",
        ),
        (model.get("liveness_claim") is False, "ABSTRACT_MODEL_LIVENESS_CLAIM_INVALID"),
        (model.get("terminal_credit_delta", 0) == 0, "ABSTRACT_MODEL_NONZERO_TERMINAL_CREDIT"),
    )
    errors = [error for ok, error in checks if not ok]
    if errors:
        return _fail(*errors)

    try:
        concrete_auto_mode, concrete_error = _load_concrete_auto_mode(concrete_path)
    except Exception as exc:
        return _fail("CONCRETE_LOAD_FAILED:" + type(exc).__name__)

    checked = 0
    mismatches: list[dict[str, Any]] = []
    for mask in range(1 << len(SIGNALS)):
        signal = _signal_map(mask)
        for operation_class in OPERATION_CLASSES:
            for problem_mapping in (False, True):
                for repair_has_executable in (False, True):
                    for learning_option_present in (False, True):
                        payload = _build_payload(
                            signal,
                            operation_class=operation_class,
                            problem_mapping=problem_mapping,
                            repair_has_executable=repair_has_executable,
                        )
                        options = (
                            {"state_path": "state.json"}
                            if learning_option_present
                            else {}
                        )
                        expected = _expected_mode(
                            signal,
                            operation_class=operation_class,
                            problem_mapping=problem_mapping,
                            repair_has_executable=repair_has_executable,
                            learning_option_present=learning_option_present,
                        )
                        try:
                            actual = concrete_auto_mode(payload, options)
                            actual_error = None
                        except concrete_error as exc:
                            actual = None
                            actual_error = str(exc)
                        except Exception as exc:
                            return _fail(
                                "CONCRETE_UNEXPECTED_EXCEPTION:" + type(exc).__name__,
                                cases_checked=checked,
                            )

                        checked += 1
                        if expected is None:
                            matches = (
                                actual is None
                                and actual_error == "AUTO_ROUTE_AMBIGUOUS_OR_UNMODELED"
                            )
                        else:
                            matches = actual == expected and actual_error is None
                        if not matches:
                            mismatches.append({
                                "mask": mask,
                                "operation_class": operation_class,
                                "problem_mapping": problem_mapping,
                                "repair_has_executable": repair_has_executable,
                                "learning_option_present": learning_option_present,
                                "expected": expected,
                                "actual": actual,
                                "actual_error": actual_error,
                            })
                            if len(mismatches) >= 16:
                                return _fail(
                                    "REFINEMENT_COUNTEREXAMPLES_FOUND",
                                    cases_checked=checked,
                                    mismatch_count=len(mismatches),
                                    counterexamples=mismatches,
                                )

    if checked != EXPECTED_STATE_COUNT:
        return _fail(
            "EXHAUSTIVE_STATE_COUNT_MISMATCH",
            cases_checked=checked,
            expected_state_count=EXPECTED_STATE_COUNT,
        )
    if mismatches:
        return _fail(
            "REFINEMENT_COUNTEREXAMPLES_FOUND",
            cases_checked=checked,
            mismatch_count=len(mismatches),
            counterexamples=mismatches,
        )

    return {
        "pass": True,
        "subject_id": SUBJECT_ID,
        "certificate_subject_id": cert.get("subject_id"),
        "refinement_fact": "EXHAUSTIVE_FINITE_AUTO_ROUTE_MODEL_MATCH",
        "cases_checked": checked,
        "mismatch_count": 0,
        "abstract_model_git_blob_sha": _blob_sha(abstract_path),
        "concrete_implementation_git_blob_sha": _blob_sha(concrete_path),
        "liveness_preserved": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

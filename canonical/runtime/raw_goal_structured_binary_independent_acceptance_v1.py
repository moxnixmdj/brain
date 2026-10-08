"""Independent raw acceptance for strict structured-binary round-trip goals.

This cell promotes an already verified Project Brain compound-goal pattern only when
all semantics are explicit and mechanically checkable:

1. create an exact literal JSON record set;
2. encode that exact JSON with one verified bound codec capability;
3. decode with a producer-independent implementation from a different supplier
   class and prove semantic equality to the source JSON;
4. finish through the model-independent controller.

The verifier independently recompiles the raw goal, reopens the exact JSON source,
checks the complete controller trace, and requires the cross-supplier verifier to
report semantic equality plus producer/dependency or implementation independence.

No lexical grounding, provider proposal, or codec execution success alone grants
acceptance authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_STRUCTURED_BINARY_INDEPENDENT_ACCEPTANCE_V1"
ROOT = Path(__file__).resolve().parents[2]


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _base(status: str, *, matched: bool = False, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": matched,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _safe_canonical_path(raw: Any, *, suffix: str | None = None) -> str | None:
    value = str(raw or "").strip()
    p = PurePosixPath(value)
    if (
        not value
        or p.is_absolute()
        or ".." in p.parts
        or not value.startswith("canonical/")
    ):
        return None
    if suffix is not None and p.suffix.lower() != suffix.lower():
        return None
    return value


def _load_registry(root: Path) -> dict[str, Any]:
    doc = json.loads(
        (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    rows = doc.get("capabilities")
    if not isinstance(rows, Mapping):
        raise ValueError("BOUND_CAPABILITY_REGISTRY_INVALID")
    return goal_compiler._platform_admissible_registry(dict(rows))


def _routing_targets(compiled: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    direct = compiled.get("target_effects")
    if isinstance(direct, list):
        for effect in direct:
            if isinstance(effect, str) and effect and effect not in out:
                out.append(effect)
    parts = compiled.get("compiled_parts")
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, Mapping):
                continue
            targets = part.get("target_effects")
            if not isinstance(targets, list):
                continue
            for effect in targets:
                if isinstance(effect, str) and effect and effect not in out:
                    out.append(effect)
    return out


def preflight(goal: str, *, root: str | Path = ROOT) -> dict[str, Any]:
    text = str(goal or "").strip()
    if not text:
        return _base("NO_MATCH")
    rr = Path(root).resolve()
    try:
        registry = _load_registry(rr)
        compiled = goal_compiler.compile_goal(text, registry, rr)
    except goal_compiler.GoalCompilationFailure:
        return _base("NO_MATCH")
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )

    clauses = compiled.get("clauses")
    parts = compiled.get("compiled_parts")
    actions = compiled.get("controller_actions")
    if (
        compiled.get("compiler_mode") != "DETERMINISTIC_COMPOUND_ACTION_PLAN"
        or compiled.get("clause_coverage_verified") is not True
        or not isinstance(clauses, list)
        or len(clauses) != 3
        or not isinstance(parts, list)
        or len(parts) != 3
        or not isinstance(actions, list)
        or len(actions) != 4
    ):
        return _base("NO_MATCH")

    p0, p1, p2 = parts
    a0, a1, a2, a3 = actions
    if any(not isinstance(x, Mapping) for x in (p0, p1, p2, a0, a1, a2, a3)):
        return _base("FAIL_CLOSED", reason="CODEC_COMPILED_ROWS_INVALID")

    if p0.get("mode") != "NATIVE_LITERAL_JSON_RECORDS":
        return _base("NO_MATCH")
    write_args = a0.get("args")
    if (
        a0.get("type") != "write_json_records"
        or not isinstance(write_args, Mapping)
        or not isinstance(write_args.get("fields"), list)
        or not write_args.get("fields")
        or not isinstance(write_args.get("records"), list)
        or not write_args.get("records")
    ):
        return _base("FAIL_CLOSED", reason="CODEC_LITERAL_JSON_ACTION_INVALID")

    source_path = _safe_canonical_path(write_args.get("output_path"), suffix=".json")
    if source_path is None:
        return _base("FAIL_CLOSED", reason="CODEC_SOURCE_PATH_OUTSIDE_ADMITTED_SCOPE")
    fields = list(write_args["fields"])
    records = deepcopy(list(write_args["records"]))
    if (
        p0.get("output_path") != source_path
        or p0.get("fields") != fields
        or p0.get("record_count") != len(records)
    ):
        return _base("FAIL_CLOSED", reason="CODEC_LITERAL_JSON_PART_ACTION_MISMATCH")

    if p1.get("mode") != "VERIFIED_CAPABILITY":
        return _base("NO_MATCH")
    policy_capability = str(p1.get("selected_capability") or "").strip()
    inputs = p1.get("inputs")
    if (
        not policy_capability
        or policy_capability not in registry
        or not isinstance(inputs, Mapping)
        or inputs.get("json_path") != source_path
    ):
        return _base("FAIL_CLOSED", reason="CODEC_PRODUCER_BINDING_INVALID")
    binary_path = _safe_canonical_path(inputs.get("output_path"))
    if binary_path is None:
        return _base("FAIL_CLOSED", reason="CODEC_BINARY_PATH_OUTSIDE_ADMITTED_SCOPE")
    fmt = PurePosixPath(binary_path).suffix.lower().lstrip(".")
    if not fmt:
        return _base("FAIL_CLOSED", reason="CODEC_BINARY_FORMAT_MISSING")

    expected_effect = "structured.binary.encode." + fmt
    entry = registry[policy_capability]
    provides = [str(x) for x in (entry.get("provides") or [])]
    if expected_effect not in provides:
        return _base("NO_MATCH")
    p1_targets = p1.get("target_effects")
    if not isinstance(p1_targets, list) or expected_effect not in p1_targets:
        return _base("FAIL_CLOSED", reason="CODEC_PRODUCER_EFFECT_MISMATCH")

    invoke_args = a1.get("args")
    invoke_expect = a1.get("expect")
    if (
        a1.get("type") != "invoke_capability"
        or not isinstance(invoke_args, Mapping)
        or invoke_args.get("capability_id") != policy_capability
        or invoke_args.get("json_path") != source_path
        or invoke_args.get("output_path") != binary_path
        or not isinstance(invoke_expect, Mapping)
        or invoke_expect.get("type") != "field_equals"
        or invoke_expect.get("field") != "output_verified"
        or invoke_expect.get("value") is not True
    ):
        return _base("FAIL_CLOSED", reason="CODEC_PRODUCER_ACTION_INVALID")

    if p2.get("mode") != "CROSS_SUPPLIER_PRODUCER_INDEPENDENT_CODEC_VERIFICATION":
        return _base("NO_MATCH")
    producer_project = str(p2.get("producer_project") or "").strip()
    supplier_class = str(p2.get("verifier_supplier_class") or "").strip()
    if (
        p2.get("producer_capability") != policy_capability
        or p2.get("json_path") != source_path
        or p2.get("binary_path") != binary_path
        or str(p2.get("format") or "").lower() != fmt
        or not producer_project
        or supplier_class not in {"npm_javascript_library", "pypi_python_library"}
    ):
        return _base("FAIL_CLOSED", reason="CODEC_INDEPENDENT_VERIFIER_PART_INVALID")

    verify_args = a2.get("args")
    verify_expect = a2.get("expect")
    expected_verify_type = (
        "verify_with_independent_npm_codec"
        if supplier_class == "npm_javascript_library"
        else "verify_with_independent_pypi_codec"
    )
    if (
        a2.get("type") != expected_verify_type
        or not isinstance(verify_args, Mapping)
        or verify_args.get("producer_capability_id") != policy_capability
        or verify_args.get("producer_project") != producer_project
        or verify_args.get("json_path") != source_path
        or verify_args.get("binary_path") != binary_path
        or str(verify_args.get("format") or "").lower() != fmt
        or not isinstance(verify_expect, Mapping)
        or verify_expect.get("type") != "field_equals"
        or verify_expect.get("field") != "verified"
        or verify_expect.get("value") is not True
    ):
        return _base("FAIL_CLOSED", reason="CODEC_INDEPENDENT_VERIFIER_ACTION_INVALID")

    if (
        a3.get("type") != "finish"
        or (a3.get("args") or {}).get("summary") != "COMPOUND_GOAL_COMPLETE"
    ):
        return _base("FAIL_CLOSED", reason="CODEC_FINISH_ACTION_INVALID")

    routing_targets = _routing_targets(compiled)
    if expected_effect not in routing_targets:
        return _base("FAIL_CLOSED", reason="CODEC_ROUTING_EFFECT_MISSING")

    return {
        **_base("STRUCTURED_BINARY_INDEPENDENT_RAW_GOAL_MATCHED", matched=True),
        "goal_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "source_path": source_path,
        "binary_path": binary_path,
        "format": fmt,
        "fields": fields,
        "record_count": len(records),
        "records_sha256": sha256(_canon(records)).hexdigest(),
        "expected_records": records,
        "producer_capability_id": policy_capability,
        "producer_project": producer_project,
        "verifier_supplier_class": supplier_class,
        "verifier_action_type": expected_verify_type,
        "routing_target_effects": routing_targets,
        "compiler_mode": "DETERMINISTIC_COMPOUND_ACTION_PLAN",
        "preflight_execution_authority": False,
    }


def verify(*, goal: str, raw_result: Mapping[str, Any], root: str | Path = ROOT) -> dict[str, Any]:
    pf = preflight(goal, root=root)
    if pf.get("matched") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__STRUCTURED_BINARY_GOAL_NOT_MATCHED",
            "accepted_obligation_ids": [],
        }
    if not isinstance(raw_result, Mapping):
        return {
            **pf,
            "status": "FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
            "accepted_obligation_ids": [],
        }

    contract = compile_contract(
        str(goal),
        source_id="user",
        routing_target_effects=pf["routing_target_effects"],
    )
    if contract.get("pass") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
            "accepted_obligation_ids": [],
            "contract_errors": contract.get("errors"),
        }

    rr = Path(root).resolve()
    source = (rr / pf["source_path"]).resolve()
    binary = (rr / pf["binary_path"]).resolve()
    if (
        (source != rr and rr not in source.parents)
        or (binary != rr and rr not in binary.parents)
    ):
        return {
            **pf,
            "status": "FAIL_CLOSED__CODEC_ARTIFACT_OUTSIDE_REPO",
            "accepted_obligation_ids": [],
        }

    try:
        observed_records = json.loads(source.read_text(encoding="utf-8"))
        binary_present = binary.is_file() and binary.stat().st_size > 0
    except Exception as exc:
        return {
            **pf,
            "status": "OPEN__STRUCTURED_BINARY_ARTIFACT_UNREADABLE",
            "accepted_obligation_ids": [],
            "reason": type(exc).__name__ + ":" + str(exc),
        }

    source_exact = observed_records == pf["expected_records"]
    controller = raw_result.get("controller_execution")
    trace = controller.get("trace") if isinstance(controller, Mapping) else None
    trace_ok = False
    verifier_independence_ok = False
    producer_output_ok = False

    if isinstance(trace, list) and len(trace) == 4:
        t0, t1, t2, t3 = trace
        if all(isinstance(x, Mapping) for x in (t0, t1, t2, t3)):
            p0, r0 = t0.get("plan"), t0.get("result")
            p1, r1 = t1.get("plan"), t1.get("result")
            p2, r2 = t2.get("plan"), t2.get("result")
            p3, r3 = t3.get("plan"), t3.get("result")
            producer_output_ok = (
                isinstance(r1, Mapping)
                and r1.get("output_verified") is True
                and r1.get("output_path") == pf["binary_path"]
                and r1.get("source_path") == pf["source_path"]
            )
            verifier_independence_ok = (
                isinstance(r2, Mapping)
                and r2.get("verified") is True
                and r2.get("producer_independent") is True
                and (
                    r2.get("dependency_independent") is True
                    or (
                        r2.get("implementation_independent") is True
                        and r2.get("supplier_class_independent") is True
                    )
                )
                and str(r2.get("format") or "").lower() == pf["format"]
                and r2.get("producer_capability_id") == pf["producer_capability_id"]
                and r2.get("producer_project") == pf["producer_project"]
            )
            trace_ok = (
                isinstance(p0, Mapping)
                and p0.get("type") == "write_json_records"
                and (p0.get("args") or {}).get("output_path") == pf["source_path"]
                and (p0.get("args") or {}).get("fields") == pf["fields"]
                and (p0.get("args") or {}).get("records") == pf["expected_records"]
                and isinstance(r0, Mapping)
                and r0.get("verified") is True
                and isinstance(p1, Mapping)
                and p1.get("type") == "invoke_capability"
                and (p1.get("args") or {}).get("capability_id") == pf["producer_capability_id"]
                and (p1.get("args") or {}).get("json_path") == pf["source_path"]
                and (p1.get("args") or {}).get("output_path") == pf["binary_path"]
                and producer_output_ok
                and isinstance(p2, Mapping)
                and p2.get("type") == pf["verifier_action_type"]
                and (p2.get("args") or {}).get("json_path") == pf["source_path"]
                and (p2.get("args") or {}).get("binary_path") == pf["binary_path"]
                and (p2.get("args") or {}).get("producer_capability_id") == pf["producer_capability_id"]
                and (p2.get("args") or {}).get("producer_project") == pf["producer_project"]
                and str((p2.get("args") or {}).get("format") or "").lower() == pf["format"]
                and verifier_independence_ok
                and isinstance(p3, Mapping)
                and p3.get("type") == "finish"
                and (p3.get("args") or {}).get("summary") == "COMPOUND_GOAL_COMPLETE"
                and isinstance(r3, Mapping)
                and r3.get("summary") == "COMPOUND_GOAL_COMPLETE"
            )

    obligations = contract["acceptance_contract"]["obligations"]
    required_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
    full = (
        raw_result.get("pass") is True
        and raw_result.get("compiler_mode") == "DETERMINISTIC_COMPOUND_ACTION_PLAN"
        and raw_result.get("compiled_part_count") == 3
        and raw_result.get("controller_action_count") == 4
        and raw_result.get("raw_goal_sha256") == pf["goal_sha256"]
        and raw_result.get("raw_task_contract_sha256") == contract["task_contract_sha256"]
        and raw_result.get("raw_source_coverage_complete") is True
        and raw_result.get("raw_acceptance_obligation_count") == len(obligations)
        and raw_result.get("model_dependency_count") == 0
        and raw_result.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
        and isinstance(controller, Mapping)
        and controller.get("returncode") == 0
        and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
        and controller.get("final_summary") == "COMPOUND_GOAL_COMPLETE"
        and source_exact
        and binary_present
        and trace_ok
        and producer_output_ok
        and verifier_independence_ok
        and len(required_ids) == len(obligations)
        and len(required_ids) > 0
    )

    if not full:
        return {
            "schema": SCHEMA,
            "status": "OPEN__STRUCTURED_BINARY_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass": False,
            "matched": True,
            "goal_sha256": pf["goal_sha256"],
            "source_path": pf["source_path"],
            "binary_path": pf["binary_path"],
            "format": pf["format"],
            "source_exact": source_exact,
            "binary_present": binary_present,
            "producer_output_verified": producer_output_ok,
            "independent_semantic_verification_verified": verifier_independence_ok,
            "trace_verified": trace_ok,
            "required_obligation_count": len(required_ids),
            "accepted_obligation_ids": [],
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__STRUCTURED_BINARY_INDEPENDENT_RAW_GOAL_ACCEPTED",
        "pass": True,
        "matched": True,
        "goal_sha256": pf["goal_sha256"],
        "source_path": pf["source_path"],
        "binary_path": pf["binary_path"],
        "format": pf["format"],
        "producer_capability_id": pf["producer_capability_id"],
        "producer_project": pf["producer_project"],
        "verifier_supplier_class": pf["verifier_supplier_class"],
        "records_sha256": pf["records_sha256"],
        "record_count": pf["record_count"],
        "source_exact": True,
        "binary_present": True,
        "producer_output_verified": True,
        "independent_semantic_verification_verified": True,
        "required_obligation_count": len(required_ids),
        "accepted_obligation_ids": required_ids,
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "routing_success_authority": False,
        "acceptance_basis": (
            "STRICT_THREE_CLAUSE_CODEC_GRAMMAR__LOSSLESS_RAW_SOURCE_COVERAGE__"
            "EXACT_LITERAL_SOURCE_JSON__VERIFIED_BOUND_CODEC_EXECUTION__"
            "CROSS_SUPPLIER_PRODUCER_INDEPENDENT_SEMANTIC_DECODE_EQUALITY__"
            "MODEL_INDEPENDENT_CONTROLLER_TRACE"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

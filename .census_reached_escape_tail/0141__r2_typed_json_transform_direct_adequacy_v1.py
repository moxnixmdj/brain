"""R2 direct adequacy for exact typed local JSON transformation goals.

Bounded family:
- input is one repository-local JSON array of objects;
- a repository-local typed transform spec selects a finite sequence of
  independently re-computable operations;
- jq is the verified producer;
- Python stdlib code in this module independently computes the expected result.

Supported operations are exact equality selection, homogeneous scalar sorting,
top-level projection, and bounded prefix selection. Source and spec bytes are
hash-bound before execution. The output is transactional and commits only when
the independently recomputed semantic JSON result equals the produced result.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound_exec
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_TYPED_JSON_TRANSFORM_DIRECT_ADEQUACY_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_TYPED_JSON_TRANSFORM_V1"
ROUTE_ID = "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1"
CAPABILITY_ID = "json.query.jq"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r"^Using the typed JSON transform spec at (?P<spec>" + _PATH + r"\.json), "
    r"transform (?P<input>" + _PATH + r"\.json) and save the verified JSON result to "
    r"(?P<output>" + _PATH + r"\.json)\.?$",
    re.IGNORECASE,
)
_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: Path, rel: str) -> Path:
    root = root.resolve()
    p = Path(str(rel))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("PATH_INVALID")
    resolved = (root / p).resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return resolved


def _sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canon(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _path(raw: Any) -> tuple[str, ...]:
    if (
        not isinstance(raw, list)
        or not raw
        or len(raw) > 8
        or any(not isinstance(x, str) or _FIELD.fullmatch(x) is None for x in raw)
    ):
        raise ValueError("TRANSFORM_PATH_INVALID")
    return tuple(raw)


def _get(item: Mapping[str, Any], path: Sequence[str]) -> Any:
    cur: Any = item
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _validated_spec(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, Mapping) or raw.get("schema") != SPEC_SCHEMA:
        raise ValueError("TRANSFORM_SPEC_SCHEMA_INVALID")
    operations = raw.get("operations")
    if not isinstance(operations, list) or not operations or len(operations) > 16:
        raise ValueError("TRANSFORM_OPERATIONS_INVALID")
    out: list[dict[str, Any]] = []
    for row in operations:
        if not isinstance(row, Mapping):
            raise ValueError("TRANSFORM_OPERATION_NOT_OBJECT")
        op = str(row.get("op") or "").strip()
        if op == "select_eq":
            path = _path(row.get("path"))
            value = row.get("value")
            if not _scalar(value):
                raise ValueError("SELECT_EQ_VALUE_NOT_SCALAR")
            if set(row) != {"op", "path", "value"}:
                raise ValueError("SELECT_EQ_EXTRA_FIELDS")
            out.append({"op": op, "path": list(path), "value": value})
        elif op == "sort_by":
            path = _path(row.get("path"))
            descending = row.get("descending", False)
            if not isinstance(descending, bool):
                raise ValueError("SORT_DESCENDING_NOT_BOOL")
            if set(row) - {"op", "path", "descending"}:
                raise ValueError("SORT_BY_EXTRA_FIELDS")
            out.append({"op": op, "path": list(path), "descending": descending})
        elif op == "project":
            fields = row.get("fields")
            if (
                not isinstance(fields, list)
                or not fields
                or len(fields) > 64
                or len(set(fields)) != len(fields)
                or any(not isinstance(x, str) or _FIELD.fullmatch(x) is None for x in fields)
            ):
                raise ValueError("PROJECT_FIELDS_INVALID")
            if set(row) != {"op", "fields"}:
                raise ValueError("PROJECT_EXTRA_FIELDS")
            out.append({"op": op, "fields": list(fields)})
        elif op == "take":
            count = row.get("count")
            if not isinstance(count, int) or isinstance(count, bool) or count < 0 or count > 100000:
                raise ValueError("TAKE_COUNT_INVALID")
            if set(row) != {"op", "count"}:
                raise ValueError("TAKE_EXTRA_FIELDS")
            out.append({"op": op, "count": count})
        else:
            raise ValueError("TRANSFORM_OPERATION_UNSUPPORTED:" + op)
    return out


def _reference_apply(source: Any, operations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(source, list) or len(source) > 100000:
        raise ValueError("TRANSFORM_SOURCE_MUST_BE_BOUNDED_ARRAY")
    if any(not isinstance(row, Mapping) for row in source):
        raise ValueError("TRANSFORM_SOURCE_ROWS_MUST_BE_OBJECTS")
    rows = [deepcopy(dict(row)) for row in source]
    for op in operations:
        kind = op["op"]
        if kind == "select_eq":
            path = tuple(op["path"])
            wanted = op["value"]
            rows = [row for row in rows if _get(row, path) == wanted]
        elif kind == "sort_by":
            path = tuple(op["path"])
            keys = [_get(row, path) for row in rows]
            if any(v is None or isinstance(v, (dict, list, bool)) for v in keys):
                raise ValueError("SORT_KEY_MISSING_OR_UNSUPPORTED")
            key_types = {type(v) for v in keys}
            if len(key_types) > 1:
                numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in keys)
                if not numeric:
                    raise ValueError("SORT_KEYS_NOT_HOMOGENEOUS")
            rows = sorted(
                rows,
                key=lambda row: _get(row, path),
                reverse=bool(op.get("descending", False)),
            )
        elif kind == "project":
            fields = list(op["fields"])
            rows = [{field: row.get(field) for field in fields} for row in rows]
        elif kind == "take":
            rows = rows[: int(op["count"])]
        else:
            raise ValueError("REFERENCE_OPERATION_UNSUPPORTED")
    return rows


def _jq_filter(operations: Sequence[Mapping[str, Any]]) -> str:
    parts = ["."]
    for op in operations:
        kind = op["op"]
        if kind == "select_eq":
            path = json.dumps(list(op["path"]), separators=(",", ":"))
            value = json.dumps(op["value"], ensure_ascii=False, allow_nan=False)
            parts.append(f"map(select(getpath({path}) == {value}))")
        elif kind == "sort_by":
            path = json.dumps(list(op["path"]), separators=(",", ":"))
            expr = f"sort_by(getpath({path}))"
            if op.get("descending") is True:
                expr += " | reverse"
            parts.append(expr)
        elif kind == "project":
            assignments = ",".join(
                json.dumps(field) + ":.[" + json.dumps(field) + "]"
                for field in op["fields"]
            )
            parts.append("map({" + assignments + "})")
        elif kind == "take":
            parts.append(".[0:" + str(int(op["count"])) + "]")
        else:
            raise ValueError("JQ_OPERATION_UNSUPPORTED")
    return " | ".join(parts)


def _raw_contract(goal: str) -> dict[str, Any]:
    contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["json.query.transform"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids = list(
        (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
    )
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED", passed=False), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED", passed=False), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE", passed=False), "matched": False}

    try:
        spec_rel = match.group("spec")
        input_rel = match.group("input")
        output_rel = match.group("output")
        spec_path = _safe(root, spec_rel)
        input_path = _safe(root, input_rel)
        output_path = _safe(root, output_rel)
        if len({spec_path, input_path, output_path}) != 3:
            raise ValueError("TRANSFORM_PATH_COLLISION")
        if not spec_path.is_file() or not input_path.is_file():
            raise ValueError("TRANSFORM_SOURCE_OR_SPEC_MISSING")

        registry = live_bound.load_verified_registry()
        entry = registry.get(CAPABILITY_ID)
        if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            raise ValueError("JQ_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        verification = entry.get("verification")
        if not isinstance(verification, Mapping) or verification.get("independent_verified") is not True:
            raise ValueError("JQ_INDEPENDENT_VERIFICATION_REQUIRED")

        spec_raw = json.loads(spec_path.read_text(encoding="utf-8"))
        operations = _validated_spec(spec_raw)
        source = json.loads(input_path.read_text(encoding="utf-8"))
        expected = _reference_apply(source, operations)
        filt = _jq_filter(operations)

        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        instance_id = "r2-typed-json-transform-" + goal_sha[:16]
        prepared = bound_exec.prepare(
            CAPABILITY_ID,
            inputs={
                "jq_filter": filt,
                "json_path": input_rel,
                "output_path": output_rel,
            },
            instance_id=instance_id,
        )
        if prepared.get("capability_id") != CAPABILITY_ID:
            raise ValueError("JQ_PREPARED_CAPABILITY_MISMATCH")

        contract = _raw_contract(goal)
        raw_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": goal_sha,
            "policy_id": goal_scoped_policy_id(CAPABILITY_ID, goal),
            "capability_id": CAPABILITY_ID,
            "spec_path": spec_rel,
            "spec_sha256": _sha_file(spec_path),
            "input_path": input_rel,
            "input_sha256": _sha_file(input_path),
            "output_path": output_rel,
            "operations": deepcopy(operations),
            "jq_filter": filt,
            "expected_result_sha256": sha256(_canon(expected)).hexdigest(),
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids": raw_ids,
            "execution_instance_id": instance_id,
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "semantic_scope": (
                "EXACT_TYPED_LOCAL_JSON_ARRAY_TRANSFORMS__SELECT_EQ_SORT_BY_PROJECT_TAKE"
            ),
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _restore(path: Path, existed: bool, original: bytes | None) -> None:
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original or b"")
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    spec_path = _safe(root, str(pf["spec_path"]))
    input_path = _safe(root, str(pf["input_path"]))
    output_path = _safe(root, str(pf["output_path"]))
    existed = output_path.is_file()
    original = output_path.read_bytes() if existed else None

    try:
        if _sha_file(spec_path) != pf["spec_sha256"] or _sha_file(input_path) != pf["input_sha256"]:
            raise RuntimeError("TRANSFORM_SOURCE_OR_SPEC_DRIFT_BEFORE_EXECUTION")

        produced = bound_exec.execute(
            CAPABILITY_ID,
            inputs={
                "jq_filter": pf["jq_filter"],
                "json_path": pf["input_path"],
                "output_path": pf["output_path"],
            },
            instance_id=pf["execution_instance_id"],
            expected_registry_file_sha256=pf["registry_file_sha256"],
            expected_registry_entry_sha256=pf["registry_entry_sha256"],
            expected_rendered_action_sha256=pf["rendered_action_sha256"],
        )
        if not isinstance(produced, Mapping) or produced.get("pass") is not True:
            raise RuntimeError(
                "JQ_VERIFIED_EXECUTION_FAILED:" + str(produced.get("errors") if isinstance(produced, Mapping) else produced)
            )
        result = produced.get("result")
        if (
            produced.get("capability_id") != CAPABILITY_ID
            or not isinstance(result, Mapping)
            or result.get("output_verified") is not True
            or result.get("output_path") != pf["output_path"]
        ):
            raise RuntimeError("JQ_EXECUTION_BINDING_MISMATCH")

        if _sha_file(spec_path) != pf["spec_sha256"] or _sha_file(input_path) != pf["input_sha256"]:
            raise RuntimeError("TRANSFORM_SOURCE_OR_SPEC_MUTATED_BY_PRODUCER")
        if not output_path.is_file():
            raise RuntimeError("TRANSFORM_OUTPUT_MISSING")

        source = json.loads(input_path.read_text(encoding="utf-8"))
        spec_raw = json.loads(spec_path.read_text(encoding="utf-8"))
        operations = _validated_spec(spec_raw)
        if operations != pf["operations"]:
            raise RuntimeError("TRANSFORM_SPEC_SEMANTICS_DRIFT")
        expected = _reference_apply(source, operations)
        actual = json.loads(output_path.read_text(encoding="utf-8"))
        if actual != expected:
            raise RuntimeError("INDEPENDENT_JSON_TRANSFORM_VERIFICATION_FAILED")
        if sha256(_canon(actual)).hexdigest() != pf["expected_result_sha256"]:
            raise RuntimeError("INDEPENDENT_JSON_TRANSFORM_HASH_MISMATCH")

        contract = _raw_contract(str(request["goal"]))
        accepted_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted_ids != pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "selected_policy_id": pf["policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "spec_path": pf["spec_path"],
            "spec_sha256": pf["spec_sha256"],
            "input_path": pf["input_path"],
            "input_sha256": pf["input_sha256"],
            "output_path": pf["output_path"],
            "output_sha256": _sha_file(output_path),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "producer_result": deepcopy(dict(produced)),
            "acceptance_receipt": {
                "verified": True,
                "producer_independent": True,
                "verifier": "python_stdlib_reference_transform",
                "expected_result_sha256": pf["expected_result_sha256"],
                "actual_semantic_result_sha256": sha256(_canon(actual)).hexdigest(),
                "source_immutability_verified": True,
                "spec_immutability_verified": True,
            },
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "authority_boundary": (
                "EXACT_TYPED_REPOSITORY_LOCAL_JSON_ARRAY_TRANSFORM_GOAL_ONLY;"
                "SUPPORTED_OPS_SELECT_EQ_SORT_BY_PROJECT_TAKE;"
                "JQ_PRODUCER_PLUS_PRODUCER_INDEPENDENT_PYTHON_STDLIB_RECOMPUTATION;"
                "SOURCE_AND_SPEC_IMMUTABLE;ONE_REPOSITORY_LOCAL_JSON_OUTPUT;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(output_path, existed, original)
        return {
            **_base("FAIL_CLOSED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "policy_id": pf.get("policy_id"),
            "goal_sha256": pf.get("goal_sha256"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_rolled_back": True,
        }

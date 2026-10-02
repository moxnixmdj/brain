"""Brain compiler for a bounded normalized structured-method grammar.

Scope:
- candidate-visible normalized schema fields, requirements, applicability conditions,
  branch predicates, and typed rules;
- deterministic branch selection;
- explicit requirement->rule consumer lineage or justified exclusion;
- typed/dimensional intermediate DAG construction;
- invariant validation and evaluated consequences.

Semantic extraction of unstated rules remains upstream and is not claimed here.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import math

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_GRAPH_CANDIDATE_V1"
_NUMERIC = {"integer", "number"}


class CompileError(ValueError):
    pass


def _condition(cond: Mapping[str, Any] | None, values: Mapping[str, Any]) -> bool:
    if cond is None:
        return True
    if not isinstance(cond, Mapping):
        raise CompileError("CONDITION_INVALID")
    field = str(cond.get("field") or "")
    op = str(cond.get("op") or "")
    if field not in values:
        raise CompileError("CONDITION_FIELD_UNKNOWN:" + field)
    actual = values[field]
    expected = cond.get("value")
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op in {"gt", "ge", "lt", "le"}:
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise CompileError("CONDITION_NUMERIC_ACTUAL_REQUIRED")
        if not isinstance(expected, (int, float)) or isinstance(expected, bool):
            raise CompileError("CONDITION_NUMERIC_EXPECTED_REQUIRED")
        return {
            "gt": actual > expected,
            "ge": actual >= expected,
            "lt": actual < expected,
            "le": actual <= expected,
        }[op]
    raise CompileError("CONDITION_OPERATOR_UNSUPPORTED:" + op)


def _schema(rows: Any) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise CompileError("SCHEMA_FIELDS_REQUIRED")
    meta: dict[str, dict[str, Any]] = {}
    values: dict[str, Any] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompileError(f"SCHEMA_FIELD_INVALID:{i}")
        fid = str(row.get("id") or "")
        typ = str(row.get("type") or "")
        dim = str(row.get("dimension") or "")
        if not fid or fid in meta or typ not in {"integer", "number", "boolean", "enum"} or not dim:
            raise CompileError(f"SCHEMA_FIELD_DECLARATION_INVALID:{i}")
        value = row.get("value")
        if typ == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value))):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "boolean" and not isinstance(value, bool):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "enum" and not isinstance(value, str):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        meta[fid] = {"type": typ, "dimension": dim}
        values[fid] = value
    return meta, values


def _requirements(rows: Any, values: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(rows, list) or not rows:
        raise CompileError("REQUIREMENTS_REQUIRED")
    applicable: dict[str, dict[str, Any]] = {}
    exclusions: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompileError(f"REQUIREMENT_INVALID:{i}")
        rid = str(row.get("id") or "")
        source_kind = str(row.get("source_kind") or "")
        if not rid or rid in applicable or any(x["requirement_id"] == rid for x in exclusions):
            raise CompileError("REQUIREMENT_ID_INVALID_OR_DUPLICATE:" + rid)
        if source_kind not in {"schema", "standard", "feature_callout", "formula", "constraint"}:
            raise CompileError("REQUIREMENT_SOURCE_KIND_INVALID:" + rid)
        cond = row.get("applies_when")
        if _condition(cond, values):
            applicable[rid] = {"source_kind": source_kind}
        else:
            exclusions.append({
                "requirement_id": rid,
                "source_kind": source_kind,
                "reason": "APPLICABILITY_CONDITION_FALSE",
                "condition": dict(cond) if isinstance(cond, Mapping) else cond,
            })
    return applicable, sorted(exclusions, key=lambda x: x["requirement_id"])


def _choose_branch(branches: Any, values: Mapping[str, Any]) -> tuple[str, list[Mapping[str, Any]]]:
    if not isinstance(branches, list) or not branches:
        raise CompileError("BRANCHES_REQUIRED")
    matches = []
    for i, row in enumerate(branches):
        if not isinstance(row, Mapping):
            raise CompileError(f"BRANCH_INVALID:{i}")
        bid = str(row.get("id") or "")
        if not bid:
            raise CompileError("BRANCH_ID_INVALID")
        conds = row.get("when", [])
        if not isinstance(conds, list):
            raise CompileError("BRANCH_CONDITIONS_INVALID:" + bid)
        if all(_condition(c, values) for c in conds):
            matches.append(row)
    if len(matches) != 1:
        raise CompileError("BRANCH_SELECTION_NOT_UNIQUE:" + str(len(matches)))
    row = matches[0]
    rules = row.get("rules")
    if not isinstance(rules, list) or not rules:
        raise CompileError("BRANCH_RULES_MISSING:" + str(row.get("id")))
    return str(row["id"]), list(rules)


def _numeric(typ: str) -> bool:
    return typ in _NUMERIC


def _eval_rule(
    rule: Mapping[str, Any],
    known_meta: Mapping[str, Mapping[str, Any]],
    known_values: Mapping[str, Any],
) -> tuple[dict[str, Any], Any]:
    rid = str(rule.get("id") or "")
    op = str(rule.get("op") or "")
    inputs = rule.get("inputs")
    output = str(rule.get("output") or "")
    if not rid or not output or not isinstance(inputs, list) or not inputs or any(str(x) not in known_meta for x in inputs):
        raise CompileError("RULE_INPUT_OR_ID_INVALID:" + rid)
    input_ids = [str(x) for x in inputs]
    metas = [known_meta[x] for x in input_ids]
    vals = [known_values[x] for x in input_ids]

    if op in {"sum", "difference"}:
        if len(input_ids) != 2 or any(not _numeric(m["type"]) for m in metas) or metas[0]["dimension"] != metas[1]["dimension"]:
            raise CompileError("ADD_SUB_DIMENSION_OR_TYPE_INVALID:" + rid)
        value = vals[0] + vals[1] if op == "sum" else vals[0] - vals[1]
        out_type = "number"
        out_dim = metas[0]["dimension"]
    elif op == "ratio":
        if len(input_ids) != 2 or any(not _numeric(m["type"]) for m in metas) or metas[0]["dimension"] != metas[1]["dimension"]:
            raise CompileError("RATIO_DIMENSION_OR_TYPE_INVALID:" + rid)
        if float(vals[1]) == 0.0:
            raise CompileError("RATIO_DIVIDE_BY_ZERO:" + rid)
        value = float(vals[0]) / float(vals[1])
        out_type = "number"
        out_dim = "dimensionless"
    elif op == "scale":
        if len(input_ids) != 1 or not _numeric(metas[0]["type"]):
            raise CompileError("SCALE_TYPE_INVALID:" + rid)
        factor = rule.get("factor")
        if not isinstance(factor, (int, float)) or isinstance(factor, bool) or not math.isfinite(float(factor)):
            raise CompileError("SCALE_FACTOR_INVALID:" + rid)
        value = float(vals[0]) * float(factor)
        out_type = "number"
        out_dim = metas[0]["dimension"]
    elif op == "threshold_gt":
        if len(input_ids) != 1 or not _numeric(metas[0]["type"]):
            raise CompileError("THRESHOLD_TYPE_INVALID:" + rid)
        threshold = rule.get("threshold")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise CompileError("THRESHOLD_VALUE_INVALID:" + rid)
        value = float(vals[0]) > float(threshold)
        out_type = "boolean"
        out_dim = "dimensionless"
    elif op == "identity":
        if len(input_ids) != 1:
            raise CompileError("IDENTITY_ARITY_INVALID:" + rid)
        value = vals[0]
        out_type = str(metas[0]["type"])
        out_dim = str(metas[0]["dimension"])
    else:
        raise CompileError("RULE_OPERATION_UNSUPPORTED:" + rid + ":" + op)

    declared_type = str(rule.get("output_type") or "")
    declared_dim = str(rule.get("output_dimension") or "")
    if declared_type != out_type or declared_dim != out_dim:
        raise CompileError("DECLARED_OUTPUT_TYPE_OR_DIMENSION_MISMATCH:" + rid)

    invariants = rule.get("invariants", [])
    if not isinstance(invariants, list):
        raise CompileError("INVARIANTS_NOT_LIST:" + rid)
    normalized_inv = []
    for inv in invariants:
        if not isinstance(inv, Mapping):
            raise CompileError("INVARIANT_INVALID:" + rid)
        kind = str(inv.get("kind") or "")
        bound = inv.get("value")
        if kind in {"min", "max"}:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not isinstance(bound, (int, float)) or isinstance(bound, bool):
                raise CompileError("NUMERIC_INVARIANT_INVALID:" + rid)
            if kind == "min" and float(value) < float(bound):
                raise CompileError("INVARIANT_MIN_FAILED:" + rid)
            if kind == "max" and float(value) > float(bound):
                raise CompileError("INVARIANT_MAX_FAILED:" + rid)
        elif kind == "must_be_true":
            if value is not True:
                raise CompileError("INVARIANT_TRUE_FAILED:" + rid)
        else:
            raise CompileError("INVARIANT_KIND_UNSUPPORTED:" + rid)
        normalized_inv.append(dict(inv))

    node = {
        "rule_id": rid,
        "operation": op,
        "inputs": input_ids,
        "output": output,
        "output_type": out_type,
        "output_dimension": out_dim,
        "consumes_requirements": sorted(str(x) for x in rule.get("consumes_requirements", [])),
        "invariants": normalized_inv,
        "evaluated_value": value,
    }
    return node, value


def compile_graph(public: Mapping[str, Any]) -> dict[str, Any]:
    try:
        schema_meta, values = _schema(public.get("schema_fields"))
        applicable, exclusions = _requirements(public.get("requirements"), values)
        branch_id, pending = _choose_branch(public.get("branches"), values)

        common = public.get("common_rules", [])
        if not isinstance(common, list):
            raise CompileError("COMMON_RULES_INVALID")
        pending = list(common) + list(pending)

        known_meta: dict[str, dict[str, Any]] = {k: dict(v) for k, v in schema_meta.items()}
        known_values: dict[str, Any] = dict(values)
        nodes: list[dict[str, Any]] = []
        seen_rule_ids: set[str] = set()
        seen_outputs: set[str] = set()

        # Dependency-driven compilation allows rule order to be arbitrary.
        while pending:
            progressed = False
            rest = []
            for raw in pending:
                if not isinstance(raw, Mapping):
                    raise CompileError("RULE_NOT_OBJECT")
                rid = str(raw.get("id") or "")
                out_id = str(raw.get("output") or "")
                if rid in seen_rule_ids or out_id in seen_outputs or out_id in schema_meta:
                    raise CompileError("RULE_OR_OUTPUT_DUPLICATE:" + rid)
                inputs = raw.get("inputs")
                if not isinstance(inputs, list):
                    raise CompileError("RULE_INPUTS_NOT_LIST:" + rid)
                if not all(str(x) in known_meta for x in inputs):
                    rest.append(raw)
                    continue

                node, value = _eval_rule(raw, known_meta, known_values)
                for req in node["consumes_requirements"]:
                    if req not in applicable:
                        raise CompileError("RULE_CONSUMES_INAPPLICABLE_OR_UNKNOWN_REQUIREMENT:" + req)
                seen_rule_ids.add(rid)
                seen_outputs.add(out_id)
                known_meta[out_id] = {
                    "type": node["output_type"],
                    "dimension": node["output_dimension"],
                }
                known_values[out_id] = value
                nodes.append(node)
                progressed = True
            if not progressed:
                unresolved = sorted(str(x.get("id") or "") for x in rest if isinstance(x, Mapping))
                raise CompileError("RULE_DAG_UNRESOLVED:" + ",".join(unresolved))
            pending = rest

        consumers: dict[str, list[str]] = {rid: [] for rid in applicable}
        for node in nodes:
            for req in node["consumes_requirements"]:
                consumers[req].append(node["rule_id"])
        missing = sorted(rid for rid, rows in consumers.items() if not rows)
        if missing:
            raise CompileError("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER:" + ",".join(missing))

        lineage = [
            {
                "requirement_id": rid,
                "source_kind": applicable[rid]["source_kind"],
                "consumer_rule_ids": sorted(consumers[rid]),
            }
            for rid in sorted(applicable)
        ]

        requested_outputs = public.get("required_outputs")
        if not isinstance(requested_outputs, list) or not requested_outputs or any(str(x) not in known_meta for x in requested_outputs):
            raise CompileError("REQUIRED_OUTPUTS_INVALID")
        outputs = [
            {
                "id": str(oid),
                "type": known_meta[str(oid)]["type"],
                "dimension": known_meta[str(oid)]["dimension"],
                "value": known_values[str(oid)],
            }
            for oid in requested_outputs
        ]

        return {
            "schema": SCHEMA,
            "status": "COMPILED",
            "selected_branch_id": branch_id,
            "nodes": nodes,
            "requirement_lineage": lineage,
            "justified_exclusions": exclusions,
            "outputs": outputs,
            "terminal_authority": False,
            "capability_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
            "capability_credit_delta": 0,
        }

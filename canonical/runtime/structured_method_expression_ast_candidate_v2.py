"""Compositional typed-expression compiler for normalized structured methods.

This route stays inside the frozen contract boundary: rules are already normalized
and applicable semantics are explicit. Natural-language/unstated-rule extraction is
upstream and is not claimed here.
"""
from __future__ import annotations

from typing import Any, Mapping
import math
import re

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_EXPRESSION_AST_CANDIDATE_V2"
_NUMERIC = {"integer", "number"}
_DIM_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CompileError(ValueError):
    pass


def _dim_parse(raw: str) -> dict[str, int]:
    if raw == "dimensionless":
        return {}
    if not isinstance(raw, str) or not raw:
        raise CompileError("DIMENSION_INVALID")
    out: dict[str, int] = {}
    for term in raw.split("*"):
        bits = term.split("^", 1)
        unit = bits[0]
        if not _DIM_TOKEN.match(unit):
            raise CompileError("DIMENSION_TOKEN_INVALID:" + term)
        power = int(bits[1]) if len(bits) == 2 else 1
        if power:
            out[unit] = out.get(unit, 0) + power
            if out[unit] == 0:
                del out[unit]
    return out


def _dim_string(dim: Mapping[str, int]) -> str:
    if not dim:
        return "dimensionless"
    return "*".join(k if v == 1 else f"{k}^{v}" for k, v in sorted(dim.items()))


def _dim_mul(a: str, b: str, sign: int = 1) -> str:
    out = _dim_parse(a)
    for k, v in _dim_parse(b).items():
        out[k] = out.get(k, 0) + sign * v
        if out[k] == 0:
            del out[k]
    return _dim_string(out)


def _schema(rows: Any) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise CompileError("SCHEMA_FIELDS_REQUIRED")
    meta: dict[str, dict[str, str]] = {}
    vals: dict[str, Any] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompileError(f"SCHEMA_FIELD_INVALID:{i}")
        fid = str(row.get("id") or "")
        typ = str(row.get("type") or "")
        dim = str(row.get("dimension") or "")
        if not fid or fid in meta or typ not in {"integer", "number", "boolean", "enum"}:
            raise CompileError(f"SCHEMA_FIELD_DECLARATION_INVALID:{i}")
        dim = _dim_string(_dim_parse(dim))
        value = row.get("value")
        if typ == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value))):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "boolean" and not isinstance(value, bool):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ == "enum" and not isinstance(value, str):
            raise CompileError("SCHEMA_VALUE_TYPE_MISMATCH:" + fid)
        if typ in {"boolean", "enum"} and dim != "dimensionless":
            raise CompileError("NONNUMERIC_DIMENSION_MUST_BE_DIMENSIONLESS:" + fid)
        meta[fid] = {"type": typ, "dimension": dim}
        vals[fid] = value
    return meta, vals


def _refs(expr: Any) -> set[str]:
    if not isinstance(expr, Mapping):
        raise CompileError("EXPR_NOT_OBJECT")
    op = str(expr.get("op") or "")
    if op == "ref":
        rid = str(expr.get("id") or "")
        if not rid:
            raise CompileError("REF_ID_MISSING")
        return {rid}
    out: set[str] = set()
    for key in ("arg", "left", "right", "cond", "then", "else"):
        if key in expr:
            out |= _refs(expr[key])
    args = expr.get("args")
    if args is not None:
        if not isinstance(args, list):
            raise CompileError("EXPR_ARGS_NOT_LIST")
        for x in args:
            out |= _refs(x)
    return out


def _eval(expr: Mapping[str, Any], meta: Mapping[str, Mapping[str, str]], vals: Mapping[str, Any]) -> tuple[str, str, Any]:
    if not isinstance(expr, Mapping):
        raise CompileError("EXPR_NOT_OBJECT")
    op = str(expr.get("op") or "")

    if op == "ref":
        rid = str(expr.get("id") or "")
        if rid not in meta:
            raise CompileError("REF_UNKNOWN:" + rid)
        return str(meta[rid]["type"]), str(meta[rid]["dimension"]), vals[rid]

    if op == "const":
        typ = str(expr.get("type") or "")
        dim = _dim_string(_dim_parse(str(expr.get("dimension") or "")))
        value = expr.get("value")
        if typ == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise CompileError("CONST_NUMBER_INVALID")
            return "number", dim, float(value)
        if typ == "boolean":
            if not isinstance(value, bool) or dim != "dimensionless":
                raise CompileError("CONST_BOOLEAN_INVALID")
            return "boolean", dim, value
        if typ == "enum":
            if not isinstance(value, str) or dim != "dimensionless":
                raise CompileError("CONST_ENUM_INVALID")
            return "enum", dim, value
        raise CompileError("CONST_TYPE_INVALID")

    def one(key: str = "arg"):
        x = expr.get(key)
        if not isinstance(x, Mapping):
            raise CompileError("EXPR_CHILD_MISSING:" + key)
        return _eval(x, meta, vals)

    def two():
        l = expr.get("left"); r = expr.get("right")
        if not isinstance(l, Mapping) or not isinstance(r, Mapping):
            raise CompileError("EXPR_BINARY_CHILD_MISSING")
        return _eval(l, meta, vals), _eval(r, meta, vals)

    if op in {"add", "sub", "min", "max"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CompileError("ARITHMETIC_TYPE_OR_DIMENSION_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        value = {"add": av + bv, "sub": av - bv, "min": min(av, bv), "max": max(av, bv)}[op]
        return "number", a[1], value

    if op in {"mul", "div"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC:
            raise CompileError("MULDIV_TYPE_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        if op == "div" and bv == 0.0:
            raise CompileError("DIVIDE_BY_ZERO")
        return "number", _dim_mul(a[1], b[1], -1 if op == "div" else 1), av / bv if op == "div" else av * bv

    if op in {"neg", "abs"}:
        a = one()
        if a[0] not in _NUMERIC:
            raise CompileError("UNARY_NUMERIC_TYPE_INVALID:" + op)
        av = float(a[2])
        return "number", a[1], -av if op == "neg" else abs(av)

    if op == "pow_int":
        a = one()
        power = expr.get("power")
        if a[0] not in _NUMERIC or not isinstance(power, int) or isinstance(power, bool):
            raise CompileError("POW_INT_INVALID")
        dim = {k: v * power for k, v in _dim_parse(a[1]).items() if v * power}
        return "number", _dim_string(dim), float(a[2]) ** power

    if op in {"exp", "log", "sqrt"}:
        a = one()
        if a[0] not in _NUMERIC or a[1] != "dimensionless":
            raise CompileError("TRANSCENDENTAL_REQUIRES_DIMENSIONLESS:" + op)
        av = float(a[2])
        if op == "log":
            if av <= 0.0:
                raise CompileError("LOG_DOMAIN")
            value = math.log(av)
        elif op == "sqrt":
            if av < 0.0:
                raise CompileError("SQRT_DOMAIN")
            value = math.sqrt(av)
        else:
            value = math.exp(av)
        if not math.isfinite(value):
            raise CompileError("TRANSCENDENTAL_NONFINITE:" + op)
        return "number", "dimensionless", value

    if op in {"gt", "ge", "lt", "le"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CompileError("ORDER_TYPE_OR_DIMENSION_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        value = {"gt": av > bv, "ge": av >= bv, "lt": av < bv, "le": av <= bv}[op]
        return "boolean", "dimensionless", value

    if op == "isclose":
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CompileError("ISCLOSE_TYPE_OR_DIMENSION_INVALID")
        rel_tol = expr.get("rel_tol", 1e-12)
        abs_tol = expr.get("abs_tol", 0.0)
        if (
            not isinstance(rel_tol, (int, float)) or isinstance(rel_tol, bool)
            or not isinstance(abs_tol, (int, float)) or isinstance(abs_tol, bool)
            or not math.isfinite(float(rel_tol)) or not math.isfinite(float(abs_tol))
            or float(rel_tol) < 0.0 or float(abs_tol) < 0.0
        ):
            raise CompileError("ISCLOSE_TOLERANCE_INVALID")
        return "boolean", "dimensionless", math.isclose(
            float(a[2]), float(b[2]), rel_tol=float(rel_tol), abs_tol=float(abs_tol)
        )

    if op in {"eq", "neq"}:
        a, b = two()
        if a[0] != b[0] or a[1] != b[1]:
            raise CompileError("EQUALITY_TYPE_OR_DIMENSION_INVALID")
        value = a[2] == b[2]
        return "boolean", "dimensionless", value if op == "eq" else not value

    if op in {"and", "or"}:
        args = expr.get("args")
        if not isinstance(args, list) or len(args) < 2:
            raise CompileError("BOOLEAN_ARGS_INVALID:" + op)
        rows = [_eval(x, meta, vals) for x in args]
        if any(t != "boolean" or d != "dimensionless" for t, d, _ in rows):
            raise CompileError("BOOLEAN_TYPE_INVALID:" + op)
        booleans = [bool(v) for _, _, v in rows]
        return "boolean", "dimensionless", all(booleans) if op == "and" else any(booleans)

    if op == "not":
        a = one()
        if a[0] != "boolean" or a[1] != "dimensionless":
            raise CompileError("NOT_TYPE_INVALID")
        return "boolean", "dimensionless", not bool(a[2])

    if op == "if":
        c = one("cond")
        t = one("then")
        e = one("else")
        if c[0] != "boolean" or c[1] != "dimensionless":
            raise CompileError("IF_CONDITION_INVALID")
        if t[0] != e[0] or t[1] != e[1]:
            raise CompileError("IF_BRANCH_TYPE_OR_DIMENSION_MISMATCH")
        return t if c[2] else e

    raise CompileError("EXPR_OPERATION_UNSUPPORTED:" + op)


def _requirements(rows: Any, meta: Mapping[str, Mapping[str, str]], vals: Mapping[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    if not isinstance(rows, list) or not rows:
        raise CompileError("REQUIREMENTS_REQUIRED")
    applicable: dict[str, str] = {}
    exclusions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompileError(f"REQUIREMENT_INVALID:{i}")
        rid = str(row.get("id") or "")
        kind = str(row.get("source_kind") or "")
        if not rid or rid in seen or kind not in {"schema", "standard", "feature_callout", "formula", "constraint"}:
            raise CompileError("REQUIREMENT_DECLARATION_INVALID:" + rid)
        seen.add(rid)
        cond = row.get("applies_when")
        applies = True
        if cond is not None:
            typ, dim, value = _eval(cond, meta, vals)
            if typ != "boolean" or dim != "dimensionless":
                raise CompileError("REQUIREMENT_CONDITION_NOT_BOOLEAN:" + rid)
            applies = bool(value)
        if applies:
            applicable[rid] = kind
        else:
            exclusions.append({"requirement_id": rid, "source_kind": kind, "reason": "APPLICABILITY_CONDITION_FALSE"})
    return applicable, sorted(exclusions, key=lambda x: x["requirement_id"])


def _choose_branch(branches: Any, meta: Mapping[str, Mapping[str, str]], vals: Mapping[str, Any]) -> tuple[str, list[Mapping[str, Any]]]:
    if not isinstance(branches, list) or not branches:
        raise CompileError("BRANCHES_REQUIRED")
    matches = []
    for row in branches:
        if not isinstance(row, Mapping):
            raise CompileError("BRANCH_INVALID")
        bid = str(row.get("id") or "")
        when = row.get("when")
        if not bid or not isinstance(when, Mapping):
            raise CompileError("BRANCH_DECLARATION_INVALID")
        typ, dim, value = _eval(when, meta, vals)
        if typ != "boolean" or dim != "dimensionless":
            raise CompileError("BRANCH_CONDITION_NOT_BOOLEAN:" + bid)
        if value:
            matches.append(row)
    if len(matches) != 1:
        raise CompileError("BRANCH_SELECTION_NOT_UNIQUE:" + str(len(matches)))
    rules = matches[0].get("rules")
    if not isinstance(rules, list):
        raise CompileError("BRANCH_RULES_INVALID")
    return str(matches[0]["id"]), list(rules)


def compile_graph(public: Mapping[str, Any]) -> dict[str, Any]:
    try:
        meta, vals = _schema(public.get("schema_fields"))
        applicable, exclusions = _requirements(public.get("requirements"), meta, vals)
        branch_id, branch_rules = _choose_branch(public.get("branches"), meta, vals)
        common = public.get("common_rules", [])
        if not isinstance(common, list):
            raise CompileError("COMMON_RULES_INVALID")
        pending = list(common) + branch_rules
        nodes: list[dict[str, Any]] = []
        seen_rule_ids: set[str] = set()
        outputs_seen: set[str] = set()

        while pending:
            progressed = False
            rest = []
            for raw in pending:
                if not isinstance(raw, Mapping):
                    raise CompileError("RULE_NOT_OBJECT")
                rid = str(raw.get("id") or "")
                out = str(raw.get("output") or "")
                expr = raw.get("expr")
                if not rid or not out or not isinstance(expr, Mapping):
                    raise CompileError("RULE_DECLARATION_INVALID")
                if rid in seen_rule_ids or out in outputs_seen or out in meta:
                    raise CompileError("RULE_OR_OUTPUT_DUPLICATE:" + rid)
                refs = _refs(expr)
                if not refs.issubset(meta):
                    rest.append(raw)
                    continue
                typ, dim, value = _eval(expr, meta, vals)
                decl_t = str(raw.get("output_type") or "")
                decl_d = _dim_string(_dim_parse(str(raw.get("output_dimension") or "")))
                if typ != decl_t or dim != decl_d:
                    raise CompileError("DECLARED_OUTPUT_TYPE_OR_DIMENSION_MISMATCH:" + rid)
                consumes = sorted(str(x) for x in raw.get("consumes_requirements", []))
                if any(x not in applicable for x in consumes):
                    raise CompileError("RULE_CONSUMES_INAPPLICABLE_OR_UNKNOWN_REQUIREMENT:" + rid)
                meta[out] = {"type": typ, "dimension": dim}
                vals[out] = value
                invariants = raw.get("invariants", [])
                if not isinstance(invariants, list):
                    raise CompileError("INVARIANTS_NOT_LIST:" + rid)
                normalized_inv = []
                for inv in invariants:
                    if not isinstance(inv, Mapping):
                        raise CompileError("INVARIANT_INVALID:" + rid)
                    it, idim, iv = _eval(inv, meta, vals)
                    if it != "boolean" or idim != "dimensionless" or iv is not True:
                        raise CompileError("INVARIANT_FAILED:" + rid)
                    normalized_inv.append(dict(inv))
                nodes.append({
                    "rule_id": rid,
                    "expression": dict(expr),
                    "output": out,
                    "output_type": typ,
                    "output_dimension": dim,
                    "consumes_requirements": consumes,
                    "invariants": normalized_inv,
                    "evaluated_value": value,
                })
                seen_rule_ids.add(rid)
                outputs_seen.add(out)
                progressed = True
            if not progressed:
                unresolved = sorted(str(x.get("id") or "") for x in rest if isinstance(x, Mapping))
                raise CompileError("RULE_DAG_UNRESOLVED:" + ",".join(unresolved))
            pending = rest

        consumers: dict[str, list[str]] = {rid: [] for rid in applicable}
        for node in nodes:
            for req in node["consumes_requirements"]:
                consumers[req].append(node["rule_id"])
        missing = sorted(rid for rid, xs in consumers.items() if not xs)
        if missing:
            raise CompileError("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER:" + ",".join(missing))
        lineage = [{
            "requirement_id": rid,
            "source_kind": applicable[rid],
            "consumer_rule_ids": sorted(consumers[rid]),
        } for rid in sorted(applicable)]

        requested = public.get("required_outputs")
        if not isinstance(requested, list) or not requested or any(str(x) not in meta for x in requested):
            raise CompileError("REQUIRED_OUTPUTS_INVALID")
        outputs = [{
            "id": str(oid),
            "type": meta[str(oid)]["type"],
            "dimension": meta[str(oid)]["dimension"],
            "value": vals[str(oid)],
        } for oid in requested]

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

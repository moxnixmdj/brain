from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime.structured_method_expression_ast_candidate_v2 import compile_graph

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_INDEPENDENT_SEMANTIC_CHECKER_V1"
_NUMERIC = {"integer", "number"}


class CheckError(ValueError):
    pass


def _dim_parse(raw: str) -> dict[str, int]:
    if raw == "dimensionless":
        return {}
    if not isinstance(raw, str) or not raw:
        raise CheckError("DIMENSION_INVALID")
    out: dict[str, int] = {}
    for term in raw.split("*"):
        bits = term.split("^", 1)
        unit = bits[0]
        if not unit or not (unit[0].isalpha() or unit[0] == "_") or not all(c.isalnum() or c == "_" for c in unit):
            raise CheckError("DIMENSION_TOKEN_INVALID:" + term)
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


def _refs(expr: Any) -> set[str]:
    if not isinstance(expr, Mapping):
        raise CheckError("EXPR_NOT_OBJECT")
    if expr.get("op") == "ref":
        rid = str(expr.get("id") or "")
        if not rid:
            raise CheckError("REF_ID_MISSING")
        return {rid}
    out: set[str] = set()
    for key in ("arg", "left", "right", "cond", "then", "else"):
        if key in expr:
            out |= _refs(expr[key])
    args = expr.get("args")
    if args is not None:
        if not isinstance(args, list):
            raise CheckError("ARGS_NOT_LIST")
        for row in args:
            out |= _refs(row)
    return out


def _constants(expr: Any) -> list[Any]:
    if not isinstance(expr, Mapping):
        return []
    out: list[Any] = []
    if expr.get("op") == "const":
        out.append(expr.get("value"))
    for key in ("arg", "left", "right", "cond", "then", "else"):
        if key in expr:
            out.extend(_constants(expr[key]))
    args = expr.get("args")
    if isinstance(args, list):
        for row in args:
            out.extend(_constants(row))
    return out


def _eval(expr: Mapping[str, Any], meta: Mapping[str, Mapping[str, str]], vals: Mapping[str, Any]) -> tuple[str, str, Any]:
    if not isinstance(expr, Mapping):
        raise CheckError("EXPR_NOT_OBJECT")
    op = str(expr.get("op") or "")
    if op == "ref":
        rid = str(expr.get("id") or "")
        if rid not in meta or rid not in vals:
            raise CheckError("REF_UNKNOWN:" + rid)
        return str(meta[rid]["type"]), str(meta[rid]["dimension"]), vals[rid]
    if op == "const":
        typ = str(expr.get("type") or "")
        dim = _dim_string(_dim_parse(str(expr.get("dimension") or "")))
        value = expr.get("value")
        if typ == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise CheckError("CONST_NUMBER_INVALID")
            return "number", dim, float(value)
        if typ == "boolean":
            if not isinstance(value, bool) or dim != "dimensionless":
                raise CheckError("CONST_BOOLEAN_INVALID")
            return "boolean", dim, value
        if typ == "enum":
            if not isinstance(value, str) or dim != "dimensionless":
                raise CheckError("CONST_ENUM_INVALID")
            return "enum", dim, value
        raise CheckError("CONST_TYPE_INVALID")

    def one(key: str = "arg"):
        x = expr.get(key)
        if not isinstance(x, Mapping):
            raise CheckError("CHILD_MISSING:" + key)
        return _eval(x, meta, vals)

    def two():
        left = expr.get("left")
        right = expr.get("right")
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            raise CheckError("BINARY_CHILD_MISSING")
        return _eval(left, meta, vals), _eval(right, meta, vals)

    if op in {"add", "sub", "min", "max"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CheckError("ARITHMETIC_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        return "number", a[1], {"add": av+bv, "sub": av-bv, "min": min(av,bv), "max": max(av,bv)}[op]
    if op in {"mul", "div"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC:
            raise CheckError("MULDIV_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        if op == "div" and bv == 0.0:
            raise CheckError("DIVIDE_BY_ZERO")
        return "number", _dim_mul(a[1], b[1], -1 if op == "div" else 1), av / bv if op == "div" else av * bv
    if op in {"neg", "abs"}:
        a = one()
        if a[0] not in _NUMERIC:
            raise CheckError("UNARY_INVALID:" + op)
        av = float(a[2])
        return "number", a[1], -av if op == "neg" else abs(av)
    if op == "pow_int":
        a = one()
        p = expr.get("power")
        if a[0] not in _NUMERIC or not isinstance(p, int) or isinstance(p, bool):
            raise CheckError("POW_INVALID")
        d = {k: v*p for k, v in _dim_parse(a[1]).items() if v*p}
        return "number", _dim_string(d), float(a[2]) ** p
    if op in {"exp", "log", "sqrt"}:
        a = one()
        if a[0] not in _NUMERIC or a[1] != "dimensionless":
            raise CheckError("TRANSCENDENTAL_INVALID:" + op)
        av = float(a[2])
        if op == "log":
            if av <= 0: raise CheckError("LOG_DOMAIN")
            value = math.log(av)
        elif op == "sqrt":
            if av < 0: raise CheckError("SQRT_DOMAIN")
            value = math.sqrt(av)
        else:
            value = math.exp(av)
        if not math.isfinite(value):
            raise CheckError("NONFINITE:" + op)
        return "number", "dimensionless", value
    if op in {"gt", "ge", "lt", "le"}:
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CheckError("ORDER_INVALID:" + op)
        av, bv = float(a[2]), float(b[2])
        return "boolean", "dimensionless", {"gt": av>bv, "ge": av>=bv, "lt": av<bv, "le": av<=bv}[op]
    if op == "isclose":
        a, b = two()
        if a[0] not in _NUMERIC or b[0] not in _NUMERIC or a[1] != b[1]:
            raise CheckError("ISCLOSE_INVALID")
        rt, at = expr.get("rel_tol", 1e-12), expr.get("abs_tol", 0.0)
        if not isinstance(rt, (int,float)) or isinstance(rt,bool) or not isinstance(at,(int,float)) or isinstance(at,bool):
            raise CheckError("ISCLOSE_TOLERANCE_INVALID")
        return "boolean", "dimensionless", math.isclose(float(a[2]), float(b[2]), rel_tol=float(rt), abs_tol=float(at))
    if op in {"eq", "neq"}:
        a, b = two()
        if a[0] != b[0] or a[1] != b[1]:
            raise CheckError("EQUALITY_INVALID")
        eq = a[2] == b[2]
        return "boolean", "dimensionless", eq if op == "eq" else not eq
    if op in {"and", "or"}:
        args = expr.get("args")
        if not isinstance(args, list) or len(args) < 2:
            raise CheckError("BOOLEAN_ARGS_INVALID")
        rows = [_eval(x, meta, vals) for x in args]
        if any(t != "boolean" or d != "dimensionless" for t,d,_ in rows):
            raise CheckError("BOOLEAN_TYPE_INVALID")
        vs = [bool(v) for _,_,v in rows]
        return "boolean", "dimensionless", all(vs) if op == "and" else any(vs)
    if op == "not":
        a = one()
        if a[0] != "boolean" or a[1] != "dimensionless":
            raise CheckError("NOT_INVALID")
        return "boolean", "dimensionless", not bool(a[2])
    if op == "if":
        c = one("cond"); t = one("then"); e = one("else")
        if c[0] != "boolean" or c[1] != "dimensionless" or t[0] != e[0] or t[1] != e[1]:
            raise CheckError("IF_INVALID")
        return t if c[2] else e
    raise CheckError("OP_UNSUPPORTED:" + op)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
        except Exception:
            return False
    return a == b


def _alternates(typ: str, current: Any, expr: Mapping[str, Any]) -> list[Any]:
    if typ == "boolean":
        return [not bool(current)]
    if typ == "enum":
        vals = [x for x in _constants(expr) if isinstance(x, str) and x != current]
        vals.append("__BRAIN_EDGE_ALT__" if current != "__BRAIN_EDGE_ALT__" else "__BRAIN_EDGE_ALT_2__")
        return vals
    if typ == "integer":
        c = int(current)
        vals = [0, 1, -1, c+1, c-1, c*2, -c]
        vals += [int(x) for x in _constants(expr) if isinstance(x, int) and not isinstance(x, bool)]
        return list(dict.fromkeys(x for x in vals if x != c))
    if typ == "number":
        c = float(current)
        vals = [0.0, 1.0, -1.0, c+1.0, c-1.0, c*2.0, -c]
        for k in range(-6, 7):
            vals.extend([10.0**k, -(10.0**k)])
        vals += [float(x) for x in _constants(expr) if isinstance(x, (int,float)) and not isinstance(x,bool)]
        return list(dict.fromkeys(x for x in vals if math.isfinite(x) and x != c))
    return []


def verify(public: Mapping[str, Any]) -> dict[str, Any]:
    compiled = compile_graph(public)
    if compiled.get("status") != "COMPILED":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "reason": "PRIMARY_COMPILER_REJECTED:" + str(compiled.get("reason") or ""), "terminal_authority": False}

    try:
        fields = public.get("schema_fields")
        if not isinstance(fields, list) or not fields:
            raise CheckError("SCHEMA_FIELDS_REQUIRED")
        meta: dict[str, dict[str, str]] = {}
        vals: dict[str, Any] = {}
        for row in fields:
            if not isinstance(row, Mapping):
                raise CheckError("SCHEMA_FIELD_INVALID")
            fid = str(row.get("id") or "")
            if not fid or fid in meta:
                raise CheckError("SCHEMA_FIELD_ID_INVALID")
            typ = str(row.get("type") or "")
            dim = _dim_string(_dim_parse(str(row.get("dimension") or "")))
            meta[fid] = {"type": typ, "dimension": dim}
            vals[fid] = row.get("value")

        edge_witnesses: list[dict[str, Any]] = []
        invariant_checks = 0
        for node in compiled.get("nodes", []):
            if not isinstance(node, Mapping):
                raise CheckError("NODE_INVALID")
            rid = str(node.get("rule_id") or "")
            out = str(node.get("output") or "")
            expr = node.get("expression")
            if not rid or not out or not isinstance(expr, Mapping):
                raise CheckError("NODE_FIELDS_INVALID")

            typ, dim, value = _eval(expr, meta, vals)
            if typ != str(node.get("output_type") or "") or dim != str(node.get("output_dimension") or "") or not _same(value, node.get("evaluated_value")):
                raise CheckError("INDEPENDENT_EVALUATOR_DIVERGENCE:" + rid)

            refs = sorted(_refs(expr))
            for ref in refs:
                if ref not in meta or ref not in vals:
                    raise CheckError("EDGE_REF_UNKNOWN:" + rid + ":" + ref)
                witness = None
                for alt in _alternates(meta[ref]["type"], vals[ref], expr):
                    trial = dict(vals)
                    trial[ref] = alt
                    try:
                        t2, d2, v2 = _eval(expr, meta, trial)
                    except Exception:
                        continue
                    if t2 == typ and d2 == dim and not _same(v2, value):
                        witness = {"rule_id": rid, "ref_id": ref, "from": vals[ref], "to": alt, "output_from": value, "output_to": v2}
                        break
                if witness is None:
                    raise CheckError("NO_INDEPENDENT_EDGE_SENSITIVITY_WITNESS:" + rid + ":" + ref)
                edge_witnesses.append(witness)

            meta[out] = {"type": typ, "dimension": dim}
            vals[out] = value
            for inv in node.get("invariants", []):
                if not isinstance(inv, Mapping):
                    raise CheckError("INVARIANT_INVALID:" + rid)
                it, idim, iv = _eval(inv, meta, vals)
                if it != "boolean" or idim != "dimensionless" or iv is not True:
                    raise CheckError("INDEPENDENT_INVARIANT_FAILED:" + rid)
                invariant_checks += 1

        return {
            "schema": SCHEMA,
            "status": "PASS__INDEPENDENT_TYPED_SEMANTIC_CHECKS",
            "pass": True,
            "selected_branch_id": compiled.get("selected_branch_id"),
            "rule_count": len(compiled.get("nodes", [])),
            "material_edge_count": len(edge_witnesses),
            "invariant_check_count": invariant_checks,
            "edge_sensitivity_witnesses": edge_witnesses,
            "requirement_lineage": compiled.get("requirement_lineage", []),
            "outputs": compiled.get("outputs", []),
            "terminal_authority": False,
        }
    except Exception as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "reason": type(exc).__name__ + ":" + str(exc), "terminal_authority": False}

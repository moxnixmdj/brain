"""Fail-closed semantic certificate verifier for the typed structured-method stratum.

This module does not import the Brain candidate compiler.  It reuses the already
independent expression-AST evaluator as the semantic kernel, then requires one
counterfactual witness for every rule-expression source reference.  The witness
must preserve the source type and must make the rule denotation change.

The result is deliberately narrow:
- executable invariants are re-evaluated and must be true;
- every admitted material expression edge gets a semantic consequence witness;
- opaque operators / prose invariants are not admitted;
- no whole-leaf or family credit follows without a separate coverage proof.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime.structured_method_expression_ast_proof_v2 import (
    _dim_parse,
    _dim_string,
    _eval,
)

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_EDGE_CONSEQUENCE_CERTIFICATE_V1"


class CertificateError(ValueError):
    pass


def _refs(expr: Mapping[str, Any]) -> set[str]:
    if not isinstance(expr, Mapping):
        raise CertificateError("EXPR_NOT_OBJECT")
    op = expr.get("op")
    if op == "ref":
        rid = expr.get("id")
        if not isinstance(rid, str) or not rid:
            raise CertificateError("REF_ID_INVALID")
        return {rid}
    out: set[str] = set()
    for key in ("arg", "left", "right", "cond", "then", "else"):
        child = expr.get(key)
        if child is not None:
            if not isinstance(child, Mapping):
                raise CertificateError("EXPR_CHILD_INVALID:" + key)
            out |= _refs(child)
    args = expr.get("args")
    if args is not None:
        if not isinstance(args, list):
            raise CertificateError("EXPR_ARGS_INVALID")
        for child in args:
            if not isinstance(child, Mapping):
                raise CertificateError("EXPR_ARG_INVALID")
            out |= _refs(child)
    return out


def _same_value(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def _schema(case: Mapping[str, Any]) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    rows = case.get("schema_fields")
    if not isinstance(rows, list) or not rows:
        raise CertificateError("SCHEMA_FIELDS_REQUIRED")
    meta: dict[str, dict[str, str]] = {}
    vals: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CertificateError("SCHEMA_FIELD_INVALID")
        rid = row.get("id")
        typ = row.get("type")
        dim = row.get("dimension")
        if not isinstance(rid, str) or not rid or rid in meta:
            raise CertificateError("SCHEMA_FIELD_ID_INVALID")
        if typ not in {"number", "integer", "boolean", "enum"}:
            raise CertificateError("SCHEMA_FIELD_TYPE_INVALID:" + rid)
        if not isinstance(dim, str) or not dim:
            raise CertificateError("SCHEMA_FIELD_DIMENSION_INVALID:" + rid)
        meta[rid] = {"type": str(typ), "dimension": _dim_string(_dim_parse(dim))}
        vals[rid] = row.get("value")
    return meta, vals


def _select_rules(
    case: Mapping[str, Any],
    meta: Mapping[str, Mapping[str, str]],
    vals: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    branches = case.get("branches")
    common = case.get("common_rules", [])
    if not isinstance(common, list) or not isinstance(branches, list) or not branches:
        raise CertificateError("RULE_COLLECTIONS_INVALID")
    matches: list[Mapping[str, Any]] = []
    for branch in branches:
        if not isinstance(branch, Mapping) or not isinstance(branch.get("when"), Mapping):
            raise CertificateError("BRANCH_INVALID")
        typ, dim, value = _eval(branch["when"], meta, vals)
        if typ != "boolean" or dim != "dimensionless":
            raise CertificateError("BRANCH_CONDITION_INVALID")
        if value is True:
            matches.append(branch)
    if len(matches) != 1:
        raise CertificateError("BRANCH_SELECTION_NOT_UNIQUE:" + str(len(matches)))
    selected = matches[0].get("rules")
    if not isinstance(selected, list):
        raise CertificateError("BRANCH_RULES_INVALID")
    return [*common, *selected]


def _validate_alternate(
    source_id: str,
    alternate: Any,
    meta: Mapping[str, Mapping[str, str]],
    baseline: Any,
) -> None:
    typ = meta[source_id]["type"]
    if typ in {"number", "integer"}:
        if not isinstance(alternate, (int, float)) or isinstance(alternate, bool):
            raise CertificateError("ALTERNATE_NUMERIC_TYPE:" + source_id)
        if not math.isfinite(float(alternate)):
            raise CertificateError("ALTERNATE_NONFINITE:" + source_id)
        if typ == "integer" and (not isinstance(alternate, int) or isinstance(alternate, bool)):
            raise CertificateError("ALTERNATE_INTEGER_TYPE:" + source_id)
    elif typ == "boolean":
        if not isinstance(alternate, bool):
            raise CertificateError("ALTERNATE_BOOLEAN_TYPE:" + source_id)
    elif typ == "enum":
        if not isinstance(alternate, str):
            raise CertificateError("ALTERNATE_ENUM_TYPE:" + source_id)
    else:
        raise CertificateError("ALTERNATE_TYPE_UNSUPPORTED:" + source_id)
    if _same_value(alternate, baseline):
        raise CertificateError("ALTERNATE_EQUALS_BASELINE:" + source_id)


def verify(
    case: Mapping[str, Any],
    certificates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        if not isinstance(case, Mapping):
            raise CertificateError("CASE_NOT_OBJECT")
        if not isinstance(certificates, list):
            raise CertificateError("CERTIFICATES_NOT_LIST")

        meta, vals = _schema(case)
        pending = list(_select_rules(case, meta, vals))
        rule_rows: list[dict[str, Any]] = []

        # First independently evaluate the admitted typed semantics and all invariants.
        while pending:
            progressed = False
            rest: list[Mapping[str, Any]] = []
            for rule in pending:
                if not isinstance(rule, Mapping):
                    raise CertificateError("RULE_INVALID")
                rid = rule.get("id")
                out = rule.get("output")
                expr = rule.get("expr")
                if not isinstance(rid, str) or not rid or not isinstance(out, str) or not out:
                    raise CertificateError("RULE_ID_OR_OUTPUT_INVALID")
                if not isinstance(expr, Mapping):
                    raise CertificateError("OPAQUE_RULE_NOT_ADMITTED:" + str(rid))
                refs = _refs(expr)
                if not refs.issubset(meta):
                    rest.append(rule)
                    continue
                typ, dim, value = _eval(expr, meta, vals)
                declared_type = rule.get("output_type")
                declared_dim = rule.get("output_dimension")
                if typ != declared_type or dim != _dim_string(_dim_parse(str(declared_dim))):
                    raise CertificateError("OUTPUT_SEMANTICS_MISMATCH:" + rid)
                meta[out] = {"type": typ, "dimension": dim}
                vals[out] = value

                invs = rule.get("invariants", [])
                if not isinstance(invs, list):
                    raise CertificateError("INVARIANTS_NOT_LIST:" + rid)
                for inv in invs:
                    if not isinstance(inv, Mapping):
                        raise CertificateError("OPAQUE_INVARIANT_NOT_ADMITTED:" + rid)
                    it, idim, iv = _eval(inv, meta, vals)
                    if it != "boolean" or idim != "dimensionless" or iv is not True:
                        raise CertificateError("INVARIANT_SEMANTIC_FAILURE:" + rid)

                rule_rows.append({
                    "rule_id": rid,
                    "output": out,
                    "expr": expr,
                    "refs": sorted(refs),
                    "baseline_output": value,
                })
                progressed = True
            if not progressed:
                unresolved = sorted(str(x.get("id") or "") for x in rest)
                raise CertificateError("RULE_DAG_UNRESOLVED:" + ",".join(unresolved))
            pending = rest

        # Certificates must be exact: one per semantic source edge, no extras.
        cert_map: dict[tuple[str, str], Mapping[str, Any]] = {}
        for cert in certificates:
            if not isinstance(cert, Mapping):
                raise CertificateError("CERTIFICATE_INVALID")
            rid = cert.get("rule_id")
            sid = cert.get("source_id")
            if not isinstance(rid, str) or not isinstance(sid, str):
                raise CertificateError("CERTIFICATE_ID_INVALID")
            key = (rid, sid)
            if key in cert_map:
                raise CertificateError("DUPLICATE_CERTIFICATE:" + rid + ":" + sid)
            cert_map[key] = cert

        required = {
            (row["rule_id"], sid)
            for row in rule_rows
            for sid in row["refs"]
        }
        if set(cert_map) != required:
            missing = sorted(required - set(cert_map))
            extra = sorted(set(cert_map) - required)
            raise CertificateError("CERTIFICATE_COVERAGE_MISMATCH:missing=" + repr(missing) + ":extra=" + repr(extra))

        # Re-evaluate each rule with only the certified source changed.
        checked = 0
        by_rule = {row["rule_id"]: row for row in rule_rows}
        for key in sorted(required):
            rid, sid = key
            row = by_rule[rid]
            cert = cert_map[key]
            alternate = cert.get("alternate_value")
            _validate_alternate(sid, alternate, meta, vals[sid])
            mutated = dict(vals)
            mutated[sid] = alternate
            mtyp, mdim, mvalue = _eval(row["expr"], meta, mutated)
            if mtyp != meta[row["output"]]["type"] or mdim != meta[row["output"]]["dimension"]:
                raise CertificateError("MUTATED_OUTPUT_TYPE_OR_DIMENSION_DRIFT:" + rid + ":" + sid)
            if _same_value(mvalue, row["baseline_output"]):
                raise CertificateError("NO_SEMANTIC_EDGE_CONSEQUENCE:" + rid + ":" + sid)
            checked += 1

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "typed_semantic_rule_count": len(rule_rows),
            "semantic_edge_witness_count": checked,
            "invariant_semantics_checked": True,
            "edge_consequence_coverage_complete": True,
            "whole_leaf_credit": False,
            "capability_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "whole_leaf_credit": False,
            "capability_credit_delta": 0,
        }

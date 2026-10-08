"""Exhaustive truth-table checker for one explicitly bounded Boolean cover.

Unlike receipt-shape gates, this module recomputes the logical statement from
the supplied formulas. It NEVER certifies that the finite model equals the
terminal observable trace universe or that a supplied adequacy formula faithfully
represents real-world route competence.

The only proved conditional facts are, within the declared finite Boolean
space: (1) every admitted route satisfies its declared adequacy formula on
the scope, and (2) every in-scope assignment activates some admitted route.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINITE_SYMBOLIC_COVER_PROOF_CHECKER_V1"
MAX_VARS = 12
MAX_ROUTES = 64
MAX_AST_NODES = 512
MAX_AST_DEPTH = 32
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")


class MalformedFormula(ValueError):
    pass


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": status == "PASS__EXACT_FINITE_FORMULA_COVER_VERIFIED",
        "finite_formula_cover_proved": status == "PASS__EXACT_FINITE_FORMULA_COVER_VERIFIED",
        "scope_is_entire_terminal_universe_proved": False,
        "route_real_world_adequacy_proved": False,
        "brain_route_ownership_proved": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _parse(expr: Any, symbols: frozenset[str], budget: list[int], depth: int = 0):
    budget[0] += 1
    if budget[0] > MAX_AST_NODES:
        raise MalformedFormula("AST_NODE_LIMIT")
    if depth > MAX_AST_DEPTH:
        raise MalformedFormula("AST_DEPTH_LIMIT")
    if type(expr) is not list or not expr or type(expr[0]) is not str:
        raise MalformedFormula("INVALID_FORMULA_NODE")
    op = expr[0]
    if op == "const":
        if len(expr) != 2 or type(expr[1]) is not bool:
            raise MalformedFormula("INVALID_BOOLEAN_CONSTANT")
        return ("const", expr[1])
    if op == "var":
        if len(expr) != 2 or type(expr[1]) is not str or expr[1] not in symbols:
            raise MalformedFormula("UNKNOWN_FORMULA_VARIABLE")
        return ("var", expr[1])
    if op == "not":
        if len(expr) != 2:
            raise MalformedFormula("INVALID_NOT_ARITY")
        return ("not", _parse(expr[1], symbols, budget, depth + 1))
    if op in ("and", "or"):
        if len(expr) < 3:
            raise MalformedFormula("INVALID_AND_OR_ARITY")
        return (op, tuple(_parse(x, symbols, budget, depth + 1) for x in expr[1:]))
    raise MalformedFormula("UNKNOWN_FORMULA_OPERATOR")


def _eval(expr: tuple, world: Mapping[str, bool]) -> bool:
    op = expr[0]
    if op == "const":
        return expr[1]
    if op == "var":
        return world[expr[1]]
    if op == "not":
        return not _eval(expr[1], world)
    if op == "and":
        return all(_eval(x, world) for x in expr[1])
    if op == "or":
        return any(_eval(x, world) for x in expr[1])
    raise AssertionError("PARSED_EXPRESSION_HAS_UNKNOWN_OPERATOR")


def check(problem: Mapping[str, Any]) -> dict[str, Any]:
    """Check exact finite Boolean semantics; never infer terminal scope equality."""
    if not isinstance(problem, Mapping):
        return _result("FAIL_CLOSED", reason="MAPPING_REQUIRED")
    if set(problem) != {"scope_id", "variables", "scope", "routes"}:
        return _result("FAIL_CLOSED", reason="EXACT_INPUT_FIELDS_REQUIRED")
    scope_id = problem["scope_id"]
    names = problem["variables"]
    routes = problem["routes"]
    if type(scope_id) is not str or not scope_id.strip():
        return _result("FAIL_CLOSED", reason="SCOPE_ID_INVALID")
    if (type(names) is not list or not 1 <= len(names) <= MAX_VARS
            or any(type(n) is not str or _NAME.fullmatch(n) is None for n in names)
            or len(set(names)) != len(names)):
        return _result("FAIL_CLOSED", reason="VARIABLE_DOMAIN_INVALID")
    if type(routes) is not list or not 1 <= len(routes) <= MAX_ROUTES:
        return _result("FAIL_CLOSED", reason="ROUTES_INVALID")

    budget = [0]
    try:
        scope = _parse(problem["scope"], frozenset(names), budget)
        normalized = []
        seen = set()
        for row in routes:
            if not isinstance(row, Mapping) or set(row) != {"route_id", "admission", "adequacy"}:
                raise MalformedFormula("ROUTE_FIELDS_INVALID")
            rid = row["route_id"]
            if type(rid) is not str or not rid.strip() or rid in seen:
                raise MalformedFormula("ROUTE_ID_INVALID_OR_DUPLICATE")
            seen.add(rid)
            normalized.append((
                rid,
                _parse(row["admission"], frozenset(names), budget),
                _parse(row["adequacy"], frozenset(names), budget),
            ))
        encoded = json.dumps(dict(problem), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (MalformedFormula, TypeError, ValueError, OverflowError) as exc:
        return _result("FAIL_CLOSED", reason=str(exc))

    digest = hashlib.sha256(encoded).hexdigest()
    scoped = 0
    covered = 0
    first_uncovered = None
    first_unsound = None
    assignments = 1 << len(names)
    for bits in range(assignments):
        world = {name: bool(bits & (1 << i)) for i, name in enumerate(names)}
        if not _eval(scope, world):
            continue
        scoped += 1
        any_admitted = False
        for rid, admission, adequacy in normalized:
            if _eval(admission, world):
                any_admitted = True
                if not _eval(adequacy, world) and first_unsound is None:
                    first_unsound = {"world": world, "route_id": rid}
        if any_admitted:
            covered += 1
        elif first_uncovered is None:
            first_uncovered = {"world": world}
    common = {
        "input_sha256": digest,
        "boolean_variable_count": len(names),
        "all_assignments_checked": assignments,
        "in_scope_assignments_checked": scoped,
        "covered_in_scope_assignments": covered,
        "route_count": len(normalized),
        "formal_adequacy_semantics": "SUPPLIED_FORMULA_ONLY__NOT_REAL_WORLD_PROOF",
    }
    if scoped == 0:
        return _result("FAIL_CLOSED", reason="EMPTY_DECLARED_SCOPE_VACUITY", **common)
    if first_unsound is not None:
        return _result("COUNTEREXAMPLE__ADMISSION_DOES_NOT_IMPLY_DECLARED_ADEQUACY",
                       counterexample=first_unsound, **common)
    if first_uncovered is not None:
        return _result("COUNTEREXAMPLE__UNCOVERED_DECLARED_SCOPE",
                       counterexample=first_uncovered, **common)
    return _result("PASS__EXACT_FINITE_FORMULA_COVER_VERIFIED",
                   conditional_theorem="FOR_ALL_ASSIGNMENTS_IN_DECLARED_BOOLEAN_SCOPE__EVERY_ADMISSION_IMPLIES_ITS_SUPPLIED_ADEQUACY_FORMULA__AND_SOME_ADMISSION_IS_TRUE",
                   **common)

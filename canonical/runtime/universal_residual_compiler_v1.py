"""Deterministic symbolic residual compiler for the universal positive-cover route.

This module compiles the declared sound overapproximation M and declared route
admission predicates A_i into an exact Boolean residual:

    R = M AND NOT(A_1 OR ... OR A_n)

The emitted DIMACS is deterministic and content-addressable. A bounded
truth-table cross-check classifies the declared model as SAT/UNSAT and returns
one constructive witness when SAT.

Neither the compiler nor the bounded cross-check proves real target-scope
fidelity, route adequacy, Brain ownership, or global U-empty authority.
"""
from __future__ import annotations

import hashlib
import itertools
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_RESIDUAL_COMPILER_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_RESIDUAL_SPEC_V1"
MAX_VARIABLES = 15
MAX_ROUTES = 64
MAX_FORMULA_UNITS = 4096
TOP_LEVEL_FIELDS = frozenset({"schema", "scope_id", "variables", "overapprox_cnf", "routes"})
ROUTE_FIELDS = frozenset({"route_id", "admission_cnf"})
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")


def _fail(reason: str, **more: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "residual_compiled": False,
        "global_scope_complete": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **more,
    }


def _check_cnf(
    value: Any,
    variables: set[str],
    budget: list[int],
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        raise ValueError("CNF_MUST_BE_ARRAY")
    budget[0] += 1
    clauses: list[tuple[str, ...]] = []
    for clause in value:
        budget[0] += 1
        if budget[0] > MAX_FORMULA_UNITS:
            raise ValueError("CNF_BUDGET_EXCEEDED")
        if not isinstance(clause, list):
            raise ValueError("CNF_CLAUSE_MUST_BE_ARRAY")
        literals: list[str] = []
        for lit in clause:
            budget[0] += 1
            if budget[0] > MAX_FORMULA_UNITS:
                raise ValueError("CNF_BUDGET_EXCEEDED")
            if not isinstance(lit, str) or not lit:
                raise ValueError("CNF_LITERAL_INVALID")
            name = lit[1:] if lit.startswith("!") else lit
            if name not in variables:
                raise ValueError("CNF_UNKNOWN_LITERAL")
            literals.append(lit)
        clauses.append(tuple(literals))
    return tuple(clauses)


def _holds(cnf: tuple[tuple[str, ...], ...], valuation: Mapping[str, bool]) -> bool:
    return all(
        any(
            (not valuation[lit[1:]]) if lit.startswith("!") else valuation[lit]
            for lit in clause
        )
        for clause in cnf
    )


def _neg(lit: int) -> int:
    return -lit


def _literal_id(lit: str, ids: Mapping[str, int]) -> int:
    if lit.startswith("!"):
        return -ids[lit[1:]]
    return ids[lit]


def _encode_clause_truth(
    source_clause: tuple[str, ...],
    *,
    ids: Mapping[str, int],
    aux_id: int,
) -> list[list[int]]:
    """Encode aux_id <-> OR(source_clause)."""
    if not source_clause:
        return [[-aux_id]]
    src = [_literal_id(lit, ids) for lit in source_clause]
    out = [[-aux_id, *src]]
    out.extend([[aux_id, _neg(lit)] for lit in src])
    return out


def _encode_cnf_truth(
    cnf: tuple[tuple[str, ...], ...],
    *,
    ids: Mapping[str, int],
    next_var: int,
) -> tuple[list[list[int]], int, int]:
    """Return clauses, truth-variable id, and next free variable id."""
    clauses: list[list[int]] = []
    clause_vars: list[int] = []
    cursor = next_var
    for source_clause in cnf:
        cvar = cursor
        cursor += 1
        clause_vars.append(cvar)
        clauses.extend(_encode_clause_truth(source_clause, ids=ids, aux_id=cvar))

    fvar = cursor
    cursor += 1
    if not clause_vars:
        clauses.append([fvar])
    else:
        clauses.extend([[-fvar, cvar] for cvar in clause_vars])
        clauses.append([fvar, *[-cvar for cvar in clause_vars]])
    return clauses, fvar, cursor


def _compile_dimacs(
    variables: list[str],
    overapprox: tuple[tuple[str, ...], ...],
    routes: list[tuple[str, tuple[tuple[str, ...], ...]]],
) -> tuple[str, int, int]:
    ids = {name: index + 1 for index, name in enumerate(variables)}
    clauses: list[list[int]] = []

    for clause in overapprox:
        clauses.append([_literal_id(lit, ids) for lit in clause])

    next_var = len(variables) + 1
    for _, admission in routes:
        encoded, admission_var, next_var = _encode_cnf_truth(
            admission, ids=ids, next_var=next_var
        )
        clauses.extend(encoded)
        clauses.append([-admission_var])

    max_var = next_var - 1
    lines = [f"p cnf {max_var} {len(clauses)}"]
    lines.extend(" ".join(map(str, clause)) + " 0" for clause in clauses)
    dimacs = "\n".join(lines) + "\n"
    return dimacs, max_var, len(clauses)


def compile_residual(
    spec_reference: Mapping[str, Any],
    *,
    repo_root: str | Path,
    expected_scope_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(expected_scope_id, str) or not expected_scope_id:
            return _fail("EXPECTED_SCOPE_REQUIRED")
        bound = resolve_receipt_bytes(spec_reference, repo_root=repo_root)
        spec = bound["document"]
        if spec.get("schema") != SPEC_SCHEMA:
            return _fail("SPEC_SCHEMA_INVALID")
        if spec.get("scope_id") != expected_scope_id:
            return _fail("SPEC_SCOPE_MISMATCH")
        if set(spec) != TOP_LEVEL_FIELDS:
            return _fail("SPEC_FIELDS_INVALID")

        variables = spec.get("variables")
        if (
            not isinstance(variables, list)
            or not variables
            or len(variables) > MAX_VARIABLES
            or len(set(variables)) != len(variables)
            or any(not isinstance(v, str) or not _IDENTIFIER.fullmatch(v) for v in variables)
        ):
            return _fail("VARIABLES_INVALID_OR_TOO_LARGE")

        variable_set = set(variables)
        budget = [0]
        overapprox = _check_cnf(spec.get("overapprox_cnf"), variable_set, budget)
        route_rows = spec.get("routes")
        if not isinstance(route_rows, list) or not 1 <= len(route_rows) <= MAX_ROUTES:
            return _fail("ROUTES_INVALID_OR_TOO_MANY")

        routes: list[tuple[str, tuple[tuple[str, ...], ...]]] = []
        seen: set[str] = set()
        for row in route_rows:
            if not isinstance(row, dict) or set(row) != ROUTE_FIELDS:
                return _fail("ROUTE_FIELDS_INVALID")
            rid = row.get("route_id")
            if not isinstance(rid, str) or not rid or rid in seen:
                return _fail("ROUTE_ID_INVALID")
            seen.add(rid)
            routes.append((rid, _check_cnf(row.get("admission_cnf"), variable_set, budget)))

        dimacs, dimacs_variables, dimacs_clauses = _compile_dimacs(
            variables, overapprox, routes
        )
        residual_sha256 = hashlib.sha256(dimacs.encode("utf-8")).hexdigest()

        scoped_count = 0
        witness = None
        for bits in itertools.product((False, True), repeat=len(variables)):
            valuation = dict(zip(variables, bits))
            if not _holds(overapprox, valuation):
                continue
            scoped_count += 1
            if not any(_holds(admission, valuation) for _, admission in routes):
                witness = valuation
                break

        if scoped_count == 0:
            return _fail(
                "EMPTY_DECLARED_SCOPE_NOT_CREDITABLE",
                spec_git_blob_sha=bound["git_blob_sha"],
                residual_sha256=residual_sha256,
            )

        semantic_status = (
            "SAT_ON_DECLARED_BOUNDED_MODEL"
            if witness is not None
            else "UNSAT_ON_DECLARED_BOUNDED_MODEL"
        )
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__RESIDUAL_COMPILED",
            "scope_id": expected_scope_id,
            "spec_git_blob_sha": bound["git_blob_sha"],
            "spec_byte_sha256": bound["byte_sha256"],
            "residual_sha256": residual_sha256,
            "dimacs": dimacs,
            "dimacs_variable_count": dimacs_variables,
            "dimacs_clause_count": dimacs_clauses,
            "declared_variable_count": len(variables),
            "route_count": len(routes),
            "scoped_valuations_examined_until_decision": scoped_count,
            "semantic_status": semantic_status,
            "residual_model": witness,
            "residual_compiled": True,
            "bounded_semantic_crosscheck_only": True,
            "independent_unsat_certificate_replay_performed": False,
            "global_scope_complete": False,
            "u_empty_authorized": False,
            "abc_closed_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "DETERMINISTIC_DECLARED_RESIDUAL_ONLY__NO_REAL_TARGET_SCOPE__"
                "NO_ROUTE_ADEQUACY__NO_UNSAT_CERTIFICATE_REPLAY__NO_U_EMPTY"
            ),
        }
    except Exception as exc:
        return _fail(
            "SPEC_BINDING_OR_REPLAY_INVALID",
            exception_type=type(exc).__name__,
            detail=str(exc)[:200],
        )

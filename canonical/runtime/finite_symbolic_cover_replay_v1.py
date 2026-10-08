"""Exact finite Boolean policy-cover replay, without target-scope promotion.

This is a small executable proof kernel, not an LLM judge or trusted receipt
flag. It byte-authenticates a repository JSON specification, enumerates every
valuation in the *declared Boolean vocabulary*, and replays the declared
pure-Boolean route program and acceptance contract.

A positive result proves a precise proposition ABOUT THE DECLARED FORMULAS.
It does NOT show that the declaration captures all Opus-relevant situations,
that production code implements the formula, or that Brain owns the route.
There is no global U-empty, ABC, acceptance, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import itertools
import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_FINITE_SYMBOLIC_COVER_REPLAY_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_FINITE_SYMBOLIC_COVER_SPEC_V1"
MAX_VARIABLES = 15
MAX_ROUTES = 64
MAX_FORMULA_UNITS = 4096
MAX_EVALUATION_WORK_UNITS = 4_000_000
TOP_LEVEL_FIELDS = frozenset({"schema", "scope_id", "variables", "scope_cnf", "expected_output_cnf", "routes"})
ROUTE_FIELDS = frozenset({"route_id", "admission_cnf", "program_output_cnf"})
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")


def _fail(reason: str, **more: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "declared_symbolic_scope_covered": False,
        "global_scope_complete": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **more,
    }


def _check_cnf(value: Any, variables: set[str], budget: list[int]) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        raise ValueError("CNF_MUST_BE_ARRAY")
    clauses = []
    budget[0] += 1  # Count each formula, including empty TRUE.
    for clause in value:
        budget[0] += 1
        if budget[0] > MAX_FORMULA_UNITS:
            raise ValueError("CNF_BUDGET_EXCEEDED")
        if not isinstance(clause, list):
            raise ValueError("CNF_CLAUSE_MUST_BE_ARRAY")
        literals = []
        for lit in clause:
            budget[0] += 1
            if budget[0] > MAX_FORMULA_UNITS:
                raise ValueError("CNF_BUDGET_EXCEEDED")
            if not isinstance(lit, str) or not lit or (
                lit[1:] if lit.startswith("!") else lit
            ) not in variables:
                raise ValueError("CNF_UNKNOWN_OR_INVALID_LITERAL")
            literals.append(lit)
        clauses.append(tuple(literals))
    return tuple(clauses)


def _holds(cnf: tuple[tuple[str, ...], ...], values: Mapping[str, bool]) -> bool:
    return all(any(
        not values[literal[1:]] if literal.startswith("!")
        else values[literal]
        for literal in clause
    ) for clause in cnf)


def verify(
    spec_reference: Mapping[str, Any],
    *,
    repo_root: str | Path,
    expected_scope_id: str,
) -> dict[str, Any]:
    """Replay the exact pinned JSON specification; never accept a raw claim.

    [] denotes TRUE, and [[]] denotes FALSE in the CNF dialect.
    Each policy program outputs one Boolean. No Python/user code is executed.
    """
    try:
        if not isinstance(expected_scope_id, str) or not expected_scope_id:
            return _fail("EXPECTED_SCOPE_REQUIRED")
        bound = resolve_receipt_bytes(spec_reference, repo_root=repo_root)
        spec = bound["document"]
        if spec.get("schema") != SPEC_SCHEMA:
            return _fail("SPEC_SCHEMA_INVALID")
        if spec.get("scope_id") != expected_scope_id:
            return _fail("SPEC_SCOPE_MISMATCH")
        if any(k in spec for k in (
            "global_scope_complete", "terminal_authority", "u_empty_authorized",
            "opus55_equivalent", "selected_cover_complete_authorized",
        )):
            return _fail("GLOBAL_AUTHORITY_CLAIM_FORBIDDEN")
        if set(spec) != TOP_LEVEL_FIELDS:
            return _fail("SPEC_FIELDS_INVALID")
        variables = spec.get("variables")
        if (
            not isinstance(variables, list)
            or not variables
            or len(variables) > MAX_VARIABLES
            or any(not isinstance(v, str) or not _IDENTIFIER.fullmatch(v)
                   for v in variables)
            or len(set(variables)) != len(variables)
        ):
            return _fail("VARIABLES_INVALID_OR_TOO_LARGE")
        keys = set(variables)
        budget = [0]
        in_scope = _check_cnf(spec.get("scope_cnf"), keys, budget)
        expected = _check_cnf(spec.get("expected_output_cnf"), keys, budget)
        routes = spec.get("routes")
        if not isinstance(routes, list) or not 1 <= len(routes) <= MAX_ROUTES:
            return _fail("ROUTES_INVALID_OR_TOO_MANY")

        compiled = []
        ids = set()
        for row in routes:
            if not isinstance(row, dict):
                return _fail("ROUTE_NOT_OBJECT")
            if set(row) != ROUTE_FIELDS:
                return _fail("ROUTE_FIELDS_INVALID")
            rid = row.get("route_id")
            if not isinstance(rid, str) or not rid or rid in ids:
                return _fail("ROUTE_ID_INVALID")
            ids.add(rid)
            compiled.append((
                rid,
                _check_cnf(row.get("admission_cnf"), keys, budget),
                _check_cnf(row.get("program_output_cnf"), keys, budget),
            ))
        if budget[0] > MAX_FORMULA_UNITS:
            return _fail("CNF_BUDGET_EXCEEDED")
        estimated_units = (1 << len(variables)) * budget[0]
        if estimated_units > MAX_EVALUATION_WORK_UNITS:
            return _fail("EVALUATION_WORK_BUDGET_EXCEEDED",
                         estimated_work_units=estimated_units,
                         max_work_units=MAX_EVALUATION_WORK_UNITS)
        checked = 0
        for bits in itertools.product((False, True), repeat=len(variables)):
            valuation = dict(zip(variables, bits))
            if not _holds(in_scope, valuation):
                continue
            checked += 1
            wanted = _holds(expected, valuation)
            admitting = []
            for rid, admission, program in compiled:
                if not _holds(admission, valuation):
                    continue
                admitting.append(rid)
                actual = _holds(program, valuation)
                if actual != wanted:
                    return _fail(
                        "ADMITTED_ROUTE_OUTPUT_MISMATCH",
                        scope_id=expected_scope_id,
                        failing_valuation=valuation,
                        failing_route_id=rid,
                        expected_output=wanted,
                        observed_program_output=actual,
                        checked_scoped_valuations=checked,
                        spec_git_blob_sha=bound["git_blob_sha"],
                    )
            if not admitting:
                return _fail(
                    "UNCOVERED_SCOPED_VALUATION",
                    scope_id=expected_scope_id,
                    failing_valuation=valuation,
                    checked_scoped_valuations=checked,
                    spec_git_blob_sha=bound["git_blob_sha"],
                )
        if checked == 0:
            return _fail("EMPTY_DECLARED_SCOPE_NOT_CREDITABLE")
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXHAUSTIVE_DECLARED_BOOLEAN_SCOPE_COVER",
            "scope_id": expected_scope_id,
            "spec_git_blob_sha": bound["git_blob_sha"],
            "spec_byte_sha256": bound["byte_sha256"],
            "variable_count": len(variables),
            "scoped_valuations_checked": checked,
            "total_valuations": 1 << len(variables),
            "route_count": len(compiled),
            "bounded_evaluation_work_units": estimated_units,
            "declared_symbolic_scope_covered": True,
            "declared_program_and_acceptance_formula_replayed": True,
            "production_route_implementation_verified": False,
            "real_target_scope_completeness_verified": False,
            "global_scope_complete": False,
            "u_empty_authorized": False,
            "abc_closed_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "EXACT_THEOREM_ONLY_ABOUT_PINNED_FINITE_BOOLEAN_MODEL;"
                "NO_PROOF_OF_MODEL_FIDELITY_PRODUCTION_IMPLEMENTATION_OR_OPUS55_SCOPE"
            ),
        }
    except Exception as exc:
        return _fail("SPEC_BINDING_OR_REPLAY_INVALID", exception_type=type(exc).__name__,
                     detail=str(exc)[:200])

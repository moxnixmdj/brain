"""Canonical numeric semantics for Unknown-Domain direct V3.

V3 removes an evaluator-only IEEE-754 role-order artifact from ADD2.  ADD2 is a
commutative primitive, so its numeric consequence is defined by a deterministic
permutation-invariant summation of the same three visible numbers.  All other
primitive semantics are unchanged from V2.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_SEMANTICS_V1"


class V3SemanticsError(ValueError):
    pass


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise V3SemanticsError(field + "_BOOLEAN_INVALID")
    try:
        out = float(value)
    except Exception as exc:
        raise V3SemanticsError(field + "_FLOAT_INVALID") from exc
    if not math.isfinite(out):
        raise V3SemanticsError(field + "_NONFINITE")
    return out


def eval_program(program: Mapping[str, Any], role_values: Mapping[str, float]) -> float:
    if not isinstance(program, Mapping):
        raise V3SemanticsError("PROGRAM_INVALID")
    if program.get("dsl") != "UDIR_V1":
        raise V3SemanticsError("PROGRAM_DSL_INVALID")
    op = str(program.get("op") or "")
    params = program.get("params")
    if not isinstance(params, Mapping):
        raise V3SemanticsError("PROGRAM_PARAMS_INVALID")

    x = _finite(role_values.get("r0", 0.0), "r0")
    if op == "AFFINE_POS":
        return _finite(params["bias"], "bias") + _finite(params["gain"], "gain") * x
    if op == "SIGN":
        return -1.0 if x < 0 else 1.0
    if op == "COMPLEMENT":
        return _finite(params["total"], "total") - x
    if op == "SAT_MONO":
        return _finite(params["bias"], "bias") + _finite(params["gain"], "gain") * (x / (1.0 + abs(x)))
    if op == "ADD2":
        # The mathematical primitive is commutative.  Sort the three finite
        # operands before fsum so hidden r0/r1 orientation cannot alter a bit.
        operands = sorted((
            _finite(params["bias"], "bias"),
            _finite(role_values["r0"], "r0"),
            _finite(role_values["r1"], "r1"),
        ))
        return math.fsum(operands)
    if op == "STEP":
        return _finite(params["high"], "high") if x >= _finite(params["threshold"], "threshold") else _finite(params["low"], "low")
    raise V3SemanticsError("PROGRAM_OP_UNKNOWN")

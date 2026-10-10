"""Direct constructor for the conjunctive direct-field typed acceptance fragment.

This is the constructive dual of typed_acceptance_finite_search_v1: instead of
enumerating a Cartesian product, it solves independent field constraints and then
re-verifies the constructed candidate with the authoritative typed verifier.

Supported acceptance form:
- one atom or AND of atoms;
- atom op in {ge, le, eq};
- left side is a candidate-field ref;
- right side is a typed constant of matching type/dimension.

It is complete for this declared fragment. Anything else fails closed.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime.typed_acceptance_program_v1 import verify

SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_CONSTRUCTIVE_SOLVER_V1"


class ConstructiveSolveError(ValueError):
    pass


def _atoms(expr: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if not isinstance(expr, Mapping):
        raise ConstructiveSolveError("EXPR_INVALID")
    if expr.get("op") == "and":
        args = expr.get("args")
        if not isinstance(args, list) or not args:
            raise ConstructiveSolveError("AND_ARGS_INVALID")
        out: list[Mapping[str, Any]] = []
        for row in args:
            out.extend(_atoms(row))
        return out
    return [expr]


def solve(program: Mapping[str, Any], *, trusted_values: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(program, Mapping):
            raise ConstructiveSolveError("PROGRAM_NOT_OBJECT")
        fields = program.get("fields")
        if not isinstance(fields, list) or not fields:
            raise ConstructiveSolveError("FIELDS_INVALID")

        meta: dict[str, dict[str, str]] = {}
        for i, row in enumerate(fields):
            if not isinstance(row, Mapping):
                raise ConstructiveSolveError(f"FIELD_INVALID:{i}")
            fid = row.get("id")
            typ = row.get("type")
            dim = row.get("dimension")
            src = row.get("source")
            if not isinstance(fid, str) or not fid or fid in meta:
                raise ConstructiveSolveError(f"FIELD_ID_INVALID:{i}")
            if typ not in {"integer", "number", "boolean", "enum"}:
                raise ConstructiveSolveError(f"FIELD_TYPE_INVALID:{fid}")
            if not isinstance(dim, str) or not dim:
                raise ConstructiveSolveError(f"FIELD_DIMENSION_INVALID:{fid}")
            if src not in {"trusted", "candidate"}:
                raise ConstructiveSolveError(f"FIELD_SOURCE_INVALID:{fid}")
            meta[fid] = {"type": typ, "dimension": dim, "source": src}

        candidate_ids = {k for k,v in meta.items() if v["source"] == "candidate"}
        trusted_ids = {k for k,v in meta.items() if v["source"] == "trusted"}
        if set(trusted_values) != trusted_ids:
            raise ConstructiveSolveError("TRUSTED_FIELD_SET_MISMATCH")

        state: dict[str, dict[str, Any]] = {
            fid: {"eq": None, "lo": None, "hi": None}
            for fid in candidate_ids
        }

        for atom in _atoms(program.get("accept_when")):
            op = atom.get("op")
            if op not in {"ge", "le", "eq"}:
                raise ConstructiveSolveError("UNSUPPORTED_ATOM:" + str(op))
            left = atom.get("left")
            right = atom.get("right")
            if not isinstance(left, Mapping) or left.get("op") != "ref":
                raise ConstructiveSolveError("LEFT_MUST_BE_DIRECT_REF")
            fid = left.get("id")
            if fid not in candidate_ids:
                raise ConstructiveSolveError("LEFT_REF_NOT_CANDIDATE:" + str(fid))
            if not isinstance(right, Mapping) or right.get("op") != "const":
                raise ConstructiveSolveError("RIGHT_MUST_BE_CONST")
            typ = meta[fid]["type"]
            dim = meta[fid]["dimension"]
            if right.get("type") != typ and not (typ == "integer" and right.get("type") == "number"):
                raise ConstructiveSolveError("CONST_TYPE_MISMATCH:" + fid)
            if right.get("dimension") != dim:
                raise ConstructiveSolveError("CONST_DIMENSION_MISMATCH:" + fid)
            value = right.get("value")
            s = state[fid]
            if op == "eq":
                if s["eq"] is not None and s["eq"] != value:
                    return _unsat(fid, "CONFLICTING_EQUALITIES")
                s["eq"] = value
            elif typ not in {"integer", "number"}:
                raise ConstructiveSolveError("ORDER_ON_NONNUMERIC:" + fid)
            elif op == "ge":
                v = float(value)
                s["lo"] = v if s["lo"] is None else max(float(s["lo"]), v)
            elif op == "le":
                v = float(value)
                s["hi"] = v if s["hi"] is None else min(float(s["hi"]), v)

        candidate: dict[str, Any] = {}
        for fid in sorted(candidate_ids):
            typ = meta[fid]["type"]
            s = state[fid]
            eq = s["eq"]
            lo = s["lo"]
            hi = s["hi"]

            if eq is not None:
                value = eq
                if typ == "integer":
                    if isinstance(value, bool) or float(value) != int(float(value)):
                        return _unsat(fid, "INTEGER_EQUALITY_NONINTEGER")
                    value = int(float(value))
                if typ in {"integer", "number"}:
                    fv = float(value)
                    if lo is not None and fv < lo:
                        return _unsat(fid, "EQUALITY_BELOW_LOWER_BOUND")
                    if hi is not None and fv > hi:
                        return _unsat(fid, "EQUALITY_ABOVE_UPPER_BOUND")
                candidate[fid] = value
                continue

            if typ in {"integer", "number"}:
                low = -math.inf if lo is None else float(lo)
                high = math.inf if hi is None else float(hi)
                if low > high:
                    return _unsat(fid, "EMPTY_INTERVAL")
                if typ == "integer":
                    ilo = math.ceil(low) if math.isfinite(low) else 0
                    ihi = math.floor(high) if math.isfinite(high) else 0
                    if ilo > ihi:
                        return _unsat(fid, "EMPTY_INTEGER_INTERVAL")
                    value = ilo if math.isfinite(low) else (ihi if math.isfinite(high) else 0)
                    candidate[fid] = int(value)
                else:
                    if math.isfinite(low):
                        value = low
                    elif math.isfinite(high):
                        value = high
                    else:
                        value = 0.0
                    candidate[fid] = float(value)
            elif typ == "boolean":
                candidate[fid] = False
            else:
                return {
                    "schema": SCHEMA,
                    "status": "UNRESOLVED__UNCONSTRAINED_ENUM",
                    "pass": False,
                    "field_id": fid,
                    "complete_for_declared_fragment": False,
                    "proposal_authority": False,
                    "terminal_authority": False,
                }

        verdict = verify(program, trusted_values=trusted_values, candidate_values=candidate)
        if verdict.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__CONSTRUCTED_CANDIDATE_DID_NOT_REVERIFY",
                "pass": False,
                "candidate": candidate,
                "verdict": verdict,
                "complete_for_declared_fragment": False,
                "proposal_authority": False,
                "terminal_authority": False,
            }
        return {
            "schema": SCHEMA,
            "status": "PASS__DIRECT_CONSTRUCTIVE_ACCEPTANCE_SOLUTION",
            "pass": True,
            "candidate": candidate,
            "complete_for_declared_fragment": True,
            "cartesian_enumeration_used": False,
            "live_reverification_passed": True,
            "proposal_authority": False,
            "terminal_authority": False,
            "scope_boundary": "CONJUNCTION_OF_DIRECT_CANDIDATE_FIELD_GE_LE_EQ_CONSTANT_ATOMS_ONLY",
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "complete_for_declared_fragment": False,
            "proposal_authority": False,
            "terminal_authority": False,
        }


def _unsat(field_id: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "PROVED_UNSAT_IN_DECLARED_FRAGMENT",
        "pass": False,
        "field_id": field_id,
        "reason": reason,
        "complete_for_declared_fragment": True,
        "proposal_authority": False,
        "terminal_authority": False,
    }

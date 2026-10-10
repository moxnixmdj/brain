"""Typed declarative acceptance programs for structured task verification.

Programs are bounded JSON-like ASTs interpreted by the existing structured-method
expression evaluator. They are not Python, shell, or dynamically imported code.

Security / authority model:
- trusted fields and candidate fields are declared separately;
- proposals may populate only candidate fields;
- trusted fields come only from the verifier payload;
- extra/missing fields fail closed;
- types and dimensions are checked before evaluation;
- acceptance requires one boolean dimensionless expression evaluating exactly True.

This solves verifier *execution* for a broad structured class. Whether the
acceptance program itself is semantically adequate for the task remains an
upstream task-contract/source-grounding obligation.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.structured_method_expression_ast_candidate_v2 import (
    _schema as _typed_schema,
    _eval as _typed_eval,
)

SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_V1"
PROGRAM_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1"
SOURCES = {"trusted", "candidate"}


class AcceptanceProgramError(ValueError):
    pass


def _declarations(program: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    if program.get("schema") != PROGRAM_SCHEMA:
        raise AcceptanceProgramError("PROGRAM_SCHEMA_INVALID")
    rows = program.get("fields")
    if not isinstance(rows, list) or not rows:
        raise AcceptanceProgramError("PROGRAM_FIELDS_REQUIRED")
    out: dict[str, dict[str, str]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise AcceptanceProgramError(f"FIELD_DECLARATION_INVALID:{i}")
        fid = str(row.get("id") or "")
        typ = str(row.get("type") or "")
        dim = str(row.get("dimension") or "")
        source = str(row.get("source") or "")
        if not fid or fid in out:
            raise AcceptanceProgramError("FIELD_ID_INVALID_OR_DUPLICATE:" + fid)
        if typ not in {"integer", "number", "boolean", "enum"}:
            raise AcceptanceProgramError("FIELD_TYPE_INVALID:" + fid)
        if not dim:
            raise AcceptanceProgramError("FIELD_DIMENSION_MISSING:" + fid)
        if source not in SOURCES:
            raise AcceptanceProgramError("FIELD_SOURCE_INVALID:" + fid)
        out[fid] = {"type": typ, "dimension": dim, "source": source}
    expr = program.get("accept_when")
    if not isinstance(expr, Mapping):
        raise AcceptanceProgramError("ACCEPT_WHEN_REQUIRED")
    return out


def verify(
    program: Mapping[str, Any],
    *,
    trusted_values: Mapping[str, Any],
    candidate_values: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(program, Mapping):
            raise AcceptanceProgramError("PROGRAM_NOT_OBJECT")
        if not isinstance(trusted_values, Mapping):
            raise AcceptanceProgramError("TRUSTED_VALUES_NOT_OBJECT")
        if not isinstance(candidate_values, Mapping):
            raise AcceptanceProgramError("CANDIDATE_VALUES_NOT_OBJECT")
        decl = _declarations(program)

        trusted_ids = {k for k, v in decl.items() if v["source"] == "trusted"}
        candidate_ids = {k for k, v in decl.items() if v["source"] == "candidate"}
        if set(trusted_values) != trusted_ids:
            missing = sorted(trusted_ids - set(trusted_values))
            extra = sorted(set(trusted_values) - trusted_ids)
            raise AcceptanceProgramError(
                "TRUSTED_FIELD_SET_MISMATCH:missing=" + ",".join(missing) + ";extra=" + ",".join(extra)
            )
        if set(candidate_values) != candidate_ids:
            missing = sorted(candidate_ids - set(candidate_values))
            extra = sorted(set(candidate_values) - candidate_ids)
            raise AcceptanceProgramError(
                "CANDIDATE_FIELD_SET_MISMATCH:missing=" + ",".join(missing) + ";extra=" + ",".join(extra)
            )

        schema_rows = []
        for fid in sorted(decl):
            meta = decl[fid]
            value = trusted_values[fid] if meta["source"] == "trusted" else candidate_values[fid]
            schema_rows.append({
                "id": fid,
                "type": meta["type"],
                "dimension": meta["dimension"],
                "value": value,
            })
        meta, vals = _typed_schema(schema_rows)
        typ, dim, value = _typed_eval(program["accept_when"], meta, vals)
        if typ != "boolean" or dim != "dimensionless":
            raise AcceptanceProgramError("ACCEPTANCE_EXPRESSION_NOT_BOOLEAN_DIMENSIONLESS")

        passed = value is True
        return {
            "schema": SCHEMA,
            "status": "PASS__DECLARATIVE_ACCEPTANCE_PROGRAM" if passed else "FALSIFIED__DECLARATIVE_ACCEPTANCE_PROGRAM",
            "pass": passed,
            "trusted_field_ids": sorted(trusted_ids),
            "candidate_field_ids": sorted(candidate_ids),
            "accepted": passed,
            "terminal_authority": False,
            "soundness_boundary": (
                "EXECUTES_ONLY_THE_DECLARED_TYPED_ACCEPTANCE_PROGRAM;"
                "SEMANTIC_ADEQUACY_OF_THAT_PROGRAM_FOR_THE_REAL_TASK_MUST_BE_PROVED_UPSTREAM"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }

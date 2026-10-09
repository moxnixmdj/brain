"""Constructive independent-acceptance policy for one exact coding-specification cell.

Selected cell (membership is NEVER self-certified here):
- the authoritative source semantics for this residual are already proved to consist
  only of source_aligned_acceptance_program_v1 controlled requirements;
- exact candidate field schema is independently bound;
- field types are number or boolean;
- every candidate field occurs in exactly one normative requirement.

For that cell this policy:
1. compiles every controlled source requirement into the Brain typed acceptance AST;
2. constructs a candidate satisfying the complete conjunction;
3. re-verifies that candidate with the independent typed verifier;
4. mutates exactly one field per requirement and re-verifies that every mutation
   is rejected.

This is an adequacy policy for SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001
inside the declared cell only. It does not implement the requested software change,
prove CursorBench score, or infer membership in the cell.
"""
from __future__ import annotations

from copy import deepcopy
from math import inf, isfinite, nextafter
from typing import Any, Mapping

from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.typed_acceptance_constructive_solver_v1 import solve
from canonical.runtime.typed_acceptance_program_v1 import verify

SCHEMA = "PROJECT_BRAIN_CODING_CONTROLLED_TYPED_ACCEPTANCE_POLICY_V1"
POLICY_ID = "CODING_CONTROLLED_TYPED_ACCEPTANCE_MODEL_POLICY_V1"
CONDITION_ATOM_ID = "CODING_CONTROLLED_TYPED_ACCEPTANCE_SINGLE_CONSTRAINT_CELL_V1"
BEHAVIOR_ID = "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"


def _fail(status: str, reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "behavior_id": BEHAVIOR_ID,
        "pass": False,
        "status": status,
        "reason": reason,
        "selected_cell_membership_self_certified": False,
        "policy_selection_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _schema(field_schema: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, str]]:
    if not isinstance(field_schema, Mapping) or not field_schema:
        raise ValueError("FIELD_SCHEMA_INVALID")
    out: dict[str, dict[str, str]] = {}
    for field, raw in field_schema.items():
        if not isinstance(field, str) or not field or not isinstance(raw, Mapping):
            raise ValueError("FIELD_SCHEMA_ROW_INVALID")
        typ = raw.get("type")
        dim = raw.get("dimension")
        if typ not in {"number", "boolean"}:
            raise ValueError("CELL_FIELD_TYPE_OUTSIDE_SELECTED_FRAGMENT:" + field)
        if not isinstance(dim, str) or not dim:
            raise ValueError("FIELD_DIMENSION_INVALID:" + field)
        if typ == "boolean" and dim != "dimensionless":
            raise ValueError("BOOLEAN_DIMENSION_INVALID:" + field)
        out[field] = {"type": str(typ), "dimension": dim}
    return out


def _falsifying_value(row: Mapping[str, Any], typ: str) -> Any:
    mode = row.get("mode")
    literal = row.get("literal")
    if typ == "boolean":
        if mode != "EQ_BOOL" or literal not in {"true", "false"}:
            raise ValueError("BOOLEAN_REQUIREMENT_OUTSIDE_SELECTED_FRAGMENT")
        return literal != "true"

    if mode not in {"GE", "LE", "EQ_NUM"}:
        raise ValueError("NUMBER_REQUIREMENT_OUTSIDE_SELECTED_FRAGMENT")
    value = float(str(literal))
    if not isfinite(value):
        raise ValueError("NONFINITE_NUMERIC_LITERAL")
    if mode == "GE":
        candidate = nextafter(value, -inf)
    else:
        candidate = nextafter(value, inf)
    if not isfinite(candidate) or candidate == value:
        raise ValueError("NUMERIC_FALSIFIER_UNAVAILABLE")
    return candidate


def build(
    source_text: str,
    *,
    source_id: str,
    field_schema: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    try:
        schema = _schema(field_schema)
        compiled = compile_program(
            source_text,
            source_id=source_id,
            field_schema=schema,
        )
        if compiled.get("status") != "COMPILED":
            return _fail(
                "UNRESOLVED__OUTSIDE_CONTROLLED_TYPED_ACCEPTANCE_CELL",
                "SOURCE_ACCEPTANCE_PROGRAM_NOT_COMPILED",
                compiler=compiled,
            )

        requirements = compiled.get("compiled_requirements")
        if not isinstance(requirements, list) or not requirements:
            return _fail("FAIL_CLOSED", "COMPILED_REQUIREMENTS_MISSING")

        counts = {field: 0 for field in schema}
        by_field: dict[str, Mapping[str, Any]] = {}
        for row in requirements:
            if not isinstance(row, Mapping):
                return _fail("FAIL_CLOSED", "COMPILED_REQUIREMENT_NOT_OBJECT")
            field = row.get("field")
            if field not in schema:
                return _fail("FAIL_CLOSED", "COMPILED_REQUIREMENT_UNKNOWN_FIELD")
            counts[str(field)] += 1
            by_field[str(field)] = row

        if any(count != 1 for count in counts.values()):
            return _fail(
                "UNRESOLVED__OUTSIDE_SINGLE_CONSTRAINT_PER_FIELD_CELL",
                "EVERY_FIELD_MUST_HAVE_EXACTLY_ONE_CONTROLLED_REQUIREMENT",
                field_requirement_counts=counts,
            )
        if len(requirements) != len(schema):
            return _fail("FAIL_CLOSED", "REQUIREMENT_FIELD_CARDINALITY_MISMATCH")

        program = compiled.get("acceptance_program")
        if not isinstance(program, Mapping):
            return _fail("FAIL_CLOSED", "ACCEPTANCE_PROGRAM_MISSING")

        constructive = solve(program, trusted_values={})
        if constructive.get("pass") is not True:
            return _fail(
                "FAIL_CLOSED",
                "SELECTED_CELL_CONSTRUCTIVE_BASELINE_NOT_PROVED",
                constructive=constructive,
            )
        baseline = constructive.get("candidate")
        if not isinstance(baseline, Mapping) or set(baseline) != set(schema):
            return _fail("FAIL_CLOSED", "CONSTRUCTIVE_BASELINE_FIELD_SET_INVALID")

        baseline_verdict = verify(
            program,
            trusted_values={},
            candidate_values=baseline,
        )
        if baseline_verdict.get("pass") is not True:
            return _fail("FAIL_CLOSED", "BASELINE_REVERIFICATION_FAILED")

        witnesses: list[dict[str, Any]] = []
        for field in sorted(schema):
            row = by_field[field]
            mutated = deepcopy(dict(baseline))
            mutated[field] = _falsifying_value(row, schema[field]["type"])
            verdict = verify(
                program,
                trusted_values={},
                candidate_values=mutated,
            )
            if verdict.get("pass") is True or verdict.get("status") != "FALSIFIED__DECLARATIVE_ACCEPTANCE_PROGRAM":
                return _fail(
                    "FAIL_CLOSED",
                    "REQUIREMENT_FALSIFIER_DID_NOT_REJECT:" + field,
                    verifier=verdict,
                )
            changed = sorted(
                key for key in baseline
                if baseline[key] != mutated[key]
            )
            if changed != [field]:
                return _fail("FAIL_CLOSED", "FALSIFIER_NOT_SINGLE_FIELD:" + field)
            witnesses.append({
                "field": field,
                "segment_index": row.get("segment_index"),
                "segment_sha256": row.get("segment_sha256"),
                "mode": row.get("mode"),
                "accepted_baseline_value": baseline[field],
                "falsifying_value": mutated[field],
                "only_changed_field": field,
                "independent_verifier_status": verdict.get("status"),
            })

        return {
            "schema": SCHEMA,
            "policy_id": POLICY_ID,
            "behavior_id": BEHAVIOR_ID,
            "pass": True,
            "status": "PASS__EXACT_CONTROLLED_TYPED_ACCEPTANCE_MODEL_WITH_REQUIREMENT_FALSIFIERS",
            "policy_condition": {"op": "ATOM", "id": CONDITION_ATOM_ID},
            "source_id": source_id,
            "source_sha256": compiled.get("source_sha256"),
            "acceptance_program": deepcopy(dict(program)),
            "accepted_baseline": deepcopy(dict(baseline)),
            "requirement_falsifiers": witnesses,
            "requirement_count": len(requirements),
            "every_declared_field_has_exactly_one_requirement": True,
            "baseline_live_reverification_passed": True,
            "every_requirement_has_live_rejected_single_field_falsifier": True,
            "selected_cell_membership_self_certified": False,
            "policy_selection_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "scope_boundary": (
                "CONDITIONAL_ON_SEPARATELY_PROVED_MEMBERSHIP_IN_"
                "CODING_CONTROLLED_TYPED_ACCEPTANCE_SINGLE_CONSTRAINT_CELL_V1;"
                "NUMBER_AND_BOOLEAN_FIELDS_ONLY;"
                "ONE_CONTROLLED_NORMATIVE_REQUIREMENT_PER_FIELD"
            ),
        }
    except Exception as exc:
        return _fail(
            "FAIL_CLOSED",
            type(exc).__name__ + ":" + str(exc),
        )

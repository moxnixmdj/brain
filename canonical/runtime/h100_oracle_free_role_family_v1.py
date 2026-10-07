"""Oracle-free role + family discovery for bounded two-column numeric tasks.

The solver receives only rows with two opaque numeric columns. It is not told
which column is input, which is target, or which parametric family is correct.
It enumerates both directed role assignments, invokes the existing verified
zero-learned parametric family search, and accepts a role assignment only when
the family fit is exact under the frozen threshold.

If more than one directed assignment is exact, the observations do not identify
a unique role orientation under this hypothesis class. The solver abstains
instead of inventing semantics.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_zero_learned_parametric_unary_v1 as param

SCHEMA = "PROJECT_BRAIN_H100_ORACLE_FREE_ROLE_FAMILY_V1"


class OracleFreeRoleFamilyError(ValueError):
    pass


def _finite(v: Any) -> float:
    if isinstance(v, bool):
        raise OracleFreeRoleFamilyError("NON_NUMERIC_VALUE")
    try:
        out = float(v)
    except (TypeError, ValueError) as exc:
        raise OracleFreeRoleFamilyError("NON_NUMERIC_VALUE") from exc
    if not math.isfinite(out):
        raise OracleFreeRoleFamilyError("NONFINITE_VALUE")
    return out


def _normalize(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[dict[str, float]]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) < 8:
        raise OracleFreeRoleFamilyError("AT_LEAST_EIGHT_ROWS_REQUIRED")
    first = rows[0]
    if not isinstance(first, Mapping):
        raise OracleFreeRoleFamilyError("ROW_NOT_MAPPING")
    names = sorted(str(k) for k in first.keys())
    if len(names) != 2 or len(set(names)) != 2:
        raise OracleFreeRoleFamilyError("EXACTLY_TWO_COLUMNS_REQUIRED")
    out: list[dict[str, float]] = []
    expected = set(names)
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(str(k) for k in row.keys()) != expected:
            raise OracleFreeRoleFamilyError(f"ROW_SCHEMA_MISMATCH:{i}")
        out.append({name: _finite(row[name]) for name in names})
    return names, out


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    exact_nrmse: float = 1e-8,
) -> dict[str, Any]:
    names, data = _normalize(rows)
    directed = []
    for target in names:
        input_name = names[1] if target == names[0] else names[0]
        result = param.discover(
            data,
            target=target,
            input_name=input_name,
            exact_nrmse=exact_nrmse,
        )
        best = result.get("best_candidate")
        exact = (
            result.get("status") == "EXACT_CANDIDATE_FOUND"
            and isinstance(best, Mapping)
            and float(best.get("nrmse", math.inf)) <= float(exact_nrmse)
        )
        directed.append({
            "target_column": target,
            "input_column": input_name,
            "exact": bool(exact),
            "family": None if not isinstance(best, Mapping) else best.get("family"),
            "nrmse": None if not isinstance(best, Mapping) else best.get("nrmse"),
            "candidate": dict(best) if exact and isinstance(best, Mapping) else None,
        })

    exact_rows = [row for row in directed if row["exact"]]
    if len(exact_rows) == 1:
        status = "UNIQUE_ROLE_AND_FAMILY_IDENTIFIED"
        selected = exact_rows[0]
    elif len(exact_rows) == 0:
        status = "NO_EXACT_ROLE_FAMILY_IDENTIFIED"
        selected = None
    else:
        status = "ABSTAIN__ROLE_ORIENTATION_NONIDENTIFIABLE"
        selected = None

    return {
        "schema": SCHEMA,
        "status": status,
        "column_names": names,
        "directed_hypothesis_count": 2,
        "exact_directed_hypothesis_count": len(exact_rows),
        "selected": selected,
        "directed_results": directed,
        "semantic_side_information": {
            "target_column_supplied": False,
            "input_column_supplied": False,
            "family_supplied": False,
            "ontology_label_supplied": False,
        },
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "hard_nonclaims": [
            "TWO_COLUMN_NUMERIC_SCOPE_ONLY",
            "PARAMETRIC_FAMILY_VOCABULARY_IS_PREEXISTING_EXECUTABLE_STRUCTURE",
            "UNIQUE_EXACT_FIT_IS_NOT_OPEN_WORLD_SEMANTIC_UNDERSTANDING",
            "AMBIGUOUS_ORIENTATIONS_ABSTAIN_INSTEAD_OF_GUESSING",
            "NO_OPUS55_ACCEPTANCE_OR_TERMINAL_CREDIT",
        ],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }

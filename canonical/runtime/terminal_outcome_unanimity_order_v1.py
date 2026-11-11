from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class OutcomeOrderError(ValueError):
    pass


@dataclass(frozen=True)
class OutcomeVector:
    evaluator_ids: tuple[str, ...]
    values: tuple[float, ...]

    @classmethod
    def from_mapping(
        cls,
        evaluator_ids: Sequence[str],
        raw: Mapping[str, float | int | bool],
    ) -> "OutcomeVector":
        ids = tuple(str(x) for x in evaluator_ids)
        if not ids or len(set(ids)) != len(ids):
            raise OutcomeOrderError("EVALUATOR_IDS_INVALID")
        if set(raw) != set(ids):
            raise OutcomeOrderError("OUTCOME_COMPONENT_SET_MISMATCH")
        vals = []
        for key in ids:
            value = raw[key]
            if isinstance(value, bool):
                vals.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                vals.append(float(value))
            else:
                raise OutcomeOrderError("OUTCOME_VALUE_INVALID:" + key)
        return cls(ids, tuple(vals))


def geq(a: OutcomeVector, b: OutcomeVector) -> bool:
    if a.evaluator_ids != b.evaluator_ids:
        raise OutcomeOrderError("EVALUATOR_IDENTITY_MISMATCH")
    return all(x >= y for x, y in zip(a.values, b.values))


def equivalent(a: OutcomeVector, b: OutcomeVector) -> bool:
    return a.evaluator_ids == b.evaluator_ids and a.values == b.values


def compare(a: OutcomeVector, b: OutcomeVector) -> str:
    ab = geq(a, b)
    ba = geq(b, a)
    if ab and ba:
        return "EQUIVALENT"
    if ab:
        return "A_DOMINATES"
    if ba:
        return "B_DOMINATES"
    return "INCOMPARABLE"


def verify_partial_order(samples: Sequence[OutcomeVector]) -> dict[str, object]:
    rows = tuple(samples)
    if not rows:
        raise OutcomeOrderError("SAMPLES_EMPTY")
    ids = rows[0].evaluator_ids
    if any(x.evaluator_ids != ids for x in rows):
        raise OutcomeOrderError("EVALUATOR_IDENTITY_MISMATCH")
    reflexive = all(geq(x, x) for x in rows)
    transitive = all(
        not (geq(a, b) and geq(b, c)) or geq(a, c)
        for a in rows for b in rows for c in rows
    )
    antisymmetric = all(
        not (geq(a, b) and geq(b, a)) or equivalent(a, b)
        for a in rows for b in rows
    )
    return {
        "status": "PASS__TASK_LOCAL_UNANIMITY_ORDER"
        if reflexive and transitive and antisymmetric
        else "FAIL_CLOSED",
        "reflexive": reflexive,
        "transitive": transitive,
        "antisymmetric_on_quotient": antisymmetric,
        "global_scalar_weight_required": False,
        "terminal_credit": False,
    }

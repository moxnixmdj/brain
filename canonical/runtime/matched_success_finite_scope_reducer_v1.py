from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Any, Iterable, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_FINITE_SCOPE_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_FINITE_SCOPE_OUTPUT_V1"


class ReducerError(ValueError):
    pass


@dataclass(frozen=True)
class Rational:
    numerator: int
    denominator: int

    @classmethod
    def from_count(cls, successes: int, total: int) -> "Rational":
        if not isinstance(successes, int) or not isinstance(total, int):
            raise ReducerError("COUNT_TYPE_INVALID")
        if total <= 0:
            raise ReducerError("TOTAL_MUST_BE_POSITIVE")
        if successes < 0 or successes > total:
            raise ReducerError("SUCCESS_COUNT_OUT_OF_RANGE")
        g = gcd(successes, total)
        if successes == 0:
            return cls(0, 1)
        return cls(successes // g, total // g)

    def as_dict(self) -> dict[str, int | str]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "exact": f"{self.numerator}/{self.denominator}",
        }


def _ids(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ReducerError(name + "_INVALID")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ReducerError(name + "_ITEM_INVALID")
    out = tuple(x.strip() for x in value)
    if len(set(out)) != len(out):
        raise ReducerError(name + "_DUPLICATE")
    return out


def _success_ids(value: Any, universe: set[str], name: str) -> set[str]:
    if not isinstance(value, list):
        raise ReducerError(name + "_INVALID")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ReducerError(name + "_ITEM_INVALID")
    out = {x.strip() for x in value}
    if len(out) != len(value):
        raise ReducerError(name + "_DUPLICATE")
    extra = sorted(out - universe)
    if extra:
        raise ReducerError(name + "_OUTSIDE_UNIVERSE:" + ",".join(extra))
    return out


def exact_rate(success_ids: Iterable[str], case_ids: Iterable[str]) -> Rational:
    cases = tuple(case_ids)
    successes = set(success_ids)
    return Rational.from_count(len(successes), len(cases))


def compile_reducer(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise ReducerError("SCHEMA_INVALID")

        predicate_id = doc.get("predicate_id")
        if predicate_id not in {
            "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
            "IF_SCOPE_BOUNDARY_NONINFERIOR",
            "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        }:
            raise ReducerError("PREDICATE_ID_INVALID")

        scope = doc.get("scope")
        if not isinstance(scope, Mapping):
            raise ReducerError("SCOPE_INVALID")
        for key in (
            "finite",
            "complete",
            "frozen",
            "content_addressed",
            "same_case_universe_for_brain_and_opus",
            "binary_success_criterion",
            "no_population_extrapolation",
            "fixed_case_count_before_first_result",
            "no_sequential_early_stop",
        ):
            if scope.get(key) is not True:
                raise ReducerError("SCOPE_" + key.upper() + "_NOT_TRUE")

        case_ids = _ids(scope.get("case_ids"), "CASE_IDS")
        universe = set(case_ids)

        brain_success = _success_ids(
            doc.get("brain_success_case_ids"), universe, "BRAIN_SUCCESS_CASE_IDS"
        )
        opus_success = _success_ids(
            doc.get("opus_success_case_ids"), universe, "OPUS_SUCCESS_CASE_IDS"
        )

        brain_rate = exact_rate(brain_success, case_ids)
        opus_rate = exact_rate(opus_success, case_ids)

        brain_ge_opus = len(brain_success) >= len(opus_success)
        success_set_inclusion = opus_success.issubset(brain_success)
        if success_set_inclusion and not brain_ge_opus:
            raise ReducerError("INTERNAL_MONOTONICITY_CONTRADICTION")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__EXACT_FINITE_SCOPE_REDUCER",
            "predicate_id": predicate_id,
            "case_count": len(case_ids),
            "brain_success_count": len(brain_success),
            "opus_success_count": len(opus_success),
            "brain_bound": brain_rate.as_dict(),
            "opus_bound": opus_rate.as_dict(),
            "brain_noninferior": brain_ge_opus,
            "opus_success_set_subset_of_brain": success_set_inclusion,
            "monotonicity_transport_proved_for_this_input": (
                success_set_inclusion and brain_ge_opus
            ),
            "reducer_identity": "EXACT_COMPLETE_FINITE_SCOPE_SUCCESS_FRACTION",
            "same_reducer_for_brain_and_opus": True,
            "population_generalization_claimed": False,
            "brain_exact_finite_scope_interval": {"lower": brain_rate.as_dict(), "upper": brain_rate.as_dict(), "coverage_on_claimed_finite_universe": "1"},
            "opus_exact_finite_scope_interval": {"lower": opus_rate.as_dict(), "upper": opus_rate.as_dict(), "coverage_on_claimed_finite_universe": "1"},
            "confidence_semantics": "FULL_ENUMERATION_OF_THE_CLAIMED_FINITE_ACCEPTANCE_UNIVERSE__DEGENERATE_EXACT_INTERVAL__NO_SAMPLING_UNCERTAINTY",
            "multiplicity_semantics": "TRIVIAL_JOINT_COVERAGE_ONE_FOR_FULLY_ENUMERATED_FINITE_UNIVERSES__NO_STOCHASTIC_MULTIPLICITY_PENALTY",
            "stopping_rule": "FIXED_COMPLETE_CASE_UNIVERSE__NO_SEQUENTIAL_STOPPING",
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except ReducerError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }


def monotonicity_theorem(total: int) -> bool:
    if not isinstance(total, int) or total <= 0:
        raise ReducerError("TOTAL_MUST_BE_POSITIVE")
    # Exact finite-scope reducer is k/n. For fixed positive n, k2 >= k1
    # iff k2*n >= k1*n, so the reducer is monotone in success count.
    for k1 in range(total + 1):
        for k2 in range(k1, total + 1):
            a = Rational.from_count(k1, total)
            b = Rational.from_count(k2, total)
            if b.numerator * a.denominator < a.numerator * b.denominator:
                return False
    return True

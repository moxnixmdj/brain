"""Exact finite-poset characterization for target-free monotone dominance.

For a finite scope-complete material partial order Y and Brain support S, universal
noninferiority against every target distribution and every bounded monotone
utility is possible without target-distribution information iff S is exactly the
unique greatest element of Y.

This kernel proves only the finite order-theoretic characterization. Applying it
to a live runtime still requires separate scope-complete evidence that the
declared outcome abstraction/order is sound and that the runtime support is
confined to the declared support.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_HIDDEN_EVALUATOR_TARGET_FREE_CHARACTERIZATION_V1"


class CertificateError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def characterize_target_free_monotone_dominance(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        outcomes = [_token(x, "OUTCOME") for x in _sequence(cert.get("outcomes"), "OUTCOMES")]
        if not outcomes:
            raise CertificateError("OUTCOMES_EMPTY")
        if len(outcomes) != len(set(outcomes)):
            raise CertificateError("OUTCOMES_DUPLICATE")
        outcome_set = set(outcomes)

        reach: dict[str, set[str]] = {x: {x} for x in outcomes}
        for i, edge in enumerate(_sequence(cert.get("dominance_edges"), "DOMINANCE_EDGES")):
            pair = _sequence(edge, f"EDGE_{i}")
            if len(pair) != 2:
                raise CertificateError(f"EDGE_{i}_ARITY")
            better = _token(pair[0], f"EDGE_{i}_BETTER")
            worse = _token(pair[1], f"EDGE_{i}_WORSE")
            if better not in outcome_set or worse not in outcome_set:
                raise CertificateError(f"EDGE_{i}_UNKNOWN_OUTCOME")
            reach[better].add(worse)

        changed = True
        while changed:
            changed = False
            for a in outcomes:
                closure = set(reach[a])
                for b in tuple(reach[a]):
                    closure.update(reach[b])
                if closure != reach[a]:
                    reach[a] = closure
                    changed = True

        for a in outcomes:
            for b in outcomes:
                if a != b and b in reach[a] and a in reach[b]:
                    raise CertificateError("DOMINANCE_NOT_ANTISYMMETRIC:" + a + ":" + b)

        support = [_token(x, "BRAIN_SUPPORT") for x in _sequence(cert.get("brain_support"), "BRAIN_SUPPORT")]
        if not support:
            raise CertificateError("BRAIN_SUPPORT_EMPTY")
        if len(support) != len(set(support)):
            raise CertificateError("BRAIN_SUPPORT_DUPLICATE")
        if any(x not in outcome_set for x in support):
            raise CertificateError("BRAIN_SUPPORT_UNKNOWN_OUTCOME")

        greatest = [g for g in outcomes if all(y in reach[g] for y in outcomes)]
        if len(greatest) > 1:
            raise CertificateError("INTERNAL_PARTIAL_ORDER_GREATEST_NONUNIQUE")

        greatest_element = greatest[0] if greatest else None
        universal = greatest_element is not None and support == [greatest_element]

        counterexample = None
        if not universal:
            for y in outcomes:
                bad = [b for b in support if y not in reach[b]]
                if bad:
                    upper_set = [z for z in outcomes if y in reach[z]]
                    counterexample = {
                        "target_distribution": "DELTA:" + y,
                        "monotone_utility": "INDICATOR_OF_UPPER_SET:" + y,
                        "upper_set": upper_set,
                        "brain_support_outside_upper_set": bad,
                        "logic": "POSITIVE_BRAIN_MASS_OUTSIDE_THIS_UPPER_SET_IMPLIES_E_Q_U_LT_1_WHILE_E_DELTA_Y_U_EQ_1",
                    }
                    break
            if counterexample is None:
                raise CertificateError("CHARACTERIZATION_CONTRADICTION")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "outcome_count": len(outcomes),
            "brain_support_count": len(support),
            "greatest_element": greatest_element,
            "target_free_universal_monotone_dominance": universal,
            "target_distribution_or_additional_evaluator_information_required": not universal,
            "counterexample": counterexample,
            "application_requires_scope_complete_order_receipt": True,
            "application_requires_scope_complete_brain_support_receipt": True,
            "theorem": "TARGET_FREE_UNIVERSAL_MONOTONE_DOMINANCE_IFF_UNIQUE_GREATEST_SUPPORT",
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "target_free_universal_monotone_dominance": None,
            "target_distribution_or_additional_evaluator_information_required": None,
            "acceptance_credit_delta": 0,
        }

"""Bounded zero-learned scientific hypothesis and test-selection kernel.

This module proves only a finite, explicit-mechanism subregion of
SCIENTIFIC_HYPOTHESIS_AND_QUESTION_FORMATION_001.

It does NOT invent domain semantics, mechanisms, priors, or observation models.
Given:
  * normalized anomaly observations,
  * an explicit finite mechanism grammar,
  * explicit priors,
  * explicit feasible tests and P(outcome | hypothesis),
it:
  1. generates the hypotheses whose declared mechanism predicts an observed anomaly,
  2. normalizes their explicit priors,
  3. computes exact Shannon expected information gain for every feasible test,
  4. selects the maximum information-gain-per-cost test fail-closed.

Persistent learned state: zero bytes.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUNDED_SCIENTIFIC_HYPOTHESIS_KERNEL_V1"


class HypothesisKernelError(ValueError):
    pass


def _finite_number(x: Any, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise HypothesisKernelError(f"{name}_NOT_NUMBER")
    y = float(x)
    if not math.isfinite(y):
        raise HypothesisKernelError(f"{name}_NOT_FINITE")
    return y


def _entropy(weights: Mapping[str, float]) -> float:
    out = 0.0
    for p in weights.values():
        if p > 0.0:
            out -= p * math.log2(p)
    return out


def _normalize_positive(weights: Mapping[str, float], label: str) -> dict[str, float]:
    if not weights:
        raise HypothesisKernelError(f"{label}_EMPTY")
    cleaned: dict[str, float] = {}
    for key, value in weights.items():
        if not isinstance(key, str) or not key:
            raise HypothesisKernelError(f"{label}_ID_INVALID")
        p = _finite_number(value, f"{label}:{key}")
        if p < 0.0:
            raise HypothesisKernelError(f"{label}_NEGATIVE:{key}")
        cleaned[key] = p
    total = sum(cleaned.values())
    if total <= 0.0:
        raise HypothesisKernelError(f"{label}_ZERO_MASS")
    return {k: v / total for k, v in cleaned.items()}


def _parse_observations(rows: Any) -> set[tuple[str, int]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise HypothesisKernelError("OBSERVATIONS_INVALID")
    out: set[tuple[str, int]] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise HypothesisKernelError(f"OBSERVATION_NOT_OBJECT:{i}")
        variable = row.get("variable")
        direction = row.get("direction")
        if not isinstance(variable, str) or not variable:
            raise HypothesisKernelError(f"OBSERVATION_VARIABLE_INVALID:{i}")
        if isinstance(direction, bool) or direction not in (-1, 1):
            raise HypothesisKernelError(f"OBSERVATION_DIRECTION_INVALID:{i}")
        out.add((variable, int(direction)))
    return out


def generate_hypotheses(
    *,
    observations: Any,
    mechanisms: Any,
) -> list[dict[str, Any]]:
    observed = _parse_observations(observations)
    if not isinstance(mechanisms, Sequence) or isinstance(mechanisms, (str, bytes)):
        raise HypothesisKernelError("MECHANISMS_NOT_LIST")

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for i, row in enumerate(mechanisms):
        if not isinstance(row, Mapping):
            raise HypothesisKernelError(f"MECHANISM_NOT_OBJECT:{i}")
        mid = row.get("id")
        target = row.get("target")
        direction = row.get("predicted_direction")
        statement = row.get("hypothesis")
        if not isinstance(mid, str) or not mid:
            raise HypothesisKernelError(f"MECHANISM_ID_INVALID:{i}")
        if mid in seen:
            raise HypothesisKernelError(f"MECHANISM_ID_DUPLICATE:{mid}")
        seen.add(mid)
        if not isinstance(target, str) or not target:
            raise HypothesisKernelError(f"MECHANISM_TARGET_INVALID:{mid}")
        if isinstance(direction, bool) or direction not in (-1, 1):
            raise HypothesisKernelError(f"MECHANISM_DIRECTION_INVALID:{mid}")
        if not isinstance(statement, str) or not statement.strip():
            raise HypothesisKernelError(f"MECHANISM_HYPOTHESIS_INVALID:{mid}")

        matches = sorted(
            variable for variable, sign in observed
            if variable == target and sign == int(direction)
        )
        if not matches:
            continue
        candidates.append({
            "hypothesis_id": mid,
            "hypothesis": statement.strip(),
            "predicted_target": target,
            "predicted_direction": int(direction),
            "matched_observations": matches,
            "falsifiable": True,
            "semantic_origin": "EXPLICIT_MECHANISM_GRAMMAR",
        })
    return candidates


def _test_information_gain(
    *,
    posterior: Mapping[str, float],
    test: Mapping[str, Any],
) -> dict[str, Any]:
    test_id = test.get("id")
    if not isinstance(test_id, str) or not test_id:
        raise HypothesisKernelError("TEST_ID_INVALID")
    cost = _finite_number(test.get("cost"), f"TEST_COST:{test_id}")
    if cost <= 0.0:
        raise HypothesisKernelError(f"TEST_COST_NONPOSITIVE:{test_id}")
    likelihoods = test.get("likelihoods")
    if not isinstance(likelihoods, Mapping):
        raise HypothesisKernelError(f"TEST_LIKELIHOODS_INVALID:{test_id}")

    outcome_names: set[str] | None = None
    parsed: dict[str, dict[str, float]] = {}
    for hid in posterior:
        row = likelihoods.get(hid)
        if not isinstance(row, Mapping) or not row:
            raise HypothesisKernelError(f"TEST_HYPOTHESIS_LIKELIHOOD_MISSING:{test_id}:{hid}")
        probs: dict[str, float] = {}
        for outcome, raw in row.items():
            if not isinstance(outcome, str) or not outcome:
                raise HypothesisKernelError(f"TEST_OUTCOME_INVALID:{test_id}:{hid}")
            p = _finite_number(raw, f"TEST_PROB:{test_id}:{hid}:{outcome}")
            if p < 0.0 or p > 1.0:
                raise HypothesisKernelError(f"TEST_PROB_OUT_OF_RANGE:{test_id}:{hid}:{outcome}")
            probs[outcome] = p
        if abs(sum(probs.values()) - 1.0) > 1e-9:
            raise HypothesisKernelError(f"TEST_PROB_NOT_NORMALIZED:{test_id}:{hid}")
        if outcome_names is None:
            outcome_names = set(probs)
        elif set(probs) != outcome_names:
            raise HypothesisKernelError(f"TEST_OUTCOME_SET_MISMATCH:{test_id}:{hid}")
        parsed[hid] = probs

    assert outcome_names is not None
    prior_entropy = _entropy(posterior)
    expected_posterior_entropy = 0.0
    outcome_masses: dict[str, float] = {}

    for outcome in sorted(outcome_names):
        mass = sum(posterior[hid] * parsed[hid][outcome] for hid in posterior)
        outcome_masses[outcome] = mass
        if mass <= 0.0:
            continue
        conditional = {
            hid: posterior[hid] * parsed[hid][outcome] / mass
            for hid in posterior
        }
        expected_posterior_entropy += mass * _entropy(conditional)

    eig = max(0.0, prior_entropy - expected_posterior_entropy)
    return {
        "test_id": test_id,
        "cost": cost,
        "expected_information_gain_bits": eig,
        "information_gain_per_cost": eig / cost,
        "outcome_masses": outcome_masses,
    }


def formulate_and_rank(
    *,
    observations: Any,
    mechanisms: Any,
    priors: Any,
    tests: Any,
    max_test_cost: Any,
) -> dict[str, Any]:
    candidates = generate_hypotheses(
        observations=observations,
        mechanisms=mechanisms,
    )
    if not candidates:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED_NO_EXPLICIT_MECHANISM_MATCH",
            "hypotheses": [],
            "selected_test": None,
            "persistent_learned_bytes": 0,
            "terminal_authority": False,
            "semantic_authority": False,
        }

    if not isinstance(priors, Mapping):
        raise HypothesisKernelError("PRIORS_NOT_MAPPING")
    ids = [row["hypothesis_id"] for row in candidates]
    missing = sorted(set(ids) - set(priors))
    if missing:
        raise HypothesisKernelError("PRIORS_MISSING:" + ",".join(missing))
    extra = sorted(set(priors) - set(ids))
    if extra:
        raise HypothesisKernelError("PRIORS_FOR_NONCANDIDATES:" + ",".join(extra))
    posterior = _normalize_positive({hid: priors[hid] for hid in ids}, "PRIORS")

    budget = _finite_number(max_test_cost, "MAX_TEST_COST")
    if budget <= 0.0:
        raise HypothesisKernelError("MAX_TEST_COST_NONPOSITIVE")
    if not isinstance(tests, Sequence) or isinstance(tests, (str, bytes)):
        raise HypothesisKernelError("TESTS_NOT_LIST")

    test_rows: list[dict[str, Any]] = []
    seen_tests: set[str] = set()
    for i, raw in enumerate(tests):
        if not isinstance(raw, Mapping):
            raise HypothesisKernelError(f"TEST_NOT_OBJECT:{i}")
        tid = raw.get("id")
        if not isinstance(tid, str) or not tid:
            raise HypothesisKernelError(f"TEST_ID_INVALID:{i}")
        if tid in seen_tests:
            raise HypothesisKernelError(f"TEST_ID_DUPLICATE:{tid}")
        seen_tests.add(tid)
        if raw.get("feasible") is not True:
            continue
        row = _test_information_gain(posterior=posterior, test=raw)
        if row["cost"] <= budget:
            test_rows.append(row)

    ranked_hypotheses = sorted(
        [
            {**row, "prior_probability": posterior[row["hypothesis_id"]]}
            for row in candidates
        ],
        key=lambda row: (-row["prior_probability"], row["hypothesis_id"]),
    )
    ranked_tests = sorted(
        test_rows,
        key=lambda row: (
            -row["information_gain_per_cost"],
            -row["expected_information_gain_bits"],
            row["cost"],
            row["test_id"],
        ),
    )

    selected = ranked_tests[0] if ranked_tests and ranked_tests[0]["expected_information_gain_bits"] > 0.0 else None
    status = "BOUNDED_HYPOTHESIS_AND_TEST_SELECTED" if selected else "UNRESOLVED_NO_DISCRIMINATING_FEASIBLE_TEST"
    return {
        "schema": SCHEMA,
        "status": status,
        "hypotheses": ranked_hypotheses,
        "ranked_tests": ranked_tests,
        "selected_test": selected,
        "selection_rule": "MAX_EXPECTED_INFORMATION_GAIN_PER_COST__THEN_RAW_INFORMATION_GAIN__THEN_LOWER_COST__THEN_TEST_ID",
        "scope_boundary": {
            "mechanism_semantics": "MUST_BE_EXPLICIT_INPUT",
            "priors": "MUST_BE_EXPLICIT_INPUT",
            "observation_model": "MUST_BE_EXPLICIT_INPUT",
            "open_ended_mechanism_invention": "NOT_OWNED",
            "scientific_coherence_inference": "NOT_OWNED_BEYOND_EXPLICIT_GRAMMAR",
        },
        "persistent_learned_bytes": 0,
        "terminal_authority": False,
        "semantic_authority": False,
    }

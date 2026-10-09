"""Independent verifier for bounded finance semantic hypothesis-product control V1."""
from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity

SCHEMA = "PROJECT_BRAIN_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_RESULT_V1"
MAX_DIMENSIONS = 8
MAX_WORLDS = 256


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verified": False,
        "producer_independent": True,
        "reason": reason,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
            raise ValueError("CASE_SCHEMA_INVALID")
        if case.get("domain") != "FINANCE":
            raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
        if case.get("cartesian_product_complete") is not True:
            raise ValueError("CARTESIAN_PRODUCT_COMPLETENESS_REQUIRED")
        if case.get("terminal_signature_factorization_complete") is not True:
            raise ValueError("TERMINAL_SIGNATURE_FACTORIZATION_COMPLETENESS_REQUIRED")

        raw_dimensions = case.get("dimensions")
        if (
            not isinstance(raw_dimensions, Sequence)
            or isinstance(raw_dimensions, (str, bytes))
            or not raw_dimensions
            or len(raw_dimensions) > MAX_DIMENSIONS
        ):
            raise ValueError("DIMENSIONS_INVALID")

        dimensions = []
        candidate_ids = {}
        seen_dimensions = set()
        world_count = 1
        for raw in raw_dimensions:
            if not isinstance(raw, Mapping):
                raise ValueError("DIMENSION_NOT_OBJECT")
            dimension_id = str(raw.get("dimension_id") or "").strip()
            if not dimension_id or dimension_id in seen_dimensions:
                raise ValueError("DIMENSION_ID_INVALID")
            if raw.get("candidate_set_complete") is not True:
                raise ValueError(
                    "CANDIDATE_SET_COMPLETENESS_REQUIRED:" + dimension_id
                )
            seen_dimensions.add(dimension_id)
            raw_candidates = raw.get("candidates")
            if (
                not isinstance(raw_candidates, Sequence)
                or isinstance(raw_candidates, (str, bytes))
                or not raw_candidates
            ):
                raise ValueError("CANDIDATES_REQUIRED:" + dimension_id)

            candidates = []
            seen_candidates = set()
            for candidate in raw_candidates:
                if not isinstance(candidate, Mapping):
                    raise ValueError("CANDIDATE_NOT_OBJECT")
                candidate_id = str(candidate.get("candidate_id") or "").strip()
                fragment = candidate.get("terminal_signature_fragment")
                if (
                    not candidate_id
                    or candidate_id in seen_candidates
                    or not isinstance(fragment, Mapping)
                ):
                    raise ValueError("CANDIDATE_INVALID:" + dimension_id)
                seen_candidates.add(candidate_id)
                candidates.append((candidate_id, dict(fragment)))
            world_count *= len(candidates)
            if world_count > MAX_WORLDS:
                raise ValueError("JOINT_WORLD_LIMIT_EXCEEDED")
            dimensions.append((dimension_id, candidates))
            candidate_ids[dimension_id] = seen_candidates

        raw_observations = case.get("observations", [])
        if (
            not isinstance(raw_observations, Sequence)
            or isinstance(raw_observations, (str, bytes))
        ):
            raise ValueError("OBSERVATIONS_INVALID")
        observations = []
        seen_observations = set()
        for raw in raw_observations:
            if not isinstance(raw, Mapping):
                raise ValueError("OBSERVATION_NOT_OBJECT")
            observation_id = str(raw.get("observation_id") or "").strip()
            dimension_id = str(raw.get("dimension_id") or "").strip()
            outcomes = raw.get("outcomes")
            cost = raw.get("cost_units")
            if (
                not observation_id
                or observation_id in seen_observations
                or dimension_id not in candidate_ids
            ):
                raise ValueError("OBSERVATION_ID_OR_DIMENSION_INVALID")
            if (
                raw.get("outcome_map_complete") is not True
                or not isinstance(outcomes, Mapping)
                or set(outcomes) != candidate_ids[dimension_id]
            ):
                raise ValueError(
                    "OBSERVATION_CANDIDATE_COVERAGE_INCOMPLETE:"
                    + observation_id
                )
            if (
                not isinstance(cost, (int, float))
                or isinstance(cost, bool)
                or cost < 0
            ):
                raise ValueError("OBSERVATION_COST_INVALID:" + observation_id)
            seen_observations.add(observation_id)
            observations.append(
                (observation_id, dimension_id, dict(outcomes), float(cost))
            )

        worlds = []
        for combination in product(*[row[1] for row in dimensions]):
            assignment = {
                dimensions[index][0]: combination[index][0]
                for index in range(len(dimensions))
            }
            signature = {}
            for _, fragment in combination:
                for key, value in fragment.items():
                    if key in signature and signature[key] != value:
                        raise ValueError(
                            "TERMINAL_SIGNATURE_FRAGMENT_CONFLICT:" + str(key)
                        )
                    signature[key] = value
            worlds.append(
                (
                    "joint:" + _sha(assignment)[:24],
                    assignment,
                    signature,
                )
            )

        lifted = []
        for observation_id, dimension_id, outcomes, cost in observations:
            lifted.append(
                {
                    "observation_id": observation_id,
                    "cost_units": cost,
                    "outcome_map_complete": True,
                    "outcomes": {
                        world_id: outcomes[assignment[dimension_id]]
                        for world_id, assignment, _ in worlds
                    },
                }
            )

        decision = ambiguity.decide(
            {
                "ambiguity_owner": str(
                    case.get("ambiguity_owner") or ""
                ).strip().upper(),
                "hypothesis_set_complete": True,
                "worlds": [
                    {
                        "world_id": world_id,
                        "terminal_signature_complete": True,
                        "terminal_signature": signature,
                    }
                    for world_id, _, signature in worlds
                ],
                "observations": lifted,
            }
        )
        core = {
            "domain": "FINANCE",
            "dimension_ids": [row[0] for row in dimensions],
            "dimension_candidate_counts": {
                row[0]: len(row[1]) for row in dimensions
            },
            "joint_world_count": len(worlds),
            "joint_hypothesis_set_complete": True,
            "cartesian_product_complete": True,
            "terminal_signature_factorization_complete": True,
            "joint_world_assignments": {
                world_id: assignment for world_id, assignment, _ in worlds
            },
            "decision": dict(decision),
        }
        expected = {
            "schema": RESULT_SCHEMA,
            "status": "PASS__BOUNDED_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_COMPUTED",
            "pass": True,
            **core,
            "result_sha256": _sha(core),
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        if not isinstance(result, Mapping) or dict(result) != expected:
            raise ValueError("RESULT_RECOMPUTATION_MISMATCH")
        return {
            "schema": SCHEMA,
            "verified": True,
            "producer_independent": True,
            "joint_world_count": len(worlds),
            "result_sha256": expected["result_sha256"],
            "verification_authority_mutated": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

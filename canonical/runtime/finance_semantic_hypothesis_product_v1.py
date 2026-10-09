"""Bounded finance semantic hypothesis-product control V1.

Composes multiple declared-complete finite semantic dimensions into one joint
decision-relative ambiguity problem. It never infers candidate truth.

V1 admits only an explicitly complete Cartesian product with conflict-free,
complete factorized terminal-signature fragments. Observations are dimension
local and must cover that dimension's complete candidate set.

No semantic-truth, policy-adequacy, execution, promotion, acceptance, or terminal
authority is minted here.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity

SCHEMA = "PROJECT_BRAIN_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_V1"
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


def _normalize(case: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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

    dimensions: list[dict[str, Any]] = []
    seen_dimensions: set[str] = set()
    world_count = 1
    for index, raw in enumerate(raw_dimensions):
        if not isinstance(raw, Mapping):
            raise ValueError(f"DIMENSION_NOT_OBJECT:{index}")
        dimension_id = str(raw.get("dimension_id") or "").strip()
        if not dimension_id or dimension_id in seen_dimensions:
            raise ValueError(f"DIMENSION_ID_INVALID:{index}")
        seen_dimensions.add(dimension_id)
        if raw.get("candidate_set_complete") is not True:
            raise ValueError("CANDIDATE_SET_COMPLETENESS_REQUIRED:" + dimension_id)
        raw_candidates = raw.get("candidates")
        if (
            not isinstance(raw_candidates, Sequence)
            or isinstance(raw_candidates, (str, bytes))
            or not raw_candidates
        ):
            raise ValueError("CANDIDATES_REQUIRED:" + dimension_id)

        candidates: list[dict[str, Any]] = []
        seen_candidates: set[str] = set()
        for candidate_index, candidate in enumerate(raw_candidates):
            if not isinstance(candidate, Mapping):
                raise ValueError(
                    f"CANDIDATE_NOT_OBJECT:{dimension_id}:{candidate_index}"
                )
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            fragment = candidate.get("terminal_signature_fragment")
            if not candidate_id or candidate_id in seen_candidates:
                raise ValueError(
                    f"CANDIDATE_ID_INVALID:{dimension_id}:{candidate_index}"
                )
            if not isinstance(fragment, Mapping):
                raise ValueError(
                    "TERMINAL_SIGNATURE_FRAGMENT_INVALID:" + candidate_id
                )
            seen_candidates.add(candidate_id)
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "terminal_signature_fragment": dict(fragment),
                }
            )

        world_count *= len(candidates)
        if world_count > MAX_WORLDS:
            raise ValueError("JOINT_WORLD_LIMIT_EXCEEDED")
        dimensions.append(
            {"dimension_id": dimension_id, "candidates": candidates}
        )

    candidate_ids = {
        row["dimension_id"]: {c["candidate_id"] for c in row["candidates"]}
        for row in dimensions
    }
    raw_observations = case.get("observations", [])
    if (
        not isinstance(raw_observations, Sequence)
        or isinstance(raw_observations, (str, bytes))
    ):
        raise ValueError("OBSERVATIONS_INVALID")

    observations: list[dict[str, Any]] = []
    seen_observations: set[str] = set()
    for index, raw in enumerate(raw_observations):
        if not isinstance(raw, Mapping):
            raise ValueError(f"OBSERVATION_NOT_OBJECT:{index}")
        observation_id = str(raw.get("observation_id") or "").strip()
        dimension_id = str(raw.get("dimension_id") or "").strip()
        outcomes = raw.get("outcomes")
        cost = raw.get("cost_units")
        if not observation_id or observation_id in seen_observations:
            raise ValueError(f"OBSERVATION_ID_INVALID:{index}")
        if dimension_id not in candidate_ids:
            raise ValueError("OBSERVATION_DIMENSION_UNKNOWN:" + observation_id)
        if (
            raw.get("outcome_map_complete") is not True
            or not isinstance(outcomes, Mapping)
            or set(outcomes) != candidate_ids[dimension_id]
        ):
            raise ValueError(
                "OBSERVATION_CANDIDATE_COVERAGE_INCOMPLETE:" + observation_id
            )
        if (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or cost < 0
        ):
            raise ValueError("OBSERVATION_COST_INVALID:" + observation_id)
        seen_observations.add(observation_id)
        observations.append(
            {
                "observation_id": observation_id,
                "dimension_id": dimension_id,
                "outcomes": dict(outcomes),
                "cost_units": float(cost),
            }
        )

    return dimensions, observations


def _joint_worlds(dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    worlds: list[dict[str, Any]] = []
    for combination in product(*[row["candidates"] for row in dimensions]):
        assignment = {
            dimensions[index]["dimension_id"]: combination[index]["candidate_id"]
            for index in range(len(dimensions))
        }
        signature: dict[str, Any] = {}
        for candidate in combination:
            for key, value in candidate["terminal_signature_fragment"].items():
                if key in signature and signature[key] != value:
                    raise ValueError(
                        "TERMINAL_SIGNATURE_FRAGMENT_CONFLICT:" + str(key)
                    )
                signature[key] = value
        worlds.append(
            {
                "world_id": "joint:" + _sha(assignment)[:24],
                "assignment": assignment,
                "terminal_signature_complete": True,
                "terminal_signature": signature,
            }
        )
    return worlds


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    dimensions, observations = _normalize(case)
    worlds = _joint_worlds(dimensions)

    lifted_observations = []
    for observation in observations:
        lifted_observations.append(
            {
                "observation_id": observation["observation_id"],
                "cost_units": observation["cost_units"],
                "outcome_map_complete": True,
                "outcomes": {
                    world["world_id"]: observation["outcomes"][
                        world["assignment"][observation["dimension_id"]]
                    ]
                    for world in worlds
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
                    "world_id": world["world_id"],
                    "terminal_signature_complete": True,
                    "terminal_signature": world["terminal_signature"],
                }
                for world in worlds
            ],
            "observations": lifted_observations,
        }
    )

    core = {
        "domain": "FINANCE",
        "dimension_ids": [row["dimension_id"] for row in dimensions],
        "dimension_candidate_counts": {
            row["dimension_id"]: len(row["candidates"]) for row in dimensions
        },
        "joint_world_count": len(worlds),
        "joint_hypothesis_set_complete": True,
        "cartesian_product_complete": True,
        "terminal_signature_factorization_complete": True,
        "joint_world_assignments": {
            world["world_id"]: world["assignment"] for world in worlds
        },
        "decision": dict(decision),
    }
    return {
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

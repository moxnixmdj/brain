"""Robust functional-adequacy CEGAR kernel v1.

This module does one narrow thing exactly:

Given a declared complete evaluator-domain cover, a sound over-approximation of
the still-possible worlds, and sound upper bounds on the loss of each Brain-owned
candidate law in every (cover cell, world) pair, either:

1. certify that one candidate law is adequate in every surviving world across
   the entire declared cover; or
2. return the load-bearing counterexample cell/world where the best candidate
   still violates the bound.

It does not infer benchmark semantics, prove that the challenge cover is
complete, manufacture loss bounds, observe the counterexample, or grant any
benchmark/family/capability/terminal credit.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ROBUST_FUNCTIONAL_ADEQUACY_CEGAR_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "common_law_certified": False,
        "counterexample_selected": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _fraction(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(label + "_BOOL_INVALID")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str) and value.strip():
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(label + "_RATIONAL_INVALID") from exc
    raise ValueError(label + "_EXACT_RATIONAL_STRING_OR_INT_REQUIRED")


def _fstr(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _string_ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(label + "_NONEMPTY_LIST_REQUIRED")
    out = list(value)
    if any(not isinstance(x, str) or not x for x in out):
        raise ValueError(label + "_INVALID_ID")
    if len(out) != len(set(out)):
        raise ValueError(label + "_DUPLICATE")
    return out


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")
    if problem.get("metric_semantics_bound") is not True:
        return _fail("METRIC_SEMANTICS_UNBOUND")
    if problem.get("challenge_cover_complete") is not True:
        return _fail("CHALLENGE_COVER_COMPLETENESS_UNPROVED")
    if problem.get("loss_bounds_sound") is not True:
        return _fail("LOSS_BOUND_SOUNDNESS_UNPROVED")
    if problem.get("world_cover_sound") is not True:
        return _fail("WORLD_COVER_SOUNDNESS_UNPROVED")

    try:
        threshold = _fraction(problem.get("adequacy_threshold"), "ADEQUACY_THRESHOLD")
        if threshold < 0:
            return _fail("ADEQUACY_THRESHOLD_NEGATIVE")
        world_ids = _string_ids(problem.get("world_ids"), "WORLD_IDS")
        challenge_ids = _string_ids(problem.get("challenge_ids"), "CHALLENGE_IDS")
    except ValueError as exc:
        return _fail("EXACT_BINDING_FAILED", detail=str(exc))

    candidates_raw = problem.get("candidates")
    if (
        not isinstance(candidates_raw, Sequence)
        or isinstance(candidates_raw, (str, bytes))
        or not candidates_raw
    ):
        return _fail("CANDIDATES_REQUIRED")

    expected_worlds = set(world_ids)
    expected_challenges = set(challenge_ids)
    seen_candidates: set[str] = set()
    summaries: list[dict[str, Any]] = []

    try:
        for index, raw in enumerate(candidates_raw):
            if not isinstance(raw, Mapping):
                return _fail(f"CANDIDATE_NOT_OBJECT:{index}")
            candidate_id = raw.get("candidate_id")
            if (
                not isinstance(candidate_id, str)
                or not candidate_id
                or candidate_id in seen_candidates
            ):
                return _fail(f"CANDIDATE_ID_INVALID_OR_DUPLICATE:{index}")
            seen_candidates.add(candidate_id)

            if raw.get("brain_owned") is not True:
                return _fail(f"CANDIDATE_NOT_BRAIN_OWNED:{candidate_id}")
            commitment = raw.get("policy_commitment_sha256")
            if not isinstance(commitment, str) or _SHA256.fullmatch(commitment) is None:
                return _fail(f"CANDIDATE_POLICY_COMMITMENT_INVALID:{candidate_id}")

            bounds_raw = raw.get("loss_upper_bounds")
            if not isinstance(bounds_raw, Mapping) or set(bounds_raw) != expected_challenges:
                return _fail(f"CANDIDATE_CHALLENGE_DOMAIN_MISMATCH:{candidate_id}")

            worst_loss = Fraction(-1, 1)
            worst_challenge = None
            worst_world = None
            normalized_bounds: dict[str, dict[str, str]] = {}

            for challenge_id in challenge_ids:
                per_world_raw = bounds_raw[challenge_id]
                if not isinstance(per_world_raw, Mapping) or set(per_world_raw) != expected_worlds:
                    return _fail(
                        f"CANDIDATE_WORLD_DOMAIN_MISMATCH:{candidate_id}:{challenge_id}"
                    )
                normalized_bounds[challenge_id] = {}
                for world_id in world_ids:
                    loss = _fraction(
                        per_world_raw[world_id],
                        f"LOSS:{candidate_id}:{challenge_id}:{world_id}",
                    )
                    if loss < 0:
                        return _fail(
                            f"LOSS_BOUND_NEGATIVE:{candidate_id}:{challenge_id}:{world_id}"
                        )
                    normalized_bounds[challenge_id][world_id] = _fstr(loss)
                    key = (loss, challenge_id, world_id)
                    current_key = (
                        worst_loss,
                        worst_challenge or "",
                        worst_world or "",
                    )
                    if key > current_key:
                        worst_loss = loss
                        worst_challenge = challenge_id
                        worst_world = world_id

            summaries.append(
                {
                    "candidate_id": candidate_id,
                    "policy_commitment_sha256": commitment,
                    "worst_case_loss_upper_bound": _fstr(worst_loss),
                    "worst_case_challenge_id": worst_challenge,
                    "worst_case_world_id": worst_world,
                    "loss_upper_bounds": normalized_bounds,
                }
            )
    except ValueError as exc:
        return _fail("EXACT_LOSS_BINDING_FAILED", detail=str(exc))

    # Minimax law: smallest proved worst-case loss. Candidate ID is a deterministic tie-break.
    summaries.sort(
        key=lambda row: (
            Fraction(row["worst_case_loss_upper_bound"]),
            row["candidate_id"],
        )
    )
    selected = summaries[0]
    selected_loss = Fraction(selected["worst_case_loss_upper_bound"])
    adequate = selected_loss <= threshold

    receipt_payload = {
        "threshold": _fstr(threshold),
        "world_ids": world_ids,
        "challenge_ids": challenge_ids,
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_policy_commitment_sha256": selected["policy_commitment_sha256"],
        "selected_worst_case_loss_upper_bound": _fstr(selected_loss),
        "adequate": adequate,
    }
    receipt_sha256 = hashlib.sha256(
        json.dumps(receipt_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    common = {
        "schema": SCHEMA,
        "world_count": len(world_ids),
        "challenge_count": len(challenge_ids),
        "candidate_count": len(summaries),
        "adequacy_threshold": _fstr(threshold),
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_policy_commitment_sha256": selected["policy_commitment_sha256"],
        "selected_worst_case_loss_upper_bound": _fstr(selected_loss),
        "candidate_summaries": summaries,
        "certificate_sha256": receipt_sha256,
        "metric_semantics_bound": True,
        "challenge_cover_complete": True,
        "loss_bounds_sound": True,
        "world_cover_sound": True,
        "exact_arithmetic": "fractions.Fraction",
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

    if adequate:
        return {
            **common,
            "pass": True,
            "status": "PASS__COMMON_LAW_ROBUSTLY_ADEQUATE_ON_DECLARED_COMPLETE_COVER",
            "common_law_certified": True,
            "counterexample_selected": False,
            "selected_counterexample": None,
            "theorem": (
                "ONE_BRAIN_OWNED_CANDIDATE_HAS_A_SOUND_LOSS_UPPER_BOUND_AT_OR_BELOW_"
                "THE_BOUND_ADEQUACY_THRESHOLD_FOR_EVERY_SURVIVING_WORLD_ACROSS_EVERY_"
                "CELL_OF_THE_DECLARED_COMPLETE_EVALUATOR_DOMAIN_COVER"
            ),
            "boundary": (
                "CREDIT_REQUIRES_UPSTREAM_INDEPENDENT_AUTHENTICATION_OF_METRIC_SEMANTICS_"
                "WORLD_COVER_CHALLENGE_COVER_AND_LOSS_BOUND_SOUNDNESS;THIS_KERNEL_ONLY_"
                "CHECKS_THE_BOUND_PROBLEM_AND_NEVER_GRANTS_BENCHMARK_OR_TERMINAL_CREDIT"
            ),
        }

    return {
        **common,
        "pass": False,
        "status": "UNRESOLVED__ROBUST_FUNCTIONAL_COUNTEREXAMPLE_SELECTED",
        "common_law_certified": False,
        "counterexample_selected": True,
        "selected_counterexample": {
            "challenge_id": selected["worst_case_challenge_id"],
            "world_id": selected["worst_case_world_id"],
            "proved_loss_upper_bound": selected["worst_case_loss_upper_bound"],
            "adequacy_threshold": _fstr(threshold),
        },
        "next_required": (
            "TRUTHFULLY_OBSERVE_OR_SOUNDLY_REFINE_THE_SELECTED_LOAD_BEARING_CHALLENGE_"
            "CELL__SHRINK_THE_WORLD_OR_PARAMETER_FEASIBLE_SET__RECOMPUTE_SOUND_LOSS_"
            "BOUNDS__AND_RERUN_UNTIL_COMMON_LAW_CERTIFIES_OR_BUDGET_EXHAUSTS"
        ),
        "query_optimality_claimed": False,
        "boundary": (
            "SELECTED_COUNTEREXAMPLE_IS_THE_WORST_CURRENT_ROBUST_ADEQUACY_VIOLATION_"
            "FOR_THE_MINIMAX_CANDIDATE__NOT_A_PROOF_OF_GLOBALLY_MINIMUM_QUERY_COUNT"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    del root
    return solve(args or {})

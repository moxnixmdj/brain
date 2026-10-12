"""Brain-owned grounded candidate policy frontier for R2.

This module converts independently verified plain-goal grounding into policy
*hypotheses* only. It never claims that a grounded capability is adequate for
the user's goal. P3 must authenticate adequacy over the current sound semantic
over-approximation before any policy can be selected.

V1 is deliberately limited to one action-bearing clause. Multi-clause goals
remain with the existing composition path rather than pretending one capability
solves an entire composite request.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.bound_capabilities import plain_goal_bound_grounding as grounding
from canonical.runtime.bound_capabilities import plain_goal_bound_grounding_verify as grounding_verify

SCHEMA = "PROJECT_BRAIN_R2_GROUNDED_CANDIDATE_POLICY_FRONTIER_V1"
POLICY_PREFIX = "BOUND_CAPABILITY_POLICY::"
GOAL_SCOPE_MARKER = "::RAW_GOAL_SHA256::"


def goal_scoped_policy_id(capability_id: str, goal: str) -> str:
    """Bind a grounded policy hypothesis to the exact raw goal bytes."""
    cid = str(capability_id or "").strip()
    text = str(goal or "").strip()
    if not cid or not text:
        raise ValueError("CAPABILITY_ID_AND_GOAL_REQUIRED")
    return POLICY_PREFIX + cid + GOAL_SCOPE_MARKER + sha256(text.encode("utf-8")).hexdigest()


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "policy_hypothesis_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _semantic_goal_tokens(text: str) -> set[str]:
    """Return action-intent tokens while excluding binding-only path/URL bytes."""
    cleaned = re.sub(r"https?://[^\s)\]}>]+", " ", str(text or ""))
    cleaned = re.sub(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",
        " ",
        cleaned,
    )
    cleaned = re.sub(
        r"(?<![A-Za-z0-9_])(?:[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8})(?![A-Za-z0-9_])",
        " ",
        cleaned,
    )
    return set(grounding._distinctive(grounding._tokens(cleaned)))


def _strong_semantic_candidate(row: Mapping[str, Any], semantic_tokens: set[str]) -> bool:
    lexical = row.get("lexical") or {}
    if not isinstance(lexical, Mapping):
        return False

    def goal_hits(field: str) -> list[tuple[str, str]]:
        raw = lexical.get(field) or []
        out: list[tuple[str, str]] = []
        if not isinstance(raw, list):
            return out
        for pair in raw:
            if (
                isinstance(pair, list)
                and len(pair) == 2
                and isinstance(pair[0], str)
                and isinstance(pair[1], str)
                and pair[0] in semantic_tokens
            ):
                out.append((pair[0], pair[1]))
        return out

    provides_hits = goal_hits("matched_provides")
    keyword_hits = goal_hits("matched_keywords")
    identity_hits = goal_hits("matched_identity")
    matched = {a for a, _ in provides_hits + keyword_hits + identity_hits}
    coverage = len(matched) / max(1, len(semantic_tokens))

    # An output/effect match is strong enough when it covers at least a quarter
    # of the goal tokens. Otherwise require two independent semantic
    # identity/keyword hits with meaningful goal coverage.
    return (bool(provides_hits) and coverage >= 0.25) or (
        len(keyword_hits) + len(identity_hits) >= 2 and coverage >= 0.34
    )


def propose(goal: str, *, repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    text = str(goal or "").strip()
    if not text:
        return {**_base("FAIL_CLOSED", passed=False), "reason": "GOAL_REQUIRED"}

    try:
        reg_path = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        if not reg_path.is_file():
            reg_path = (
                Path(__file__).resolve().parents[2]
                / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
            )
        registry_doc = json.loads(reg_path.read_text(encoding="utf-8"))
        registry = registry_doc.get("capabilities")
        if not isinstance(registry, Mapping):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "BOUND_CAPABILITY_REGISTRY_INVALID",
            }
        registry = goal_compiler._platform_admissible_registry(dict(registry))
        # Candidate policy discovery is semantic proposal generation, not
        # execution. Requiring all runtime inputs to be bound here causes false
        # negatives; bindability is enforced later before execution.
        result = grounding.ground(
            text,
            dict(registry),
            enforce_bindability=False,
        )
        verified, reason = grounding_verify.verify(text, result, registry)
        if not verified:
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_INDEPENDENT_VERIFICATION_FAILED:" + str(reason),
            }

        clauses = result.get("clauses")
        if not isinstance(clauses, list) or len(clauses) != 1:
            return {
                **_base("NOT_APPLICABLE__MULTI_CLAUSE_OR_EMPTY", passed=False),
                "grounding": deepcopy(dict(result)),
                "candidate_policy_count": 0,
            }
        clause = clauses[0]
        if not isinstance(clause, Mapping):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_CLAUSE_INVALID",
            }
        candidates = clause.get("candidates")
        if not isinstance(candidates, list):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_CANDIDATES_INVALID",
            }
        if not candidates:
            return {
                **_base("NOT_APPLICABLE__NO_GROUNDED_BOUND_CAPABILITY", passed=False),
                "grounding": deepcopy(dict(result)),
                "candidate_policy_count": 0,
            }

        semantic_tokens = _semantic_goal_tokens(text)
        strong_candidates = [
            row
            for row in candidates
            if isinstance(row, Mapping)
            and _strong_semantic_candidate(row, semantic_tokens)
        ]
        discarded_weak_candidate_ids = sorted(
            str(row.get("capability_id") or "")
            for row in candidates
            if isinstance(row, Mapping)
            and row not in strong_candidates
            and str(row.get("capability_id") or "")
        )
        if not strong_candidates:
            max_matched = max(
                (
                    len((r.get("lexical") or {}).get("matched_goal_tokens") or [])
                    for r in candidates
                    if isinstance(r, Mapping)
                ),
                default=0,
            )
            status = (
                "NOT_APPLICABLE__NO_GROUNDED_BOUND_CAPABILITY"
                if max_matched <= 1 and len(semantic_tokens) >= 4
                else "NOT_APPLICABLE__NO_STRONG_GROUNDED_BOUND_CAPABILITY"
            )
            return {
                **_base(status, passed=False),
                "grounding": deepcopy(dict(result)),
                "candidate_policy_count": 0,
                "discarded_weak_candidate_ids": discarded_weak_candidate_ids,
            }

        policy_conditions: dict[str, dict[str, str]] = {}
        capability_by_policy: dict[str, str] = {}
        for row in strong_candidates:
            if not isinstance(row, Mapping):
                return {
                    **_base("FAIL_CLOSED", passed=False),
                    "reason": "GROUNDING_CANDIDATE_NOT_OBJECT",
                }
            capability_id = str(row.get("capability_id") or "").strip()
            if not capability_id or capability_id not in registry:
                return {
                    **_base("FAIL_CLOSED", passed=False),
                    "reason": "GROUNDING_CANDIDATE_ID_INVALID",
                }
            policy_id = goal_scoped_policy_id(capability_id, text)
            policy_conditions[policy_id] = {"op": "TRUE"}
            capability_by_policy[policy_id] = capability_id

        return {
            **_base(
                "PASS__VERIFIED_GROUNDING_EXPOSED_AS_UNTRUSTED_POLICY_FRONTIER",
                passed=True,
            ),
            "grounding_verified": True,
            "grounding_model_dependency_count": result.get("model_dependency_count"),
            "candidate_policy_count": len(policy_conditions),
            "discarded_weak_candidate_ids": discarded_weak_candidate_ids,
            "semantic_goal_tokens": sorted(semantic_tokens),
            "raw_goal_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "policy_identity_scope": "EXACT_RAW_GOAL_SHA256",
            "policy_conditions": policy_conditions,
            "capability_by_policy": capability_by_policy,
            "grounding": deepcopy(dict(result)),
            "robustness_semantics": (
                "TRUE_MEANS_EACH_GOAL_SCOPED_CANDIDATE_MUST_BE_PROVED_ADEQUATE_OVER_"
                "THE_ENTIRE_CURRENT_SOUND_SEMANTIC_OVERAPPROXIMATION_FOR_THE_EXACT_RAW_GOAL_"
                "IDENTITY_BEFORE_SELECTION"
            ),
            "ambiguity_preserved": len(policy_conditions) > 1,
            "candidate_only": True,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": type(exc).__name__ + ":" + str(exc),
        }

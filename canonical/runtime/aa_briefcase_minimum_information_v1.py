from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_MINIMUM_INFORMATION_V1"
TARGET_AUTHORITY_BLOB_SHA = "8f24ca30e6cceb8a58f619da1623037c0a4bda0b"
TERMINAL_PREDICATE = (
    "BRAIN_PROFESSIONAL_WORK_CAPABILITY_GE_CAPABILITY_EVIDENCED_BY_"
    "FROZEN_OPUS55_AA_BRIEFCASE_1822"
)
CAPABILITY_COMPONENTS = frozenset({
    "TASK_SPECIFIC_REQUIREMENT_AND_RUBRIC_SATISFACTION",
    "ANALYTICAL_QUALITY",
    "PRESENTATION_QUALITY",
    "RELIABILITY_ACROSS_THE_RELEVANT_PROFESSIONAL_WORK_SCOPE",
})
CREDIT_RELATIONS = frozenset({
    "EXACT_EQUIVALENCE",
    "CONSERVATIVE_DOMINANCE",
    "OWNER_ACCEPTED_RELATION",
})


class MinimumInformationError(ValueError):
    pass


def _valid_sha256(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _admit(raw: Mapping[str, Any]) -> tuple[str, frozenset[str], float, str]:
    cid = str(raw.get("id") or "")
    if not cid:
        raise MinimumInformationError("CANDIDATE_ID_MISSING")

    required_true = (
        "verified",
        "causal",
        "generalization_bound",
        "subject_bound",
        "brain_owned_donor_free",
        "reference_evidence_bound",
        "terminal_predicate_entailment_bound",
        "relation_scope_complete",
    )
    if not all(raw.get(key) is True for key in required_true):
        raise MinimumInformationError(f"CANDIDATE_NOT_ADMISSIBLE:{cid}")

    if raw.get("target_authority_blob_sha") != TARGET_AUTHORITY_BLOB_SHA:
        raise MinimumInformationError(f"TARGET_AUTHORITY_MISMATCH:{cid}")
    if raw.get("terminal_predicate") != TERMINAL_PREDICATE:
        raise MinimumInformationError(f"TERMINAL_PREDICATE_MISMATCH:{cid}")

    relation = str(raw.get("typed_relation") or "")
    if relation not in CREDIT_RELATIONS:
        raise MinimumInformationError(f"NONCREDIT_RELATION:{cid}")

    subject_sha256 = str(raw.get("subject_sha256") or "")
    if not _valid_sha256(subject_sha256):
        raise MinimumInformationError(f"SUBJECT_SHA256_INVALID:{cid}")

    covered_raw = raw.get("covers_components")
    if not isinstance(covered_raw, list):
        raise MinimumInformationError(f"COMPONENT_COVERAGE_INVALID:{cid}")
    covered = frozenset(str(x) for x in covered_raw)
    if not covered or not covered <= CAPABILITY_COMPONENTS:
        raise MinimumInformationError(f"COMPONENT_COVERAGE_OUT_OF_DOMAIN:{cid}")

    cost = float(raw.get("action_cost", 1.0))
    if cost < 0:
        raise MinimumInformationError(f"NEGATIVE_ACTION_COST:{cid}")

    return cid, covered, cost, subject_sha256


def minimum_proof_carrying_information_set(
    candidates: Sequence[Mapping[str, Any]],
    *,
    required_components: Iterable[str] = CAPABILITY_COMPONENTS,
) -> dict[str, Any]:
    required = frozenset(str(x) for x in required_components)
    if not required or not required <= CAPABILITY_COMPONENTS:
        raise MinimumInformationError("REQUIRED_COMPONENT_SET_INVALID")

    admissible: list[tuple[str, frozenset[str], float, str]] = []
    rejected: list[dict[str, str]] = []
    for raw in candidates:
        try:
            admissible.append(_admit(raw))
        except MinimumInformationError as exc:
            rejected.append({"id": str(raw.get("id") or ""), "reason": str(exc)})

    best = None
    for count in range(1, len(admissible) + 1):
        for combo in combinations(admissible, count):
            subjects = {item[3] for item in combo}
            if len(subjects) != 1:
                continue
            covered = frozenset().union(*(item[1] for item in combo))
            if not required <= covered:
                continue
            ids = tuple(sorted(item[0] for item in combo))
            total_cost = sum(item[2] for item in combo)
            rank = (total_cost, len(combo), ids)
            if best is None or rank < best[0]:
                best = (rank, combo)

    if best is None:
        by_subject: dict[str, frozenset[str]] = {}
        for _, covered, _, subject in admissible:
            by_subject[subject] = by_subject.get(subject, frozenset()) | covered
        best_covered = max(by_subject.values(), key=len, default=frozenset())
        return {
            "schema": SCHEMA,
            "status": "OPEN__NO_COMPLETE_SAME_SUBJECT_PROOF_INFORMATION_SET",
            "capability_relation_proved": False,
            "selected_certificate_ids": [],
            "missing_components": sorted(required - best_covered),
            "rejected_candidates": rejected,
            "literal_aa_briefcase_elo_ge_1822_proved": False,
            "terminal_authority": False,
        }

    rank, combo = best
    return {
        "schema": SCHEMA,
        "status": "PASS__MINIMUM_PROOF_CARRYING_INFORMATION_SET_FOUND",
        "capability_relation_proved": True,
        "selected_certificate_ids": sorted(item[0] for item in combo),
        "subject_sha256": combo[0][3],
        "covered_components": sorted(required),
        "total_action_cost": rank[0],
        "literal_aa_briefcase_elo_ge_1822_proved": False,
        "hard_nonclaim": (
            "CAPABILITY_RELATION_DOES_NOT_CREATE_AN_OFFICIAL_AA_BRIEFCASE_SCORE_"
            "WITHOUT_A_SEPARATE_EXPLICIT_SCORE_ENTAILMENT"
        ),
        "terminal_authority": False,
    }


def current_authority_probe() -> dict[str, Any]:
    candidates = [
        {
            "id": "PROFESSIONAL_PROPERTY_TRUTH_24_OF_24",
            "verified": True,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "brain_owned_donor_free": True,
            "reference_evidence_bound": False,
            "terminal_predicate_entailment_bound": False,
            "relation_scope_complete": False,
            "target_authority_blob_sha": TARGET_AUTHORITY_BLOB_SHA,
            "terminal_predicate": TERMINAL_PREDICATE,
            "typed_relation": "SCHEDULING_HEURISTIC_ONLY",
            "subject_sha256": "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e",
            "covers_components": sorted(CAPABILITY_COMPONENTS),
            "action_cost": 0,
        },
        {
            "id": "P2_STRONG_VISIBLE_QUALITY_SUBREGION_TOP_LAW",
            "verified": True,
            "causal": True,
            "generalization_bound": False,
            "subject_bound": False,
            "brain_owned_donor_free": True,
            "reference_evidence_bound": False,
            "terminal_predicate_entailment_bound": False,
            "relation_scope_complete": False,
            "target_authority_blob_sha": TARGET_AUTHORITY_BLOB_SHA,
            "terminal_predicate": TERMINAL_PREDICATE,
            "typed_relation": "SCHEDULING_HEURISTIC_ONLY",
            "subject_sha256": "0" * 64,
            "covers_components": [
                "TASK_SPECIFIC_REQUIREMENT_AND_RUBRIC_SATISFACTION",
                "ANALYTICAL_QUALITY",
                "PRESENTATION_QUALITY",
            ],
            "action_cost": 0,
        },
    ]
    out = minimum_proof_carrying_information_set(candidates)
    out["probe_kind"] = "CURRENT_HIGH_AUTHORITY_REUSE_PROBE"
    out["next_action"] = (
        "PRODUCE_OR_DISCOVER_THE_CHEAPEST_ADMISSIBLE_SAME_SUBJECT_CERTIFICATE_"
        "WITH_A_CREDIT_BEARING_TYPED_ENTAILMENT_TO_THE_CANONICAL_TERMINAL_PREDICATE"
    )
    return out

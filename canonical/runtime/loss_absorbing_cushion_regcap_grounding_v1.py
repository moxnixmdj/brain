"""End-to-end bounded grounding for the exact surface "loss-absorbing cushion".

Pipeline:
    exact source span
      -> source-aligned participial disposition proof
      -> DISPOSITION::LOSS_ABSORPTION
      -> source-backed regulatory-capital candidate discovery

The result is intentionally not a concept mapping. It preserves the source as
partially understood, keeps an opaque remainder, and exposes the non-unique
candidate set for further evidence acquisition.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.bounded_participial_disposition_v1 import SEMANTIC_ATOM
from canonical.runtime.source_aligned_participial_disposition_proof_v1 import (
    KIND as PARTICIPIAL_KIND,
    verify_proof as verify_participial_proof,
)
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import regcap_property_candidate_discovery_v1 as discovery

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V1"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "proved_source_constraints": [],
        "candidate_concept_ids": [],
        "mapped_concept_id": None,
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "source_constraint_proved": False,
        "candidate_generation_authority": False,
        "semantic_identity_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        source_id = str(source_id or "").strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            return _base("FAIL_CLOSED", reason="SOURCE_SPAN_INVALID")

        source_proof = verify_participial_proof(
            source_text,
            source_id=source_id,
            claims=[{
                "claim_id": "loss-absorbing-disposition",
                "kind": PARTICIPIAL_KIND,
                "start": start,
                "end": end,
            }],
        )
        if source_proof.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_PROOF_FAIL_CLOSED",
                source_proof=source_proof,
            )

        constraints = [
            dict(row)
            for row in source_proof.get("proved_constraints", [])
            if isinstance(row, Mapping)
        ]
        expected = {"op": "ATOM", "id": SEMANTIC_ATOM}
        if expected not in constraints:
            return _base(
                "OPEN__SOURCE_SEMANTICS_UNRESOLVED",
                raw_span=source_text[start:end],
                source_id=source_id,
                source_span=[start, end],
                source_proof=source_proof,
                reason="LOSS_ABSORPTION_DISPOSITION_NOT_PROVED",
            )

        candidate_result = discovery.discover(
            {
                "schema": discovery.REQUEST_SCHEMA,
                "scope_id": regcap.SCOPE_ID,
                "property_id": SEMANTIC_ATOM,
            },
            repo_root=repo_root,
        )
        if candidate_result.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="CANDIDATE_DISCOVERY_FAIL_CLOSED",
                raw_span=source_text[start:end],
                source_id=source_id,
                source_span=[start, end],
                source_proof=source_proof,
                candidate_discovery=candidate_result,
                proved_source_constraints=constraints,
                source_constraint_proved=True,
            )

        candidate_ids = list(
            candidate_result.get("candidate_concept_ids") or []
        )
        if not candidate_ids:
            return _base(
                "OPEN__PROVED_SOURCE_PROPERTY_WITHOUT_VERIFIED_REGCAP_CANDIDATES",
                raw_span=source_text[start:end],
                source_id=source_id,
                source_span=[start, end],
                source_proof=source_proof,
                candidate_discovery=candidate_result,
                proved_source_constraints=constraints,
                source_constraint_proved=True,
                candidate_generation_authority=bool(
                    candidate_result.get("candidate_generation_authority")
                ),
                no_candidate_means_nonexistence=False,
            )

        non_unique = len(candidate_ids) > 1
        targets = {
            row["concept_id"]: list(row.get("positive_evidence_targets") or [])
            for row in candidate_result.get("candidates") or []
            if isinstance(row, Mapping) and row.get("concept_id")
        }

        return _base(
            (
                "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES"
                if non_unique
                else "OPEN__COMPOSED_SOURCE_MEANING_WITH_SINGLE_NONIDENTITY_CANDIDATE"
            ),
            passed=True,
            raw_span=source_text[start:end],
            source_id=source_id,
            source_span=[start, end],
            source_proof=source_proof,
            proved_source_constraints=constraints,
            source_constraint_proved=True,
            composed_semantics=expected,
            candidate_discovery=candidate_result,
            candidate_concept_ids=candidate_ids,
            candidate_generation_authority=bool(
                candidate_result.get("candidate_generation_authority")
            ),
            non_unique_property_witness=non_unique,
            mapped_concept_id=None,
            fully_semantically_bound=False,
            opaque_remainder_required=True,
            semantic_identity_authority=False,
            semantic_truth_authority=False,
            next_positive_evidence_targets_by_candidate=targets,
            relation_needed_for_mapping=(
                "AN_INDEPENDENT_SCOPED_CONCEPT_RELATION_PROOF__"
                "NECESSARY_PROPERTY_MATCHING_IS_NOT_SUFFICIENT"
            ),
            boundary=(
                "EXACT_BOUNDED_SURFACE_TO_COMPOSED_DISPOSITION_AND_CANDIDATES_ONLY__"
                "NO_CCOB_CCYB_TLAC_IDENTITY__OPAQUE_REMAINDER_PRESERVED__"
                "NO_OPEN_WORLD_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )

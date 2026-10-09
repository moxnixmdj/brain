"""Loss-absorbing cushion regulatory-capital grounding V3.

V3 preserves V2 exactly and adds bounded same-sentence contextual signature
narrowing.  Context can select one concept relative to the existing bound rival
set, but that relative selection never becomes global semantic identity.

If contextual compilation or matrix authentication fails, V3 preserves the
already-valid V2 result and records the failed optional refinement.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v2 as v2
from canonical.runtime import regcap_context_signature_v1 as context

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V3"


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    projection_verifier=context.matrix.verify_projection_pack,
) -> dict[str, Any]:
    base = v2.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
    )
    out = dict(base)
    out["schema"] = SCHEMA

    if base.get("status") == "FAIL_CLOSED":
        return out

    if (
        base.get("semantic_identity_authority") is True
        and base.get("mapped_concept_id")
    ):
        out.update({
            "context_signature_attempted": False,
            "context_signature_reason": "STRONGER_V2_IDENTITY_ALREADY_PROVED",
        })
        return out

    candidates = list(base.get("candidate_concept_ids") or [])
    if not candidates:
        out.update({
            "context_signature_attempted": False,
            "context_signature_reason": "NO_BOUND_RIVAL_CANDIDATES",
        })
        return out

    relative = context.resolve_relative(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        candidate_concept_ids=candidates,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    out["context_signature_attempted"] = True
    out["context_signature_result"] = relative

    if relative.get("status") == "FAIL_CLOSED":
        out.update({
            "context_refinement_preserved_base_after_failure": True,
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
        })
        return out

    if relative.get("relative_selection_authority") is not True:
        out.update({
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
        })
        return out

    selected = relative.get("relative_selected_concept_id")
    if selected:
        out.update({
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_BOUND_RIVALS",
            "pass": True,
            "relative_selection_authority": True,
            "relative_selected_concept_id": selected,
            "bound_rival_surviving_concept_ids": list(
                relative.get("surviving_candidate_ids") or []
            ),
            "relative_selection_observations": list(
                relative.get("observations") or []
            ),
            "mapped_concept_id": None,
            "fully_semantically_bound": False,
            "opaque_remainder_required": True,
            "semantic_identity_authority": False,
            "global_phrase_identity_authority": False,
            "open_world_identity_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "V3_CONTEXT_CAN_SELECT_ONE_CONCEPT_ONLY_RELATIVE_TO_THE_EXISTING_"
                "BOUND_RIVAL_SET__GLOBAL_IDENTITY_REMAINS_UNPROVED_WITHOUT_AN_"
                "INDEPENDENT_CANDIDATE_UNIVERSE_COMPLETENESS_CERTIFICATE"
            ),
        })
        return out

    out.update({
        "relative_selection_authority": True,
        "relative_selected_concept_id": None,
        "bound_rival_surviving_concept_ids": list(
            relative.get("surviving_candidate_ids") or []
        ),
    })
    return out

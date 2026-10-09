"""Loss-absorbing cushion regulatory-capital grounding V2.

V2 adds one exact source-bound identity path:
- exact surface: "loss-absorbing cushion"
- exact authenticated source: NY Fed Dudley speech, 2010-10-10
- result: REGCAP::CCOB

Every other source delegates unchanged to V1 and therefore remains candidate-only.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v1 as v1
from canonical.runtime import nyfed_loss_cushion_ccob_source_identity_v1 as source_identity
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V2"


def _upgrade(v1_result: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    out = dict(v1_result)
    out.update({
        "schema": SCHEMA,
        "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
        "pass": True,
        "candidate_concept_ids": [regcap.CCOB],
        "mapped_concept_id": regcap.CCOB,
        "fully_semantically_bound": True,
        "opaque_remainder_required": False,
        "source_context_identity_authority": True,
        "semantic_identity_authority": True,
        "semantic_truth_authority": True,
        "global_phrase_identity_authority": False,
        "source_identity_proof": identity,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "EXACT_AUTHENTICATED_NYFED_SOURCE_CONTEXT_ONLY__"
            "NO_GLOBAL_LOSS_ABSORBING_CUSHION_SYNONYMY__"
            "NO_OPEN_WORLD_ONTOLOGY_POLICY_OR_TERMINAL_AUTHORITY"
        ),
    })
    return out


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
) -> dict[str, Any]:
    base = v1.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
    )
    if base.get("status") == "FAIL_CLOSED":
        return {**base, "schema": SCHEMA}

    raw_span = source_text[start:end] if isinstance(source_text, str) else ""
    if (
        str(source_id or "").strip() != source_identity.SOURCE_ID
        or raw_span.casefold() != source_identity.EXACT_SURFACE
    ):
        return {
            **base,
            "schema": SCHEMA,
            "source_specific_identity_attempted": False,
        }

    identity = source_identity.verify(repo_root=repo_root)
    if identity.get("pass") is not True:
        return {
            **base,
            "schema": SCHEMA,
            "source_specific_identity_attempted": True,
            "source_identity_proof": identity,
            "source_specific_identity_closed": False,
        }
    return _upgrade(dict(base), dict(identity))

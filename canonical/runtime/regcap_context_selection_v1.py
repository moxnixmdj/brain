"""Producer for explicit three-rival regulatory-capital context selection V1."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime import regcap_context_signature_v1 as signature
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime.regcap_context_selection_verify_v1 import (
    CASE_SCHEMA,
    RESULT_SCHEMA,
    PHRASE,
)

SCHEMA = RESULT_SCHEMA
CANDIDATES = (regcap.CCOB, regcap.CCYB, regcap.TLAC)


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "selected_concept_id": None,
        "candidate_ids": list(CANDIDATES),
        "candidate_scope_complete_for_task": True,
        "relative_selection_authority": False,
        "semantic_identity_authority": False,
        "global_phrase_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        **extra,
    }


def compute(
    case: Mapping[str, Any],
    *,
    repo_root: Any = None,
    projection_verifier=signature.matrix.verify_projection_pack,
) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != CASE_SCHEMA:
        return _base("FAIL_CLOSED", reason="CASE_SCHEMA_INVALID")
    if set(case) != {"schema", "source_id", "source_text"}:
        return _base("FAIL_CLOSED", reason="CASE_FIELD_SET_INVALID")
    source_id = str(case.get("source_id") or "").strip()
    source_text = case.get("source_text")
    if not source_id or not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", reason="SOURCE_ID_OR_TEXT_INVALID")

    folded = source_text.casefold()
    needle = PHRASE.casefold()
    starts = []
    cursor = 0
    while True:
        at = folded.find(needle, cursor)
        if at < 0:
            break
        starts.append(at)
        cursor = at + 1
    if len(starts) != 1:
        return _base(
            "OPEN__EXACTLY_ONE_DESCRIPTOR_OCCURRENCE_REQUIRED",
            source_id=source_id,
            source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
            occurrence_count=len(starts),
        )

    start = starts[0]
    end = start + len(PHRASE)
    resolved = signature.resolve_relative(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        candidate_concept_ids=list(CANDIDATES),
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if resolved.get("status") == "FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="CONTEXT_SIGNATURE_RESOLUTION_FAILED",
            source_id=source_id,
            source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
            source_span=[start, end],
            resolution_result=resolved,
        )
    selected = resolved.get("relative_selected_concept_id")
    if (
        resolved.get("relative_selection_authority") is not True
        or not isinstance(selected, str)
        or not selected
    ):
        return _base(
            "OPEN__BOUND_REGCAP_CONTEXT_SELECTION_UNRESOLVED",
            source_id=source_id,
            source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
            source_span=[start, end],
            surviving_candidate_ids=list(
                resolved.get("surviving_candidate_ids") or CANDIDATES
            ),
            resolution_result=resolved,
        )

    return _base(
        "PASS__BOUNDED_REGCAP_CONTEXT_SELECTION_COMPUTED",
        passed=True,
        selected_concept_id=selected,
        source_id=source_id,
        source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        source_span=[start, end],
        relative_selection_authority=True,
        selection_scope="EXACT_TASK_UNIVERSE::CCOB_CCYB_TLAC",
        resolution_result=resolved,
        semantic_identity_authority=False,
        global_phrase_identity_authority=False,
        open_world_candidate_set_complete=False,
        boundary=(
            "SELECTION_IS_ONLY_RELATIVE_TO_THE_EXPLICIT_THREE_RIVAL_TASK_UNIVERSE__"
            "NO_GLOBAL_PHRASE_IDENTITY_OR_OPEN_WORLD_CANDIDATE_COMPLETENESS"
        ),
    )

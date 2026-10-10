"""No-descriptor CCoB/MREL and CCyB/MREL pair resolver V1.

This module reuses existing verified context compilers and the existing
source-backed pair authority. It adds no new language semantics.

Supported exact two-concept task scopes:
- {REGCAP::CCOB, REGCAP::MREL}
- {REGCAP::CCYB, REGCAP::MREL}

CCoB/CCyB evidence comes only from regcap_contextual_observation_compiler_v1.
MREL evidence comes only from tlac_mrel_identity_discriminator_v1.
Mixed positive markers fail closed. Missing markers remain unresolved.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import regcap_contextual_observation_compiler_v1 as context
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac_mrel

SCHEMA = "PROJECT_BRAIN_REGCAP_MREL_NO_DESCRIPTOR_PAIR_V1"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "relative_selection_authority": False,
        "candidate_universe_complete": False,
        "global_semantic_identity_authority": False,
        "open_world_ontology_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _pair_id(value: Any) -> str:
    pid = str(value or "").strip().upper()
    if pid not in pair.PAIR_IDS:
        raise ValueError("PAIR_ID_INVALID")
    return pid


def _sentence_spans(text: str):
    start = 0
    n = len(text)
    for i, ch in enumerate(text):
        boundary = ch in "!?";
        if ch == ".":
            decimal = (
                i > 0 and i + 1 < n
                and text[i - 1].isdigit()
                and text[i + 1].isdigit()
            )
            boundary = not decimal
        if not boundary:
            continue
        raw = text[start:i + 1]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right
        start = i + 1
    if start < n:
        raw = text[start:]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right


def compile_context(
    source_text: str,
    *,
    source_id: str,
    pair_id: str,
) -> dict[str, Any]:
    try:
        pid = _pair_id(pair_id)
        if not isinstance(source_text, str) or not source_text.strip():
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        source_id = str(source_id or "").strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")

        anchor_candidate = pair.PAIR_DOMAIN[pid][0]

        anchor_rows = []
        for s0, s1 in _sentence_spans(source_text):
            row = context.compile_span(source_text, start=s0, end=s1)
            if row.get("status") == "FAIL_CLOSED":
                return _base(
                    "FAIL_CLOSED",
                    reason="NO_DESCRIPTOR_CONTEXT_COMPILER_FAIL_CLOSED",
                    pair_id=pid,
                    context_result=row,
                )
            if row.get("pass") is True:
                anchor_rows.append(row)

        anchor_match = False
        for anchor in anchor_rows:
            oid = str(anchor.get("observation_id") or "")
            outcome = str(anchor.get("outcome") or "")
            if pid == pair.CCOB_MREL:
                anchor_match = anchor_match or (
                    oid == "STRUCTURAL_SIGNATURE_CLASS"
                    and outcome
                    == "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM"
                )
            else:
                anchor_match = anchor_match or (
                    oid == "FUNCTIONAL_SIGNATURE_CLASS"
                    and outcome
                    == "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
                ) or (
                    oid == "STRUCTURAL_SIGNATURE_CLASS"
                    and outcome == "EXTENDS_CCOB_AND_MET_WITH_CET1"
                )

        mrel_context = tlac_mrel.compile_context(
            source_text,
            source_id=source_id,
        )
        mrel_match = bool(
            mrel_context.get("pass") is True
            and mrel_context.get("selected_candidate_hint") == mrel.MREL
        )

        if anchor_match and mrel_match:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_NO_DESCRIPTOR_PAIR_CONTEXT_SIGNATURES",
                pair_id=pid,
                anchor_contexts=anchor_rows,
                mrel_context=mrel_context,
            )

        if not anchor_match and not mrel_match:
            return _base(
                "OPEN__NO_BOUND_NO_DESCRIPTOR_PAIR_CONTEXT_SIGNATURE",
                pair_id=pid,
                source_id=source_id,
                anchor_contexts=anchor_rows,
                mrel_context=mrel_context,
            )

        selected = mrel.MREL if mrel_match else anchor_candidate
        return _base(
            "PASS__BOUND_NO_DESCRIPTOR_REGCAP_MREL_PAIR_CONTEXT",
            passed=True,
            semantic_truth_authority=True,
            pair_id=pid,
            source_id=source_id,
            selected_candidate_hint=selected,
            observed_outcome=pair.PAIR_OUTCOMES[pid][selected],
            observation_id=pair.OBSERVATION_ID,
            anchor_contexts=anchor_rows,
            mrel_context=mrel_context,
            boundary=(
                "REUSES_ONLY_EXISTING_VERIFIED_NO_DESCRIPTOR_REGCAP_CONTEXT_AND_"
                "TLAC_MREL_GOVERNING_MARKER_COMPILERS__NO_NEW_LANGUAGE_SEMANTICS"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def resolve_relative(
    source_text: str,
    *,
    source_id: str,
    pair_id: str,
    candidate_concept_ids: Sequence[str],
    repo_root: Any = None,
    projection_verifier=pair.verify_projection_pack,
) -> dict[str, Any]:
    try:
        pid = _pair_id(pair_id)
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))

    expected = sorted(pair.PAIR_DOMAIN[pid])
    if (
        not isinstance(candidate_concept_ids, Sequence)
        or isinstance(candidate_concept_ids, (str, bytes))
    ):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_REQUIRED")
    candidates = sorted(str(x) for x in candidate_concept_ids)
    if candidates != expected:
        return _base(
            "FAIL_CLOSED",
            reason="CANDIDATE_SET_MUST_EQUAL_BOUND_PAIR",
            pair_id=pid,
            supplied_candidate_ids=candidates,
            required_candidate_ids=expected,
        )

    compiled = compile_context(
        source_text,
        source_id=source_id,
        pair_id=pid,
    )
    if compiled.get("pass") is not True:
        return compiled

    authority = pair.verify_authority(
        pid,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if authority.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="PAIR_DISCRIMINATOR_AUTHORITY_FAILED",
            pair_id=pid,
            authority_result=authority,
        )

    selected = str(compiled.get("selected_candidate_hint") or "")
    outcome = str(compiled.get("observed_outcome") or "")
    if authority.get("outcomes", {}).get(selected) != outcome:
        return _base(
            "FAIL_CLOSED",
            reason="CONTEXT_OUTCOME_NOT_BOUND_TO_AUTHENTICATED_PAIR_MATRIX",
            pair_id=pid,
        )

    return _base(
        "PASS__UNIQUE_CONCEPT_IN_BOUND_REGCAP_MREL_NO_DESCRIPTOR_PAIR_SCOPE",
        passed=True,
        semantic_truth_authority=True,
        relative_selection_authority=True,
        pair_id=pid,
        candidate_universe_complete=True,
        candidate_universe_complete_only_for_scope_id=pair.PAIR_SCOPE[pid],
        selected_concept_id=selected,
        surviving_candidate_ids=[selected],
        declared_candidate_ids=list(pair.PAIR_DOMAIN[pid]),
        observation_id=pair.OBSERVATION_ID,
        observed_outcome=outcome,
        authority_sha256=authority.get("authority_sha256"),
        global_semantic_identity_authority=False,
        open_world_ontology_complete=False,
        boundary=(
            "UNIQUE_ONLY_INSIDE_EXISTING_AUTHENTICATED_TWO_CONCEPT_TASK_SCOPE__"
            "NO_DESCRIPTOR_REQUIRED__NO_GLOBAL_OR_OPEN_WORLD_CONCEPT_IDENTITY"
        ),
    )

"""Bounded contextual signatures for the exact phrase "loss-absorbing cushion".

The compiler recognizes only six tightly bounded source patterns in the sentence
containing the exact descriptor.  It emits observations that are already
defined by regcap_contrastive_discriminator_matrix_v1.

A matching observation can select a concept only RELATIVE to a supplied subset
of the three matrix rivals.  It never proves that those rivals exhaust the open
world and never grants global concept identity.
"""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix
from canonical.runtime.source_assertion_ownership_guard_v1 import check_direct_assertion

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_SIGNATURE_V1"
EXACT_SURFACE = "loss-absorbing cushion"
MAX_SENTENCE_CHARS = 800

_CCOB_FUNC = re.compile(
    r"\b(?:can\s+be\s+)?drawn\s+down\s+as\s+losses\s+are\s+incurred\b",
    re.I,
)
_CCYB_FUNC = re.compile(
    r"\breleased\s+when\s+system[- ]wide\s+risk\s+crystalli[sz]es\s+or\s+dissipates\b",
    re.I,
)
_TLAC_FUNC_RECAP = re.compile(
    r"\bloss-absorbing\s+and\s+recapitali[sz]ation\s+capacity\b",
    re.I,
)
_TLAC_FUNC_RESOLUTION = re.compile(r"\bavailable\s+in\s+resolution\b", re.I)
_TLAC_FUNC_GSIB = re.compile(
    r"\b(?:G-SIBs?|global\s+systemically\s+important\s+banks?)\b",
    re.I,
)

_CCOB_STRUCT_PERCENT = re.compile(r"(?<!\w)2\.5(?:%|\s+percent\b)", re.I)
_CCOB_STRUCT_CET1 = re.compile(r"\b(?:CET1|Common\s+Equity\s+Tier\s+1)\b", re.I)
_CCOB_STRUCT_ABOVE = re.compile(
    r"\babove\s+(?:the\s+)?regulatory\s+minimum(?:\s+capital\s+requirement)?s?\b",
    re.I,
)
_CCYB_STRUCT_EXTENDS = re.compile(
    r"\bextend(?:s|ed|ing)?\s+(?:the\s+)?size\s+of\s+the\s+capital\s+conservation\s+buffer\b",
    re.I,
)
_CCYB_STRUCT_CET1 = _CCOB_STRUCT_CET1
_TLAC_STRUCT_MIN = re.compile(r"\bminimum\s+external\s+TLAC\b", re.I)
_TLAC_STRUCT_ALONGSIDE = re.compile(
    r"\balongside\s+minimum\s+regulatory\s+capital\s+requirements\b",
    re.I,
)

_SIGNATURES = {
    ("FUNCTIONAL_SIGNATURE_CLASS", "DRAWDOWN_AS_LOSSES_ARE_INCURRED"): "REGCAP::CCOB",
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
    ): "REGCAP::CCYB",
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
    ): "REGCAP::TLAC",
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
    ): "REGCAP::CCOB",
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "EXTENDS_CCOB_AND_MET_WITH_CET1",
    ): "REGCAP::CCYB",
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
    ): "REGCAP::TLAC",
}


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "relative_selection_authority": False,
        "semantic_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sentence_spans(text: str):
    start = 0
    n = len(text)
    for i, ch in enumerate(text):
        boundary = ch in "!?";
        if ch == ".":
            decimal_point = (
                i > 0
                and i + 1 < n
                and text[i - 1].isdigit()
                and text[i + 1].isdigit()
            )
            boundary = not decimal_point
        if not boundary:
            continue
        raw = text[start:i + 1]
        left_trim = len(raw) - len(raw.lstrip())
        right_trim = len(raw.rstrip())
        if right_trim > left_trim:
            yield start + left_trim, start + right_trim, raw[left_trim:right_trim]
        start = i + 1
    if start < n:
        raw = text[start:]
        left_trim = len(raw) - len(raw.lstrip())
        right_trim = len(raw.rstrip())
        if right_trim > left_trim:
            yield start + left_trim, start + right_trim, raw[left_trim:right_trim]


def _containing_sentence(text: str, start: int, end: int) -> tuple[int, int, str] | None:
    for left, right, sentence in _sentence_spans(text):
        if left <= start and end <= right:
            return left, right, sentence
    return None


def compile_context(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        source_id = str(source_id or "").strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            return _base("FAIL_CLOSED", reason="SOURCE_SPAN_INVALID")
        if source_text[start:end].casefold() != EXACT_SURFACE:
            return _base(
                "OPEN__EXACT_DESCRIPTOR_NOT_PRESENT",
                raw_span=source_text[start:end],
            )

        sent = _containing_sentence(source_text, start, end)
        if sent is None:
            return _base("FAIL_CLOSED", reason="CONTAINING_SENTENCE_NOT_FOUND")
        s0, s1, sentence = sent
        if len(sentence) > MAX_SENTENCE_CHARS:
            return _base(
                "OPEN__CONTEXT_SENTENCE_TOO_LARGE",
                sentence_span=[s0, s1],
            )

        ownership = check_direct_assertion(
            source_text,
            start=s0,
            end=s1,
            require_selected_span_is_complete_sentence=True,
        )
        if ownership.get("pass") is not True:
            if ownership.get("status") == "FAIL_CLOSED":
                return _base(
                    "FAIL_CLOSED",
                    reason="ASSERTION_OWNERSHIP_GUARD_FAIL_CLOSED",
                    assertion_ownership=ownership,
                )
            return _base(
                "OPEN__ASSERTION_OWNERSHIP_NOT_PROVED",
                assertion_ownership=ownership,
                source_id=source_id,
                source_text_sha256=_sha(source_text),
                descriptor_span=[start, end],
                sentence_span=[s0, s1],
                sentence=sentence,
            )

        observed: list[dict[str, Any]] = []

        if _CCOB_FUNC.search(sentence):
            observed.append({
                "observation_id": "FUNCTIONAL_SIGNATURE_CLASS",
                "outcome": "DRAWDOWN_AS_LOSSES_ARE_INCURRED",
                "relative_candidate_id": "REGCAP::CCOB",
            })
        if _CCYB_FUNC.search(sentence):
            observed.append({
                "observation_id": "FUNCTIONAL_SIGNATURE_CLASS",
                "outcome": "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
                "relative_candidate_id": "REGCAP::CCYB",
            })
        if (
            _TLAC_FUNC_RECAP.search(sentence)
            and _TLAC_FUNC_RESOLUTION.search(sentence)
            and _TLAC_FUNC_GSIB.search(sentence)
        ):
            observed.append({
                "observation_id": "FUNCTIONAL_SIGNATURE_CLASS",
                "outcome": "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
                "relative_candidate_id": "REGCAP::TLAC",
            })

        if (
            _CCOB_STRUCT_PERCENT.search(sentence)
            and _CCOB_STRUCT_CET1.search(sentence)
            and _CCOB_STRUCT_ABOVE.search(sentence)
        ):
            observed.append({
                "observation_id": "STRUCTURAL_SIGNATURE_CLASS",
                "outcome": "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
                "relative_candidate_id": "REGCAP::CCOB",
            })
        if (
            _CCYB_STRUCT_EXTENDS.search(sentence)
            and _CCYB_STRUCT_CET1.search(sentence)
        ):
            observed.append({
                "observation_id": "STRUCTURAL_SIGNATURE_CLASS",
                "outcome": "EXTENDS_CCOB_AND_MET_WITH_CET1",
                "relative_candidate_id": "REGCAP::CCYB",
            })
        if _TLAC_STRUCT_MIN.search(sentence) and _TLAC_STRUCT_ALONGSIDE.search(sentence):
            observed.append({
                "observation_id": "STRUCTURAL_SIGNATURE_CLASS",
                "outcome": "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
                "relative_candidate_id": "REGCAP::TLAC",
            })

        by_observation: dict[str, set[str]] = {}
        for row in observed:
            by_observation.setdefault(row["observation_id"], set()).add(row["outcome"])
        conflicts = {
            oid: sorted(values)
            for oid, values in by_observation.items()
            if len(values) > 1
        }
        if conflicts:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_CONTEXT_SIGNATURES",
                conflicts=conflicts,
                source_id=source_id,
                source_text_sha256=_sha(source_text),
                sentence_span=[s0, s1],
                sentence=sentence,
            )

        candidate_ids = sorted({row["relative_candidate_id"] for row in observed})
        if len(candidate_ids) > 1:
            return _base(
                "FAIL_CLOSED",
                reason="CROSS_OBSERVATION_CONTEXT_SIGNATURE_CONFLICT",
                relative_candidate_ids=candidate_ids,
                observations=observed,
                sentence_span=[s0, s1],
            )

        if not observed:
            return _base(
                "OPEN__NO_BOUND_CONTEXT_SIGNATURE",
                source_id=source_id,
                source_text_sha256=_sha(source_text),
                descriptor_span=[start, end],
                sentence_span=[s0, s1],
                sentence=sentence,
            )

        return _base(
            "PASS__BOUND_CONTEXT_SIGNATURES_COMPILED",
            passed=True,
            semantic_truth_authority=True,
            source_id=source_id,
            source_text_sha256=_sha(source_text),
            descriptor_span=[start, end],
            sentence_span=[s0, s1],
            sentence=sentence,
            observations=observed,
            relative_candidate_hint=candidate_ids[0],
            relative_selection_authority=False,
            boundary=(
                "EXACT_DESCRIPTOR_PLUS_DIRECT_ASSERTION_COMPLETE_SENTENCE_BOUNDED_SIGNATURE_GRAMMAR_ONLY__"
                "OBSERVATIONS_HAVE_SOURCE_ALIGNED_SEMANTIC_AUTHORITY__"
                "CANDIDATE_ID_IS_A_HINT_UNTIL_AUTHENTICATED_MATRIX_REPLAY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def resolve_relative(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    candidate_concept_ids: Sequence[str],
    repo_root: Any = None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    compiled = compile_context(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
    )
    if compiled.get("pass") is not True:
        return compiled

    if (
        not isinstance(candidate_concept_ids, Sequence)
        or isinstance(candidate_concept_ids, (str, bytes))
        or not candidate_concept_ids
    ):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_REQUIRED")
    candidates = [str(x) for x in candidate_concept_ids]
    if len(candidates) != len(set(candidates)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_DUPLICATE")
    if not set(candidates).issubset(set(matrix.DOMAIN)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    verified_matrix = matrix.verify_matrix(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if verified_matrix.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="CONTRASTIVE_MATRIX_AUTHORITY_FAILED",
            matrix_result=verified_matrix,
        )

    by_id = {
        row["observation_id"]: row
        for row in verified_matrix.get("observations", [])
        if isinstance(row, Mapping)
    }
    surviving = set(candidates)
    applied = []
    for obs in compiled["observations"]:
        row = by_id.get(obs["observation_id"])
        if not isinstance(row, Mapping):
            return _base(
                "FAIL_CLOSED",
                reason="COMPILED_OBSERVATION_NOT_IN_AUTHENTICATED_MATRIX",
                observation=obs,
            )
        outcome = obs["outcome"]
        matched = {
            cid for cid in surviving
            if row.get("outcomes", {}).get(cid) == outcome
        }
        if not matched:
            return _base(
                "FAIL_CLOSED",
                reason="CONTEXT_OUTCOME_CONTRADICTS_DECLARED_CANDIDATES",
                observation=obs,
                surviving_before=sorted(surviving),
            )
        surviving = matched
        applied.append({
            "observation_id": obs["observation_id"],
            "outcome": outcome,
            "surviving_candidate_ids": sorted(surviving),
        })

    ids = sorted(surviving)
    if len(ids) == 1:
        return _base(
            "PASS__UNIQUE_CANDIDATE_RELATIVE_TO_DECLARED_BOUND_RIVALS",
            passed=True,
            semantic_truth_authority=True,
            relative_selection_authority=True,
            relative_selected_concept_id=ids[0],
            surviving_candidate_ids=ids,
            declared_candidate_ids=candidates,
            candidate_universe_complete=False,
            semantic_identity_authority=False,
            observations=compiled["observations"],
            applied_observations=applied,
            matrix_sha256=verified_matrix.get("matrix_sha256"),
            open_world_identity_authorized=False,
            boundary=(
                "UNIQUE_ONLY_RELATIVE_TO_DECLARED_BOUND_RIVALS__"
                "NO_GLOBAL_OR_OPEN_WORLD_CONCEPT_IDENTITY__"
                "A_SEPARATE_CANDIDATE_UNIVERSE_COMPLETENESS_PROOF_IS_REQUIRED_FOR_IDENTITY"
            ),
        )

    return _base(
        "OPEN__CONTEXT_SIGNATURES_DO_NOT_UNIQUELY_SEPARATE_DECLARED_RIVALS",
        passed=True,
        semantic_truth_authority=True,
        relative_selection_authority=True,
        surviving_candidate_ids=ids,
        declared_candidate_ids=candidates,
        candidate_universe_complete=False,
        semantic_identity_authority=False,
        observations=compiled["observations"],
        applied_observations=applied,
        matrix_sha256=verified_matrix.get("matrix_sha256"),
    )

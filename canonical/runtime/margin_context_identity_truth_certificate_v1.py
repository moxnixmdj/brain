"""Semantic truth certificate for bounded context-rich margin identity.

Order:
1. exact authenticated multiword term containing the target occurrence;
2. authenticated ARM/index relational context.

Positive-only: a proved selected concept may yield TRUE. A different selected
concept or an unsupported occurrence remains UNKNOWN unless an independent
incompatibility proof exists elsewhere.

No global bare-margin sense, open-world finance completeness, policy adequacy,
execution, acceptance, promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import margin_contextual_term_identity_v1 as term_identity
from canonical.runtime import arm_margin_context_identity_v1 as arm_identity

SCHEMA = "PROJECT_BRAIN_MARGIN_CONTEXT_IDENTITY_TRUTH_CERTIFICATE_V1"
TRUTH_KIND = "MARGIN_CONTEXT_IDENTITY"

KNOWN_CONCEPTS = {
    term_identity.NET_INTEREST_MARGIN,
    term_identity.INITIAL_MARGIN,
    arm_identity.CONCEPT_ID,
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_id": None,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def _unknown(
    *,
    checked_id: str,
    requested_id: str,
    target: str,
    reason: str,
    resolution_attempts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__MARGIN_CONTEXT_IDENTITY_NOT_PROVED",
        "reason": reason,
        "predicate_id": checked_id,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "UNKNOWN",
        "target_concept_id": target,
        "resolution_attempts": [dict(x) for x in resolution_attempts],
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def checked_predicate_id(
    *,
    source_id: str,
    source_text: str,
    start: int,
    end: int,
    target_concept_id: str,
) -> str:
    if (
        not isinstance(source_text, str)
        or not source_text
        or isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    source_id = str(source_id or "").strip()
    target = str(target_concept_id or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if target not in KNOWN_CONCEPTS:
        raise ValueError("TARGET_CONCEPT_UNSUPPORTED")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "source_span_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "target_concept_id": target,
        "certificate_schema": SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "margin-context-identity-sha256:" + sha256(raw).hexdigest()


def _containing_term_span(
    source_text: str,
    *,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    surface = source_text[start:end].casefold()
    if surface in {"net interest margin", "initial margin"}:
        return start, end
    if surface != "margin":
        return None

    candidates = ("net interest margin", "initial margin")
    for term in candidates:
        prefix = term[:-len("margin")]
        term_start = start - len(prefix)
        if term_start < 0:
            continue
        if source_text[term_start:end].casefold() != term:
            continue
        before = source_text[term_start - 1:term_start] if term_start > 0 else ""
        after = source_text[end:end + 1]
        if before and (before.isalnum() or before == "_"):
            continue
        if after and (after.isalnum() or after == "_"):
            continue
        return term_start, end
    return None


def _resolve(
    source_text: str,
    *,
    start: int,
    end: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    attempts: list[dict[str, Any]] = []

    term_span = _containing_term_span(source_text, start=start, end=end)
    if term_span is not None:
        ts, te = term_span
        term = term_identity.resolve_span(source_text, start=ts, end=te)
        attempts.append({"route": "AUTHENTICATED_MULTIWORD_TERM", **dict(term)})
        if term.get("status") == "FAIL_CLOSED":
            return None, attempts, "MULTIWORD_TERM_AUTHORITY_FAIL_CLOSED"
        if term.get("pass") is True:
            return dict(term), attempts, None

    if source_text[start:end].casefold() == "margin":
        arm = arm_identity.resolve_occurrence(source_text, start=start, end=end)
        attempts.append({"route": "AUTHENTICATED_ARM_INDEX_RELATION", **dict(arm)})
        if arm.get("status") == "FAIL_CLOSED":
            return None, attempts, "ARM_MARGIN_AUTHORITY_FAIL_CLOSED"
        if arm.get("pass") is True:
            return dict(arm), attempts, None

    return None, attempts, None


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed = {
        "truth_kind",
        "predicate_id",
        "source_text",
        "source_id",
        "start",
        "end",
        "target_concept_id",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested_id = str(payload.get("predicate_id") or "").strip()
    source_text = payload.get("source_text")
    source_id = str(payload.get("source_id") or "").strip()
    start = payload.get("start")
    end = payload.get("end")
    target = str(payload.get("target_concept_id") or "").strip()
    if not requested_id:
        return _fail("PREDICATE_ID_REQUIRED")

    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            target_concept_id=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    selected, attempts, fatal = _resolve(
        source_text,
        start=start,
        end=end,
    )
    if fatal is not None:
        return _fail(
            fatal,
            resolution_attempts=attempts,
        )
    if selected is None:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            target=target,
            reason="NO_AUTHENTICATED_CONTEXT_IDENTITY_ROUTE_PROVED",
            resolution_attempts=attempts,
        )

    selected_id = str(selected.get("concept_id") or "")
    if selected_id != target:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            target=target,
            reason="DIFFERENT_PROVED_CONTEXT_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION",
            resolution_attempts=attempts,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SOURCE_BOUND_MARGIN_CONTEXT_IDENTITY_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "target_concept_id": target,
        "selected_concept_id": selected_id,
        "selected_resolution": selected,
        "resolution_attempts": attempts,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "semantic_identity_authority": True,
        "global_identity_authority": False,
        "open_world_finance_semantics_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "AUTHENTICATED_OCCURRENCE_LOCAL_MARGIN_CONTEXT_IDENTITY_ONLY__"
            "LONGEST_BOUND_MULTIWORD_TERM_PRECEDES_ARM_RELATIONAL_CONTEXT__"
            "DIFFERENT_PROVED_IDENTITY_REMAINS_UNKNOWN_WITHOUT_DISJOINTNESS__"
            "NO_GLOBAL_BARE_MARGIN_SENSE_OR_OPEN_WORLD_COMPLETENESS"
        ),
    }

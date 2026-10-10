"""Truth certificate for canonical bounded regulatory-capital contextual atoms V2.

V2 reuses the independently verified canonical contextual observation compiler.
It does not maintain a second language parser. Only canonical positive observation
outcomes are projected into the legacy bounded atom API.

Unrecognized, negated, attributed, quoted, hypothetical, weaker, or otherwise
unmodelled language remains UNKNOWN. Context properties never create concept
identity, candidate-universe completeness, policy adequacy, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import regcap_contextual_observation_compiler_v1 as observation

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_ATOM_TRUTH_CERTIFICATE_V2"
TRUTH_KIND = "REGCAP_CONTEXT_ATOM"

CCOB_KIND = "CERTIFIED_REGCAP_CCOB_STRUCTURE_CONTEXT"
CCYB_KIND = "CERTIFIED_REGCAP_CCYB_RELEASE_CONTEXT"
TLAC_KIND = "CERTIFIED_REGCAP_TLAC_RESOLUTION_CONTEXT"

ATOM_CET1 = "COMPOSITION::CET1"
ATOM_ABOVE_MIN = "POSITION::ABOVE_REGULATORY_MINIMUM"
ATOM_2_5 = "AMOUNT::2.5_PERCENT"
ATOM_RELEASE = "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
ATOM_LOSS = "FUNCTION::LOSS_ABSORPTION"
ATOM_RECAP = "FUNCTION::RECAPITALISATION"
ATOM_RESOLUTION = "REGIME::RESOLUTION"
ATOM_GSIB = "SCOPE::G_SIB"

CONTEXT_KINDS = {CCOB_KIND, CCYB_KIND, TLAC_KIND}
KNOWN_ATOMS = {
    ATOM_CET1,
    ATOM_ABOVE_MIN,
    ATOM_2_5,
    ATOM_RELEASE,
    ATOM_LOSS,
    ATOM_RECAP,
    ATOM_RESOLUTION,
    ATOM_GSIB,
}

_CANONICAL_OUTCOMES = {
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
    ): {
        "context_kind": CCOB_KIND,
        "atom_ids": [ATOM_2_5, ATOM_CET1, ATOM_ABOVE_MIN],
    },
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
    ): {
        "context_kind": CCYB_KIND,
        "atom_ids": [ATOM_RELEASE],
    },
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
    ): {
        "context_kind": TLAC_KIND,
        "atom_ids": [ATOM_LOSS, ATOM_RECAP, ATOM_RESOLUTION, ATOM_GSIB],
    },
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


def checked_predicate_id(
    *,
    source_id: str,
    source_text: str,
    start: int,
    end: int,
    context_kind: str,
    target_atom_id: str,
) -> str:
    if (
        not isinstance(source_text, str)
        or not source_text
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    source_id = str(source_id or "").strip()
    context_kind = str(context_kind or "").strip()
    target_atom_id = str(target_atom_id or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if context_kind not in CONTEXT_KINDS:
        raise ValueError("CONTEXT_KIND_INVALID")
    if target_atom_id not in KNOWN_ATOMS:
        raise ValueError("TARGET_ATOM_UNSUPPORTED")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "source_span_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "canonical_observation_checker_schema": observation.SCHEMA,
        "adapter_schema": SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "regcap-context-atom-sha256:" + sha256(raw).hexdigest()


def _unknown(
    *,
    checked_id: str,
    requested_id: str,
    context_kind: str,
    target_atom_id: str,
    reason: str,
    observation_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__REGCAP_CONTEXT_ATOM_NOT_PROVED",
        "reason": reason,
        "predicate_id": checked_id,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "UNKNOWN",
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "canonical_observation": dict(observation_result),
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
        "context_kind",
        "target_atom_id",
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
    context_kind = str(payload.get("context_kind") or "").strip()
    target_atom_id = str(payload.get("target_atom_id") or "").strip()

    if not requested_id:
        return _fail("PREDICATE_ID_REQUIRED")
    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    compiled = observation.compile_span(source_text, start=start, end=end)
    if compiled.get("status") == "FAIL_CLOSED":
        return _fail(
            "CANONICAL_REGCAP_OBSERVATION_FAIL_CLOSED",
            canonical_observation=compiled,
        )
    if compiled.get("pass") is not True:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="CANONICAL_BOUNDED_CONTEXT_NOT_CERTIFIED",
            observation_result=compiled,
        )

    key = (
        str(compiled.get("observation_id") or ""),
        str(compiled.get("outcome") or ""),
    )
    projection = _CANONICAL_OUTCOMES.get(key)
    if projection is None:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="CANONICAL_OBSERVATION_OUTSIDE_CONTEXT_ATOM_API",
            observation_result=compiled,
        )
    if projection["context_kind"] != context_kind:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="CANONICAL_OBSERVATION_CONTEXT_KIND_MISMATCH",
            observation_result=compiled,
        )

    atom_ids = list(projection["atom_ids"])
    if target_atom_id not in atom_ids:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="TARGET_ATOM_NOT_POSITIVELY_PROVED__ABSENCE_IS_NOT_NEGATION",
            observation_result=compiled,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CANONICAL_SOURCE_BOUND_REGCAP_CONTEXT_ATOM_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "proved_atom_ids": atom_ids,
        "canonical_observation": dict(compiled),
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "CANONICAL_VERIFIED_CONTEXTUAL_OBSERVATION_ONLY__"
            "NO_SECOND_LANGUAGE_PARSER__UNRECOGNIZED_WEAKER_NEGATED_ATTRIBUTED_QUOTED_OR_"
            "HYPOTHETICAL_LANGUAGE_REMAINS_UNKNOWN__CONTEXT_PROPERTIES_DO_NOT_MINT_IDENTITY__"
            "NO_OPEN_WORLD_COMPLETENESS_OR_POLICY_ADEQUACY"
        ),
    }

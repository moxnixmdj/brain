"""Bounded CCoB/MREL and CCyB/MREL pair discriminators V1.

This module closes only two exact pairwise ambiguities:
    {REGCAP::CCOB, REGCAP::MREL}
    {REGCAP::CCYB, REGCAP::MREL}

It reuses already-pinned BIS and EBA source packs and already-owned contextual
signature compilers.  It never infers a negative from missing evidence and never
claims global disjointness.  Pair completeness exists only by construction for
the exact declared pair scope.

Accepted positive context markers:
- CCoB: 2.5% CET1 above the regulatory minimum.
- CCyB: release when system-wide risk crystallises/dissipates, or extension of
  the CCoB met with CET1.
- MREL: the minimum requirement for own funds and eligible liabilities is set
  case-by-case by resolution authorities.

Mixed pair markers fail closed.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import regcap_context_signature_v1 as context3
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac_mrel
from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA = "PROJECT_BRAIN_REGCAP_MREL_PAIR_DISCRIMINATOR_V1"

CCOB_MREL = "CCOB_MREL"
CCYB_MREL = "CCYB_MREL"
PAIR_IDS = {CCOB_MREL, CCYB_MREL}

PAIR_SCOPE = {
    CCOB_MREL: "REGCAP_CCOB_MREL_BOUNDED_RIVAL_TASK_V1",
    CCYB_MREL: "REGCAP_CCYB_MREL_BOUNDED_RIVAL_TASK_V1",
}
PAIR_DOMAIN = {
    CCOB_MREL: (regcap.CCOB, mrel.MREL),
    CCYB_MREL: (regcap.CCYB, mrel.MREL),
}
OBSERVATION_ID = "GOVERNING_REQUIREMENT_CLASS"
PAIR_OUTCOMES = {
    CCOB_MREL: {
        regcap.CCOB: "BASEL_CCOB_2_5_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        mrel.MREL: "EU_MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY_REQUIREMENT",
    },
    CCYB_MREL: {
        regcap.CCYB: "BASEL_CCYB_SYSTEM_WIDE_RISK_RELEASABLE_BUFFER",
        mrel.MREL: "EU_MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY_REQUIREMENT",
    },
}

_BIS_SOURCE_ID = "BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01"
_EBA_SOURCE_ID = "EBA_MREL_CASE_BY_CASE_2015"

_SOURCE_REQUIREMENTS = {
    CCOB_MREL: {
        "BIS": ("CCOB_CET1_ABOVE_MINIMUM",),
        "EBA": ("MREL_NOT_FIXED_FIGURE", "MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY"),
    },
    CCYB_MREL: {
        "BIS": (
            "CCYB_RELEASE",
            "CCYB_SYSTEM_RISK_TRIGGER",
            "CCYB_EXTENDS_CCOB",
            "CCYB_CET1",
        ),
        "EBA": ("MREL_NOT_FIXED_FIGURE", "MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY"),
    },
}


def _sha(value: Any) -> str:
    import json
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "relative_selection_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "concept_equivalence_authority": False,
        "concept_disjointness_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _validate_pair_id(pair_id: Any) -> str:
    value = str(pair_id or "").strip().upper()
    if value not in PAIR_IDS:
        raise ValueError("PAIR_ID_INVALID")
    return value


def verify_authority(
    pair_id: str,
    *,
    repo_root: Any = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        pair_id = _validate_pair_id(pair_id)

        regcap_pack = regcap.load_pack(repo_root=repo_root)
        bis_pack = regcap_pack["sources_by_id"][_BIS_SOURCE_ID]
        bis = projection_verifier(dict(bis_pack))
        if not isinstance(bis, Mapping) or bis.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="BIS_SOURCE_AUTHORITY_FAILED",
                pair_id=pair_id,
                source_result=bis,
            )

        tm_pack = tlac_mrel.load_pack(repo_root=repo_root)
        eba_pack = tm_pack["sources_by_id"][_EBA_SOURCE_ID]
        eba = projection_verifier(dict(eba_pack))
        if not isinstance(eba, Mapping) or eba.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="EBA_SOURCE_AUTHORITY_FAILED",
                pair_id=pair_id,
                source_result=eba,
            )

        observed = {
            "BIS": set(
                str(x) for x in bis.get("receipt", {}).get("fragment_ids", [])
            ),
            "EBA": set(
                str(x) for x in eba.get("receipt", {}).get("fragment_ids", [])
            ),
        }
        for source_class, required in _SOURCE_REQUIREMENTS[pair_id].items():
            missing = set(required) - observed[source_class]
            if missing:
                return _base(
                    "FAIL_CLOSED",
                    reason=(
                        "REQUIRED_SOURCE_FRAGMENT_NOT_AUTHENTICATED:"
                        + source_class
                        + ":"
                        + ",".join(sorted(missing))
                    ),
                    pair_id=pair_id,
                )

        material = {
            "pair_id": pair_id,
            "scope_id": PAIR_SCOPE[pair_id],
            "candidate_domain": list(PAIR_DOMAIN[pair_id]),
            "observation_id": OBSERVATION_ID,
            "outcomes": dict(PAIR_OUTCOMES[pair_id]),
            "regcap_pack_git_blob_sha": regcap_pack["pack_git_blob_sha"],
            "tlac_mrel_pack_git_blob_sha": tm_pack["pack_git_blob_sha"],
            "bis_receipt_sha256": bis["receipt"]["receipt_sha256"],
            "eba_receipt_sha256": eba["receipt"]["receipt_sha256"],
        }
        return _base(
            "PASS__REGCAP_MREL_PAIR_DISCRIMINATOR_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            pair_id=pair_id,
            scope_id=PAIR_SCOPE[pair_id],
            candidate_domain=list(PAIR_DOMAIN[pair_id]),
            candidate_universe_complete=True,
            candidate_universe_complete_only_for_scope_id=PAIR_SCOPE[pair_id],
            observation_id=OBSERVATION_ID,
            outcomes=dict(PAIR_OUTCOMES[pair_id]),
            authority_sha256=_sha(material),
            source_results={"BIS": bis, "EBA": eba},
            boundary=(
                "PAIR_COMPLETENESS_ONLY_BY_DECLARED_TASK_SCOPE__"
                "POSITIVE_AUTHENTICATED_MARKERS_ONLY__"
                "NO_GLOBAL_CCOB_MREL_OR_CCYB_MREL_DISJOINTNESS__"
                "NO_OPEN_WORLD_REGCAP_COMPLETENESS"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def _descriptor_sentence(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
) -> tuple[dict[str, Any], str | None]:
    compiled = context3.compile_context(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return compiled, None
    sentence = compiled.get("sentence")
    if not isinstance(sentence, str) or not sentence:
        return compiled, None
    return compiled, sentence


def compile_context(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    pair_id: str,
) -> dict[str, Any]:
    try:
        pair_id = _validate_pair_id(pair_id)
        compiled3, sentence = _descriptor_sentence(
            source_text,
            source_id=source_id,
            start=start,
            end=end,
        )
        if compiled3.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="DESCRIPTOR_CONTEXT_COMPILER_FAIL_CLOSED",
                context_result=compiled3,
            )
        if sentence is None:
            return _base(
                "OPEN__NO_BOUND_PAIR_CONTEXT_SIGNATURE",
                pair_id=pair_id,
                reason="NO_DESCRIPTOR_CONTAINING_SENTENCE",
                context_result=compiled3,
            )

        anchor_candidate = PAIR_DOMAIN[pair_id][0]
        anchor_matches: list[dict[str, Any]] = []
        for row in compiled3.get("observations") or []:
            if not isinstance(row, Mapping):
                continue
            oid = str(row.get("observation_id") or "")
            outcome = str(row.get("outcome") or "")
            if pair_id == CCOB_MREL:
                if (
                    oid == "STRUCTURAL_SIGNATURE_CLASS"
                    and outcome
                    == "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM"
                ):
                    anchor_matches.append(dict(row))
            else:
                if (
                    oid == "FUNCTIONAL_SIGNATURE_CLASS"
                    and outcome
                    == "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
                ) or (
                    oid == "STRUCTURAL_SIGNATURE_CLASS"
                    and outcome == "EXTENDS_CCOB_AND_MET_WITH_CET1"
                ):
                    anchor_matches.append(dict(row))

        mrel_context = tlac_mrel.compile_context(
            sentence,
            source_id=source_id + "::descriptor_sentence",
        )
        mrel_match = bool(
            mrel_context.get("pass") is True
            and mrel_context.get("selected_candidate_hint") == mrel.MREL
        )

        if anchor_matches and mrel_match:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_PAIR_CONTEXT_SIGNATURES",
                pair_id=pair_id,
                anchor_matches=anchor_matches,
                mrel_context=mrel_context,
                sentence=sentence,
            )
        if not anchor_matches and not mrel_match:
            return _base(
                "OPEN__NO_BOUND_PAIR_CONTEXT_SIGNATURE",
                pair_id=pair_id,
                source_id=source_id,
                sentence=sentence,
                context_result=compiled3,
                mrel_context=mrel_context,
            )

        selected = mrel.MREL if mrel_match else anchor_candidate
        outcome = PAIR_OUTCOMES[pair_id][selected]
        return _base(
            "PASS__BOUND_REGCAP_MREL_PAIR_CONTEXT_SIGNATURE",
            passed=True,
            semantic_truth_authority=True,
            pair_id=pair_id,
            selected_candidate_hint=selected,
            observed_outcome=outcome,
            observation_id=OBSERVATION_ID,
            source_id=source_id,
            sentence=sentence,
            anchor_matches=anchor_matches,
            mrel_context=mrel_context,
            boundary=(
                "EXACT_POSITIVE_SAME_SENTENCE_MARKER_BUNDLES_ONLY__"
                "CANDIDATE_IS_A_HINT_UNTIL_PAIR_AUTHORITY_REPLAY"
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
    pair_id: str,
    candidate_concept_ids: Sequence[str],
    repo_root: Any = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    pair_id = _validate_pair_id(pair_id)
    expected = sorted(PAIR_DOMAIN[pair_id])
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
            pair_id=pair_id,
            supplied_candidate_ids=candidates,
            required_candidate_ids=expected,
        )

    compiled = compile_context(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        pair_id=pair_id,
    )
    if compiled.get("pass") is not True:
        return compiled

    authority = verify_authority(
        pair_id,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if authority.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="PAIR_DISCRIMINATOR_AUTHORITY_FAILED",
            pair_id=pair_id,
            authority_result=authority,
        )

    selected = str(compiled.get("selected_candidate_hint") or "")
    outcome = str(compiled.get("observed_outcome") or "")
    if authority.get("outcomes", {}).get(selected) != outcome:
        return _base(
            "FAIL_CLOSED",
            reason="CONTEXT_OUTCOME_NOT_BOUND_TO_AUTHENTICATED_PAIR_MATRIX",
            pair_id=pair_id,
        )

    return _base(
        "PASS__UNIQUE_CONCEPT_IN_BOUND_REGCAP_MREL_PAIR_SCOPE",
        passed=True,
        semantic_truth_authority=True,
        relative_selection_authority=True,
        pair_id=pair_id,
        candidate_universe_complete=True,
        selected_concept_id=selected,
        surviving_candidate_ids=[selected],
        declared_candidate_ids=list(PAIR_DOMAIN[pair_id]),
        observation_id=OBSERVATION_ID,
        observed_outcome=outcome,
        authority_sha256=authority.get("authority_sha256"),
        global_semantic_identity_authority=False,
        boundary=(
            "UNIQUE_ONLY_INSIDE_AUTHENTICATED_TWO_CONCEPT_TASK_SCOPE__"
            "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY__NO_TERMINAL_AUTHORITY"
        ),
    )

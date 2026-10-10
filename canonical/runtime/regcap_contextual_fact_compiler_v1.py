"""Bounded source-aligned regulatory-capital contextual fact compiler V1.

Recognizes three deliberately narrow direct-assertion clause families:
- release when system-wide risk crystallises/dissipates;
- 2.5% CET1 buffer above the regulatory minimum;
- G-SIB loss-absorption + recapitalisation capacity in resolution.

It proves source facts only. It grants no CCoB/CCyB/TLAC identity, no candidate
universe completeness, no negative facts, and no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_FACT_COMPILER_V1"
PROOF_SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_REGCAP_CONTEXTUAL_FACT_PROOF_V1"
CLAIM_KIND = "CERTIFIED_REGCAP_CONTEXT_FACTS"

RELEASE_FULL = "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
RELEASE_DISSIPATES = "RELEASE::SYSTEM_WIDE_RISK_DISSIPATES"
COMPOSITION_CET1 = "COMPOSITION::CET1"
POSITION_ABOVE_MINIMUM = "POSITION::ABOVE_REGULATORY_MINIMUM"
VALUE_2_5_UNKNOWN_BASIS = "QUANTITY::2_5_PERCENT__BASIS_UNKNOWN"
LOSS_ABSORPTION = "FUNCTION::LOSS_ABSORPTION"
LOSS_ABSORPTION_DISPOSITION = "DISPOSITION::LOSS_ABSORPTION"
RECAPITALISATION = "FUNCTION::RECAPITALISATION"
RESOLUTION = "REGIME::RESOLUTION"
G_SIB = "SCOPE::G_SIB"

_WS = re.compile(r"\s+")

_RELEASE_FULL_RE = re.compile(
    r"^(?:the|this|a) (?:buffer|cushion) is released when system-wide risk "
    r"crystalli[sz]es or dissipates\.?$"
)
_RELEASE_DISSIPATES_RE = re.compile(
    r"^(?:the|this|a) (?:buffer|cushion) is released when system-wide risk "
    r"dissipates\.?$"
)
_CET1_RE = re.compile(
    r"^(?:(?:the|this) (?:buffer|cushion) is |a )?2\.5% cet1 "
    r"(?:buffer|cushion) above (?:the )?regulatory minimum(?: capital requirement)?\.?$"
)
_TLAC_RE = re.compile(
    r"^(?:(?:the|this) (?:resource|capacity|cushion) (?:has|provides) )?"
    r"loss-absorbing and recapitali[sz]ation capacity available in resolution "
    r"for (?:a )?g-sib\.?$"
)
_TLAC_FAIL_RE = re.compile(
    r"^if a g-sib fails it has sufficient loss-absorbing and recapitali[sz]ation "
    r"capacity available in resolution\.?$"
)


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip()).casefold()


def _atom(fact_id: str) -> dict[str, str]:
    return {"op": "ATOM", "id": fact_id}


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "concept_identity_authority": False,
        "negative_fact_authority": False,
        "candidate_universe_complete": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def compile_facts(source_text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")

    normalized = _norm(source_text)
    fact_ids: list[str] = []
    family = None
    numeric_basis_complete = None

    if _RELEASE_FULL_RE.fullmatch(normalized):
        family = "SYSTEM_WIDE_RISK_RELEASE"
        fact_ids = [RELEASE_FULL]
    elif _RELEASE_DISSIPATES_RE.fullmatch(normalized):
        family = "SYSTEM_WIDE_RISK_RELEASE"
        fact_ids = [RELEASE_DISSIPATES]
    elif _CET1_RE.fullmatch(normalized):
        family = "CET1_2_5_ABOVE_MINIMUM"
        fact_ids = [
            COMPOSITION_CET1,
            POSITION_ABOVE_MINIMUM,
            VALUE_2_5_UNKNOWN_BASIS,
        ]
        numeric_basis_complete = False
    elif _TLAC_RE.fullmatch(normalized) or _TLAC_FAIL_RE.fullmatch(normalized):
        family = "LOSS_RECAP_RESOLUTION_GSIB"
        fact_ids = [
            LOSS_ABSORPTION,
            LOSS_ABSORPTION_DISPOSITION,
            RECAPITALISATION,
            RESOLUTION,
            G_SIB,
        ]
    else:
        return _base(
            "UNRESOLVED__OUTSIDE_BOUNDED_CONTEXTUAL_GRAMMAR",
            source_id=source_id.strip(),
            source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        )

    constraints = [_atom(fid) for fid in fact_ids]
    return _base(
        "PASS__REGCAP_CONTEXTUAL_FACTS_COMPILED",
        passed=True,
        semantic_truth_authority=True,
        source_id=source_id.strip(),
        source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        family=family,
        fact_ids=fact_ids,
        proved_constraints=constraints,
        numeric_basis_complete=numeric_basis_complete,
        concept_identity_authority=False,
        boundary=(
            "DIRECT_BOUNDED_CLAUSE_TO_POSITIVE_SOURCE_FACTS_ONLY__"
            "NO_CCOB_CCYB_TLAC_IDENTITY__NO_NEGATIVE_FACTS__"
            "NO_HYPOTHESIS_SET_COMPLETENESS__2_5_PERCENT_DENOMINATOR_REMAINS_UNKNOWN"
        ),
    )


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
) -> dict[str, Any]:
    del typed_context, expected_typed_context_sha256, fact_source, fact_source_id
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": PROOF_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    compiled = compile_facts(source_text, source_id=source_id)
    if compiled.get("status") == "FAIL_CLOSED":
        return {
            "schema": PROOF_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(compiled.get("reason") or compiled.get("status"))],
            "terminal_authority": False,
        }

    available = set(compiled.get("fact_ids") or [])
    accepted = []
    rejected = []
    proved = []
    seen = set()

    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            return {
                "schema": PROOF_SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": [f"CLAIM_NOT_OBJECT:{i}"],
                "terminal_authority": False,
            }
        if set(claim) != {"claim_id", "kind", "fact_ids"}:
            cid = str(claim.get("claim_id") or f"index:{i}")
            rejected.append({"claim_id": cid, "reason": "CLAIM_FIELD_SET_INVALID"})
            continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid or cid in seen:
            return {
                "schema": PROOF_SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["CLAIM_ID_INVALID_OR_DUPLICATE:" + cid],
                "terminal_authority": False,
            }
        seen.add(cid)
        if claim.get("kind") != CLAIM_KIND:
            rejected.append({"claim_id": cid, "reason": "CLAIM_KIND_INVALID"})
            continue
        fact_ids = claim.get("fact_ids")
        if (
            not isinstance(fact_ids, Sequence)
            or isinstance(fact_ids, (str, bytes))
            or not fact_ids
            or any(not isinstance(x, str) or not x for x in fact_ids)
        ):
            rejected.append({"claim_id": cid, "reason": "FACT_IDS_INVALID"})
            continue
        requested = list(fact_ids)
        if len(requested) != len(set(requested)):
            rejected.append({"claim_id": cid, "reason": "FACT_IDS_DUPLICATE"})
            continue
        missing = sorted(set(requested) - available)
        if missing:
            rejected.append({
                "claim_id": cid,
                "reason": "FACT_NOT_PROVED_BY_SOURCE",
                "missing_fact_ids": missing,
            })
            continue

        constraints = [_atom(fid) for fid in requested]
        accepted.append({
            "claim_id": cid,
            "kind": CLAIM_KIND,
            "fact_ids": requested,
            "constraints": constraints,
            "source_text_sha256": compiled.get("source_text_sha256"),
            "family": compiled.get("family"),
        })
        proved.extend(constraints)

    return {
        "schema": PROOF_SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "source_compile_status": compiled.get("status"),
        "concept_identity_authority": False,
        "negative_fact_authority": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_FACTS_RECOMPUTED_FROM_THE_BOUNDED_DIRECT_CLAUSE_GRAMMAR_ARE_PROVED;"
            "UNRECOGNIZED_ATTRIBUTED_NEGATED_QUOTED_OR_MORE_GENERAL_PROSE_REMAINS_UNPROVED"
        ),
    }

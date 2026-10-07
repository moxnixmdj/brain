"""Common-policy decision-region adapter for the Brain-owned judgment envelope.

This module does not infer semantics and does not certify adequacy edges.
It preserves V1 unchanged and can relax only V1's conservative UNIQUE-semantics
requirement when the already-existing positive adequacy cover compiler proves
one common policy across every surviving interpretation.

Any other V1 error remains blocking. Caller-provided adequacy edges have zero
authority unless separately bound to sound content-addressed proof receipts.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.judgment_control_envelope_v1 import (
    FINANCE_DOCUMENT,
    FINANCE_SUPERVISORY,
    configured_terminal_decision,
)
from canonical.runtime.k6_positive_adequacy_cover_certificate_v1 import (
    PositiveAdequacyCertificateError,
    certify_positive_cover,
)

SCHEMA = "PROJECT_BRAIN_JUDGMENT_COMMON_POLICY_REGION_GATE_V1"
_UNIQUE_ERROR = "FORCED_CONCLUSION_WITHOUT_UNIQUE_SEMANTIC_IDENTIFICATION"


def _blocked(reason: str, *, base: Mapping[str, Any] | None = None, cover: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "accepted": False,
        "status": "TERMINAL_BLOCKED",
        "reason": reason,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
    if base is not None:
        out["base_v1"] = dict(base)
    if cover is not None:
        out["cover"] = cover
    return out


def configured_terminal_decision_with_common_policy(
    proposal: Any,
    proof_bundle: Any,
    common_policy_binding: Any,
    *,
    mode: str,
) -> dict[str, Any]:
    """Preserve V1; repair only the unique-interpretation overconstraint.

    common_policy_binding is proof plumbing, not semantic authority. Its positive
    adequacy edges must be independently certified before any terminal promotion.
    """
    base = configured_terminal_decision(proposal, proof_bundle, mode=mode)
    if base.get("accepted") is True:
        return {
            "schema": SCHEMA,
            "accepted": True,
            "status": "TERMINAL_ACCEPTED_VIA_V1_UNIQUE_ROUTE",
            "route": "V1_UNIQUE",
            "base_v1": base,
            "terminal_authority": False,
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    errors = set(base.get("errors") or [])
    if errors != {_UNIQUE_ERROR}:
        return _blocked("BASE_V1_HAS_NON_UNIQUENESS_ERRORS", base=base)

    if mode != "FINANCE":
        return _blocked("COMMON_POLICY_REPAIR_CURRENTLY_FINANCE_ONLY", base=base)
    if not isinstance(proposal, Mapping) or proposal.get("decision") != "CONCLUDE":
        return _blocked("COMMON_POLICY_REPAIR_REQUIRES_CONCLUDE", base=base)
    if proposal.get("leaf_id") not in {FINANCE_SUPERVISORY, FINANCE_DOCUMENT}:
        return _blocked("FINANCE_LEAF_INVALID", base=base)

    ident = ((base.get("recomputed_proof") or {}).get("semantic_identifiability") or {})
    if ident.get("status") != "AMBIGUOUS":
        return _blocked("AMBIGUOUS_IDENTIFIABILITY_REQUIRED", base=base)

    witness = ident.get("ambiguity_witness")
    if not isinstance(witness, list) or len(witness) < 2:
        return _blocked("AMBIGUITY_WITNESS_INVALID", base=base)
    worlds = tuple(str(x.get("id") or "") for x in witness if isinstance(x, Mapping))
    if len(worlds) != len(witness) or any(not x for x in worlds) or len(set(worlds)) != len(worlds):
        return _blocked("AMBIGUITY_WORLD_IDS_INVALID", base=base)

    if not isinstance(common_policy_binding, Mapping):
        return _blocked("COMMON_POLICY_BINDING_REQUIRED", base=base)
    if common_policy_binding.get("schema") != "PROJECT_BRAIN_COMMON_POLICY_POSITIVE_ADEQUACY_BINDING_V1":
        return _blocked("COMMON_POLICY_BINDING_SCHEMA_INVALID", base=base)
    if common_policy_binding.get("positive_edges_independently_certified") is not True:
        return _blocked("POSITIVE_ADEQUACY_PROOF_AUTHORITY_MISSING", base=base)

    bound_worlds = common_policy_binding.get("worlds")
    policies = common_policy_binding.get("policies")
    certified = common_policy_binding.get("certified_adequate")
    if not isinstance(bound_worlds, list) or set(map(str, bound_worlds)) != set(worlds):
        return _blocked("COMMON_POLICY_WORLD_DOMAIN_MISMATCH", base=base)
    if not isinstance(policies, list) or not policies:
        return _blocked("COMMON_POLICY_POLICY_DOMAIN_INVALID", base=base)
    if not isinstance(certified, Mapping):
        return _blocked("COMMON_POLICY_ADEQUACY_RELATION_INVALID", base=base)

    try:
        cover = certify_positive_cover(
            worlds=worlds,
            policies=tuple(str(x) for x in policies),
            certified_adequate={
                str(w): tuple(str(p) for p in certified.get(w, ())) for w in worlds
            },
            discriminators=[],
            commitment_deadline=0,
            separator_reacquirable_after_restart_before_deadline=True,
            adequacy_relation_complete=False,
            discriminator_universe_complete=False,
        )
    except PositiveAdequacyCertificateError as exc:
        return _blocked("POSITIVE_COVER_COMPILER_ERROR:" + str(exc), base=base)

    if cover.get("status") != "CERTIFIED_SUFFICIENT_POSITIVE_POLICY_COVER":
        return _blocked("NO_COMMON_CERTIFIED_POLICY", base=base, cover=cover)
    if cover.get("selected_discriminators") != []:
        return _blocked("UNEXPECTED_DISCRIMINATOR_IN_COMMON_POLICY_ROUTE", base=base, cover=cover)

    decisions = cover.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 1:
        return _blocked("COMMON_POLICY_CELL_NOT_SINGLE", base=base, cover=cover)
    cell = decisions[0]
    if set(map(str, cell.get("worlds") or [])) != set(worlds):
        return _blocked("COMMON_POLICY_CELL_WORLD_MISMATCH", base=base, cover=cover)

    policy = str(cell.get("policy") or "")
    proposed = str(proposal.get("selected_alternative") or "")
    recomputed = str((((base.get("recomputed_proof") or {}).get("decision") or {}).get("selected_alternative")) or "")
    if not policy or policy != proposed or policy != recomputed:
        return _blocked("COMMON_POLICY_DOES_NOT_MATCH_RECOMPUTED_TERMINAL_DECISION", base=base, cover=cover)

    return {
        "schema": SCHEMA,
        "accepted": True,
        "status": "TERMINAL_ACCEPTED_VIA_COMMON_CERTIFIED_POLICY_REGION",
        "route": "V1_ALL_OTHER_GATES_PLUS_K6_COMMON_POLICY",
        "selected_policy": policy,
        "surviving_interpretation_ids": sorted(worlds),
        "base_v1": base,
        "cover": cover,
        "positive_adequacy_proof_authority_required": True,
        "semantic_world_identification_required": False,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }

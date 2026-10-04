"""Zero-learned lexical source fusion for H100 missing-domain-term coverage.

OEWN remains the primary lexical source. This fallback is allowed only when the
queried cue is not pinned in OEWN. It requires multi-source role agreement from a
frozen raw-knowledge pack. Ambiguous or unsupported OEWN senses are never
overridden by the fallback.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.h100_oewn_lexical_acquisition_v1 import resolve_lexical_role

SCHEMA = "PROJECT_BRAIN_H100_DOMAIN_TERM_SOURCE_FUSION_V1"
KNOWLEDGE_SCHEMA = "PROJECT_BRAIN_H100_DOMAIN_TERM_SOURCE_FALLBACK_KNOWLEDGE_V1"


class DomainSourceFusionError(ValueError):
    pass


def _norm(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise DomainSourceFusionError(label + "_INVALID")
    text = " ".join(value.strip().lower().split())
    if not text:
        raise DomainSourceFusionError(label + "_EMPTY")
    return text


def _fallback_role(cue: str, knowledge: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(knowledge, Mapping) or knowledge.get("schema") != KNOWLEDGE_SCHEMA:
        raise DomainSourceFusionError("FALLBACK_KNOWLEDGE_SCHEMA_INVALID")

    terms = knowledge.get("terms")
    sources = knowledge.get("sources")
    rule = knowledge.get("consensus_rule")
    if not isinstance(terms, Mapping) or not isinstance(sources, Mapping) or not isinstance(rule, Mapping):
        raise DomainSourceFusionError("FALLBACK_KNOWLEDGE_STRUCTURE_INVALID")

    row = terms.get(cue)
    if not isinstance(row, Mapping):
        return _abstain(cue, "ABSTAIN_SOURCE_TERM_UNPINNED", [])

    evidence = row.get("evidence")
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise DomainSourceFusionError("FALLBACK_EVIDENCE_INVALID:" + cue)

    minimum = rule.get("minimum_independent_sources")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 2:
        raise DomainSourceFusionError("FALLBACK_MINIMUM_SOURCE_RULE_INVALID")

    seen_sources: set[str] = set()
    roles: set[str] = set()
    used: list[str] = []
    allowed = set(rule.get("accepted_roles") or [])
    for i, item in enumerate(evidence):
        if not isinstance(item, Mapping):
            raise DomainSourceFusionError(f"FALLBACK_EVIDENCE_ROW_INVALID:{cue}:{i}")
        source_id = item.get("source")
        role = item.get("normalized_role")
        if not isinstance(source_id, str) or source_id not in sources:
            raise DomainSourceFusionError(f"FALLBACK_SOURCE_INVALID:{cue}:{i}")
        if source_id in seen_sources:
            raise DomainSourceFusionError(f"FALLBACK_SOURCE_DUPLICATE:{cue}:{source_id}")
        if role not in allowed:
            raise DomainSourceFusionError(f"FALLBACK_ROLE_INVALID:{cue}:{i}")
        seen_sources.add(source_id)
        roles.add(str(role))
        used.append(source_id)

    if len(seen_sources) < minimum:
        return _abstain(cue, "ABSTAIN_SOURCE_SUPPORT_INSUFFICIENT", used)
    if len(roles) != 1:
        return _abstain(cue, "ABSTAIN_SOURCE_CONFLICT", used)

    role = next(iter(roles))
    return {
        "schema": SCHEMA,
        "status": "ROLE_IDENTIFIED",
        "cue": cue,
        "role": role,
        "mode": "MULTI_SOURCE_RAW_KNOWLEDGE_CONSENSUS",
        "source_ids": sorted(used),
        "source_count": len(used),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "raw_external_knowledge_used": True,
        "hard_nonclaim": "FINITE_PINNED_SOURCE_FUSION_DOES_NOT_PROVE_OPEN_WORLD_LEXICAL_COMPLETENESS",
    }


def resolve_lexical_role_with_fallback(
    cue: Any,
    context: Any,
    oewn_knowledge: Mapping[str, Any],
    fallback_knowledge: Mapping[str, Any],
) -> dict[str, Any]:
    cue_n = _norm(cue, "CUE")
    primary = resolve_lexical_role(cue_n, context, oewn_knowledge)

    # Only missing coverage can invoke fallback. Real ambiguity stays ambiguous.
    if primary.get("status") != "ABSTAIN_LEXICAL_QUERY_NOT_PINNED":
        out = dict(primary)
        out["fusion_source"] = "OEWN_PRIMARY"
        out["fallback_attempted"] = False
        return out

    fallback = _fallback_role(cue_n, fallback_knowledge)
    fallback["fusion_source"] = "DOMAIN_SOURCE_FALLBACK"
    fallback["fallback_attempted"] = True
    fallback["primary_status"] = primary.get("status")
    return fallback


def _abstain(cue: str, status: str, source_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "cue": cue,
        "role": None,
        "mode": "ABSTAIN",
        "source_ids": sorted(source_ids),
        "source_count": len(source_ids),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "raw_external_knowledge_used": True,
        "hard_nonclaim": "ABSTENTION_PRESERVES_MISSING_INSUFFICIENT_OR_CONFLICTING_SOURCE_SEMANTICS",
    }

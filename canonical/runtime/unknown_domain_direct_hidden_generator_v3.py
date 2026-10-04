"""Unknown-Domain direct hidden generator V3.

V3 is a truth-preserving wrapper over V2 that makes identifier totality a
structural postcondition of every returned population.  V2's truncated opaque
HMAC identifiers are not assumed collision-free.  If any load-bearing opaque
identifier collision is present, generation fails closed and no population is
returned.

This module generates no case on import and grants no execution authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"
GeneratorError=v2.v1.UnknownDomainGeneratorError


def _assert_unique(xs, label: str) -> None:
    vals=[str(x) for x in xs]
    if not vals or any(not x for x in vals) or len(vals)!=len(set(vals)):
        raise GeneratorError(label+"_NOT_TOTAL_UNIQUE")


def _assert_identifier_totality(packet: Mapping[str,Any]) -> None:
    visible=packet.get("visible_cases")
    hidden=packet.get("hidden_records")
    if not isinstance(visible,list) or not isinstance(hidden,list) or len(visible)!=len(hidden):
        raise GeneratorError("PACKET_SHAPE_INVALID")
    _assert_unique([x.get("case_id") for x in visible],"CASE_IDS")

    for v,h in zip(visible,hidden):
        if v.get("case_id")!=h.get("case_id") or v.get("leaf_id")!=h.get("leaf_id"):
            raise GeneratorError("VISIBLE_HIDDEN_IDENTITY_MISMATCH")
        if v.get("leaf_id")!=v2.v1.TRANSFER:
            continue

        relevant=list(h.get("transfer_relevant_feature_ids") or [])
        distractors=list(h.get("distractor_feature_ids") or [])
        _assert_unique(relevant,"TARGET_RELEVANT_IDS")
        _assert_unique(distractors,"TARGET_DISTRACTOR_IDS")
        if set(relevant) & set(distractors):
            raise GeneratorError("TARGET_RELEVANT_DISTRACTOR_COLLISION")

        receipts=v.get("domain_a",{}).get("earned_receipts") or []
        if len(receipts)!=1 or not isinstance(receipts[0],Mapping):
            raise GeneratorError("SOURCE_RECEIPT_INVALID")
        source_binding=receipts[0].get("source_role_binding")
        if not isinstance(source_binding,Mapping):
            raise GeneratorError("SOURCE_ROLE_BINDING_INVALID")
        source_ids=list(source_binding.values())
        _assert_unique(source_ids,"SOURCE_ROLE_IDS")

        target_all=set(relevant)|set(distractors)
        source_all=set()
        for row in v.get("domain_a",{}).get("tasks") or []:
            if isinstance(row,Mapping) and isinstance(row.get("inputs"),Mapping):
                source_all.update(map(str,row["inputs"].keys()))
        if not source_all or source_all & target_all:
            raise GeneratorError("DOMAIN_VOCABULARY_TOTALITY_INVALID")


def _upgrade(packet: dict[str,Any]) -> dict[str,Any]:
    _assert_identifier_totality(packet)
    out=dict(packet)
    out["schema"]=SCHEMA
    out["identifier_totality_verified"]=True
    return out


def generate_production_population(*, beacon:str, evaluator_secret:Any, authority:Mapping[str,Any]):
    return _upgrade(v2.generate_production_population(
        beacon=beacon,evaluator_secret=evaluator_secret,authority=authority
    ))


def generate_qualification_fixture_population(*, beacon:str):
    return _upgrade(v2.generate_qualification_fixture_population(beacon=beacon))

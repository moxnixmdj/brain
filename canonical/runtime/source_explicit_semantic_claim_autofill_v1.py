"""Conservative source-explicit semantic claim autofill V1.

This module proposes only V7/V8 claims whose complete content is deterministically
parsed from exact source bytes. It fills omissions; it never replaces a caller
claim for the same semantic slot, including malformed or contradictory claims.

The output has no semantic truth, execution, acceptance, or terminal authority.
Every synthesized claim must still pass source_aligned_semantic_proof_v8.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.certified_effect_target_scope_v1 import parse_effect_target_scope
from canonical.runtime.certified_effect_id_inventory_v1 import parse_effect_id_inventories
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations

SCHEMA = "PROJECT_BRAIN_SOURCE_EXPLICIT_SEMANTIC_CLAIM_AUTOFILL_V1"
MAX_COMBINED_CLAIMS = 256


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _claim_id(source_id: str, kind: str, slot: str, payload: Mapping[str, Any]) -> str:
    raw = {
        "source_id": source_id,
        "kind": kind,
        "slot": slot,
        "payload": dict(payload),
    }
    return "AUTO_SOURCE_V1::" + sha256(_canon(raw).encode("utf-8")).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "synthesized_claims": [],
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }


def synthesize_missing_claims(
    source_text: str,
    *,
    source_id: str,
    existing_claims: Sequence[Any],
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_MISSING")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_MISSING")
    if not isinstance(existing_claims, Sequence) or isinstance(existing_claims, (str, bytes)):
        return _fail("EXISTING_CLAIMS_INVALID")
    if len(existing_claims) > MAX_COMBINED_CLAIMS:
        return _fail("EXISTING_CLAIM_COUNT_EXCEEDS_BOUND")

    existing_ids: set[str] = set()
    scope_claim_present = False
    inventory_targets: set[str] = set()
    relation_effect_ids: set[str] = set()
    block_all_inventory_autofill = False
    block_all_relation_autofill = False

    for row in existing_claims:
        if not isinstance(row, Mapping):
            continue
        cid = row.get("claim_id")
        if isinstance(cid, str) and cid:
            existing_ids.add(cid)
        kind = row.get("kind")
        if kind == "CERTIFIED_EFFECT_TARGET_SCOPE":
            scope_claim_present = True
        elif kind == "CERTIFIED_EFFECT_ID_INVENTORY":
            target = row.get("target_id")
            if isinstance(target, str) and target.strip():
                inventory_targets.add(target.strip())
            else:
                block_all_inventory_autofill = True
        elif kind == "CERTIFIED_DOCUMENT_EFFECT_RELATION":
            effect = row.get("effect")
            eid = effect.get("effect_id") if isinstance(effect, Mapping) else None
            if isinstance(eid, str) and eid.strip():
                relation_effect_ids.add(eid.strip())
            else:
                block_all_relation_autofill = True

    synthesized: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    scope = parse_effect_target_scope(source_text, source=source_id)
    diagnostics.append({
        "primitive": "CERTIFIED_EFFECT_TARGET_SCOPE",
        "parse_status": scope.get("status"),
        "parse_reason": scope.get("reason"),
    })
    if not scope_claim_present and scope.get("status") == "PARSED":
        parsed = scope["parse"]
        payload = {
            "kind": "CERTIFIED_EFFECT_TARGET_SCOPE",
            "target_ids": list(parsed["target_ids"]),
        }
        claim = {
            "claim_id": _claim_id(source_id, payload["kind"], "scope", payload),
            **payload,
        }
        if claim["claim_id"] in existing_ids:
            return _fail("AUTO_CLAIM_ID_COLLISION")
        synthesized.append(claim)

    inventories = parse_effect_id_inventories(source_text, source=source_id)
    diagnostics.append({
        "primitive": "CERTIFIED_EFFECT_ID_INVENTORY",
        "parse_status": inventories.get("status"),
        "parse_reason": inventories.get("reason"),
    })
    if not block_all_inventory_autofill and inventories.get("status") == "PARSED":
        for parsed in inventories.get("inventories") or []:
            target = str(parsed.get("target_id") or "")
            if not target or target in inventory_targets:
                continue
            payload = {
                "kind": "CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id": target,
                "effect_ids": list(parsed.get("effect_ids") or []),
            }
            claim = {
                "claim_id": _claim_id(
                    source_id, payload["kind"], "inventory:" + target, payload
                ),
                **payload,
            }
            if claim["claim_id"] in existing_ids:
                return _fail("AUTO_CLAIM_ID_COLLISION")
            synthesized.append(claim)

    relations = parse_effect_relations(source_text, source=source_id)
    diagnostics.append({
        "primitive": "CERTIFIED_DOCUMENT_EFFECT_RELATION",
        "parse_status": relations.get("status"),
        "parse_reason": relations.get("reason"),
    })
    if not block_all_relation_autofill and relations.get("status") == "PARSED":
        for parsed in relations.get("relations") or []:
            effect = parsed.get("effect")
            if not isinstance(effect, Mapping):
                continue
            eid = str(effect.get("effect_id") or "")
            if not eid or eid in relation_effect_ids:
                continue
            semantics = {k: v for k, v in effect.items() if k != "source_locator"}
            payload = {
                "kind": "CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect": semantics,
            }
            claim = {
                "claim_id": _claim_id(
                    source_id, payload["kind"], "relation:" + eid, payload
                ),
                **payload,
            }
            if claim["claim_id"] in existing_ids:
                return _fail("AUTO_CLAIM_ID_COLLISION")
            synthesized.append(claim)

    if len(existing_claims) + len(synthesized) > MAX_COMBINED_CLAIMS:
        return _fail("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")

    return {
        "schema": SCHEMA,
        "status": "PASS__SOURCE_EXPLICIT_OMISSIONS_COMPILED",
        "pass": True,
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "existing_claim_count": len(existing_claims),
        "synthesized_claim_count": len(synthesized),
        "combined_claim_count": len(existing_claims) + len(synthesized),
        "synthesized_claims": synthesized,
        "diagnostics": diagnostics,
        "fills_omissions_only": True,
        "caller_claim_replacement_allowed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }

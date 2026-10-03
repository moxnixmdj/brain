"""Fail-closed queryless bounded-corpus enumeration kernel for Retrieval V6."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RETRIEVAL_BOUNDED_ENUMERATOR_V1"


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def start(scope: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(scope, Mapping):
        raise ValueError("SCOPE_MAPPING_REQUIRED")
    source_id = _canon(scope.get("source_id"))
    scope_id = _canon(scope.get("scope_id"))
    if not source_id or not scope_id:
        raise ValueError("SOURCE_AND_SCOPE_ID_REQUIRED")
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "scope_id": scope_id,
        "declared_finite": scope.get("declared_finite") is True,
        "independently_verified_finite": scope.get("independently_verified_finite") is True,
        "expected_cursor": _canon(scope.get("start_cursor")) or None,
        "pages": [],
        "items": {},
        "failed": False,
        "final_seen": False,
        "complete": False,
        "nonexistence_claim_authorized": False,
        "authority": "CANDIDATE_ONLY",
    }


def consume_page(state: Mapping[str, Any], page: Mapping[str, Any]) -> dict[str, Any]:
    if state.get("schema") != SCHEMA:
        raise ValueError("ENUMERATOR_STATE_INVALID")
    if not isinstance(page, Mapping):
        raise ValueError("PAGE_MAPPING_REQUIRED")
    out = json.loads(json.dumps(state))
    if out.get("failed") or out.get("final_seen"):
        raise ValueError("ENUMERATION_ALREADY_TERMINAL")
    cursor = _canon(page.get("cursor")) or None
    if cursor != out.get("expected_cursor"):
        raise ValueError("CURSOR_CHAIN_MISMATCH")
    if page.get("success") is not True:
        out["failed"] = True
        out["failure"] = _canon(page.get("error")) or "PAGE_FAILED"
        out["complete"] = False
        out["nonexistence_claim_authorized"] = False
        return out

    items = page.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        raise ValueError("PAGE_ITEMS_LIST_REQUIRED")
    page_ids: list[str] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            raise ValueError("ENUMERATED_ITEM_MAPPING_REQUIRED")
        item_id = _canon(raw.get("item_id") or raw.get("id") or raw.get("url") or raw.get("name"))
        if not item_id:
            raise ValueError("ENUMERATED_ITEM_ID_REQUIRED")
        digest = hashlib.sha256(item_id.encode()).hexdigest()
        page_ids.append(digest)
        out.setdefault("items", {}).setdefault(digest, dict(raw))

    final = page.get("final") is True
    next_cursor = _canon(page.get("next_cursor")) or None
    if final and next_cursor is not None:
        raise ValueError("FINAL_PAGE_CANNOT_HAVE_NEXT_CURSOR")
    if not final and next_cursor is None:
        raise ValueError("NONFINAL_PAGE_REQUIRES_NEXT_CURSOR")
    out.setdefault("pages", []).append({
        "cursor": cursor,
        "next_cursor": next_cursor,
        "final": final,
        "item_ids": page_ids,
    })
    out["expected_cursor"] = next_cursor
    out["final_seen"] = final
    if final:
        out["complete"] = bool(out.get("declared_finite") and out.get("independently_verified_finite"))
        out["nonexistence_claim_authorized"] = bool(out["complete"])
    return out


def status(state: Mapping[str, Any]) -> dict[str, Any]:
    if state.get("failed"):
        s = "FAILED_RETRYABLE_OR_SCOPE_UNKNOWN"
    elif state.get("complete"):
        s = "DECLARED_FINITE_SCOPE_EXHAUSTIVELY_ENUMERATED"
    elif state.get("final_seen"):
        s = "FINAL_PAGE_SEEN_BUT_SCOPE_COMPLETENESS_UNPROVED"
    else:
        s = "ENUMERATION_IN_PROGRESS"
    return {
        "schema": "PROJECT_BRAIN_RETRIEVAL_BOUNDED_ENUMERATION_STATUS_V1",
        "status": s,
        "item_count": len(state.get("items") or {}),
        "page_count": len(state.get("pages") or []),
        "complete": state.get("complete") is True,
        "scope_limited": True,
        "nonexistence_claim_authorized": state.get("nonexistence_claim_authorized") is True,
        "open_world_completeness_claim_authorized": False,
        "acceptance_credit_delta": 0,
    }

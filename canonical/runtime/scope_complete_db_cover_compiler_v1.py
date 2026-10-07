"""Scope-complete D_B cover compiler.

This is the fail-closed global bridge from cell-level D_B admission to U-empty.

It does not invent scope completeness. A separately independently verified
partition receipt must bind the exact set of cell definitions. Every cell must
have an independently verified membership receipt and must actually pass one of
the existing D_B admission routes. Only then may this compiler authorize
U-empty / ABC-closed for the bound scope. D finality remains separate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_elision_db_admission_v1 as db
from canonical.runtime import source_positive_adequacy_db_admission_v1 as source_db

SCHEMA = "PROJECT_BRAIN_SCOPE_COMPLETE_DB_COVER_COMPILER_V1"
SOURCE_ROUTE = "D_SOURCE_POSITIVE_ADEQUACY"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def partition_digest(scope_id: str, cells: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for row in cells:
        rows.append({
            "cell_id": str(row.get("cell_id") or ""),
            "cell_definition_sha256": str(row.get("cell_definition_sha256") or ""),
        })
    rows.sort(key=lambda x: (x["cell_id"], x["cell_definition_sha256"]))
    body = {"scope_id": str(scope_id or ""), "cells": rows}
    return "sha256:" + sha256(_canon(body).encode("utf-8")).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "d_finality_required": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _valid_sha256(x: Any) -> bool:
    if not isinstance(x, str) or not x.startswith("sha256:"):
        return False
    h = x[7:]
    return len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def _membership(scope_id: str, row: Mapping[str, Any]) -> tuple[bool, str]:
    cid = str(row.get("cell_id") or "").strip()
    csha = row.get("cell_definition_sha256")
    if not cid or not _valid_sha256(csha):
        return False, "CELL_ID_OR_DEFINITION_DIGEST_INVALID"
    r = row.get("membership_receipt")
    if not isinstance(r, Mapping):
        return False, "CELL_MEMBERSHIP_RECEIPT_REQUIRED"
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion") != "success"
        or r.get("membership_proved") is not True
    ):
        return False, "CELL_MEMBERSHIP_RECEIPT_INVALID"
    if str(r.get("scope_id") or "").strip() != scope_id:
        return False, "CELL_MEMBERSHIP_SCOPE_MISMATCH"
    if str(r.get("cell_id") or "").strip() != cid:
        return False, "CELL_MEMBERSHIP_ID_MISMATCH"
    if r.get("cell_definition_sha256") != csha:
        return False, "CELL_MEMBERSHIP_DEFINITION_MISMATCH"
    if not str(r.get("receipt_id") or "").strip():
        return False, "CELL_MEMBERSHIP_RECEIPT_ID_REQUIRED"
    return True, ""


def _admit(candidate: Mapping[str, Any]) -> dict[str, Any]:
    route = candidate.get("route")
    if route == SOURCE_ROUTE:
        body = candidate.get("payload")
        if not isinstance(body, Mapping):
            return _fail("SOURCE_ADMISSION_PAYLOAD_MAPPING_REQUIRED")
        return source_db.evaluate(body)
    return db.evaluate(candidate)


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    scope_id = str(payload.get("scope_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    cells = payload.get("cells")
    if not isinstance(cells, Sequence) or isinstance(cells, (str, bytes)) or not cells:
        return _fail("CELLS_REQUIRED")
    if any(not isinstance(x, Mapping) for x in cells):
        return _fail("CELL_NOT_MAPPING")

    ids = [str(x.get("cell_id") or "").strip() for x in cells]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        return _fail("CELL_ID_INVALID_OR_DUPLICATE")

    expected_partition = partition_digest(scope_id, cells)
    receipt = payload.get("scope_partition_receipt")
    if not isinstance(receipt, Mapping):
        return _fail("SCOPE_PARTITION_RECEIPT_REQUIRED")
    if (
        receipt.get("independent_verified") is not True
        or receipt.get("exact_byte_bound") is not True
        or receipt.get("conclusion") != "success"
        or receipt.get("scope_partition_complete") is not True
    ):
        return _fail("SCOPE_PARTITION_COMPLETENESS_UNPROVED")
    if str(receipt.get("scope_id") or "").strip() != scope_id:
        return _fail("SCOPE_PARTITION_SCOPE_MISMATCH")
    if receipt.get("partition_sha256") != expected_partition:
        return _fail("SCOPE_PARTITION_DIGEST_MISMATCH")
    if not str(receipt.get("receipt_id") or "").strip():
        return _fail("SCOPE_PARTITION_RECEIPT_ID_REQUIRED")

    admitted = []
    for row in cells:
        cid = str(row.get("cell_id") or "").strip()
        ok, why = _membership(scope_id, row)
        if not ok:
            return _fail(why + ":" + cid)

        candidate = row.get("admission_candidate")
        if not isinstance(candidate, Mapping):
            return _fail("CELL_ADMISSION_CANDIDATE_REQUIRED:" + cid)

        try:
            result = _admit(candidate)
        except Exception as exc:
            return _fail(
                "CELL_ADMISSION_EXCEPTION:" + cid,
                exception_type=type(exc).__name__,
            )

        if result.get("pass") is not True or result.get("db_admission_authorized") is not True:
            return _fail(
                "CELL_DB_ADMISSION_UNPROVED:" + cid,
                admission_status=result.get("status"),
            )
        if str(result.get("cell_id") or "").strip() != cid:
            return _fail("CELL_DB_ADMISSION_ID_MISMATCH:" + cid)

        admitted.append({
            "cell_id": cid,
            "cell_definition_sha256": row.get("cell_definition_sha256"),
            "route": candidate.get("route"),
            "admission_status": result.get("status"),
        })

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SCOPE_COMPLETE_SOUND_DB_COVER__U_EMPTY_AUTHORIZED",
        "scope_id": scope_id,
        "partition_sha256": expected_partition,
        "cell_count": len(admitted),
        "admitted_cells": admitted,
        "u_empty_authorized": True,
        "abc_closed_authorized": True,
        "d_finality_required": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "ABC_ONLY_FOR_THE_EXACT_RECEIPT_BOUND_SCOPE__TERMINAL_REMAINS_FALSE_"
            "UNTIL_FINAL_ROUTE_FREEZE_D_EFFECT_OWNERSHIP_DONOR_INDEPENDENCE_AND_CLEAN_ROOM_REPLAY"
        ),
    }

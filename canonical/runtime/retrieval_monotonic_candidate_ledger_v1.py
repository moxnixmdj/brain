"""Monotonic candidate ledger for Retrieval V6.

Candidates may be deprioritized or falsified, but once observed their identity and
provenance are retained. Reranking is therefore incapable of silently deleting a
candidate before downstream verification.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "PROJECT_BRAIN_RETRIEVAL_MONOTONIC_CANDIDATE_LEDGER_V1"
FORBIDDEN_AUTHORITY_FIELDS = (
    "acceptance_credit", "family_credit", "capability_credit", "ownership_credit",
    "promotion_authority", "execution_authority", "verified_sufficient",
)
DISPOSITIONS = {"ACTIVE", "DEPRIORITIZED", "FALSIFIED", "VERIFIED_SUFFICIENT"}


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_url(value: Any) -> str:
    raw = _canon(value)
    if not raw:
        return ""
    try:
        p = urlsplit(raw)
        host = (p.hostname or "").casefold()
        if not host:
            return raw
        netloc = host
        if p.port:
            netloc += f":{p.port}"
        path = p.path.rstrip("/") or "/"
        return urlunsplit((p.scheme.casefold() or "https", netloc, path, p.query, ""))
    except Exception:
        return raw


def candidate_id(row: Mapping[str, Any]) -> str:
    if not isinstance(row, Mapping):
        raise ValueError("CANDIDATE_MAPPING_REQUIRED")
    identity = {
        "url": _normalize_url(row.get("url")),
        "repository": _canon(row.get("repository") or row.get("repo")),
        "path": _canon(row.get("path")),
        "ref": _canon(row.get("ref") or row.get("revision")),
        "package": _canon(row.get("package")),
        "doi": _canon(row.get("doi")),
        "source": _canon(row.get("source") or row.get("backend_id") or row.get("federation_domain")),
    }
    if not any(identity.values()):
        raise ValueError("CANDIDATE_STABLE_IDENTITY_REQUIRED")
    raw = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def empty_ledger() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "ACTIVE",
        "records": {},
        "epochs": [],
        "candidate_count": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def ingest(ledger: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], *, epoch_id: str) -> dict[str, Any]:
    if ledger.get("schema") != SCHEMA:
        raise ValueError("LEDGER_SCHEMA_INVALID")
    epoch = _canon(epoch_id)
    if not epoch:
        raise ValueError("EPOCH_ID_REQUIRED")
    out = json.loads(json.dumps(ledger))
    records = out.setdefault("records", {})
    before = set(records)
    new_ids: list[str] = []
    observed_ids: list[str] = []

    for raw in candidates:
        if not isinstance(raw, Mapping):
            raise ValueError("CANDIDATE_MAPPING_REQUIRED")
        for field in FORBIDDEN_AUTHORITY_FIELDS:
            if raw.get(field) not in (None, False, 0, [], {}):
                raise ValueError("CANDIDATE_AUTHORITY_SMUGGLING:" + field)
        cid = candidate_id(raw)
        observed_ids.append(cid)
        observation = dict(raw)
        observation["candidate_id"] = cid
        observation["epoch_id"] = epoch
        if cid not in records:
            records[cid] = {
                "candidate_id": cid,
                "first_seen_epoch": epoch,
                "last_seen_epoch": epoch,
                "disposition": "ACTIVE",
                "observations": [observation],
                "independent_verification_receipts": [],
            }
            new_ids.append(cid)
        else:
            rec = records[cid]
            rec["last_seen_epoch"] = epoch
            if observation not in rec.setdefault("observations", []):
                rec["observations"].append(observation)

    after = set(records)
    if not before.issubset(after):
        raise RuntimeError("MONOTONICITY_VIOLATION_CANDIDATE_REMOVED")
    out.setdefault("epochs", []).append({
        "epoch_id": epoch,
        "observed_candidate_ids": sorted(set(observed_ids)),
        "new_candidate_ids": sorted(new_ids),
    })
    out["candidate_count"] = len(records)
    out["last_epoch_new_candidate_count"] = len(new_ids)
    out["removed_candidate_count"] = 0
    out["monotonic_retention"] = True
    return out


def mark_disposition(
    ledger: Mapping[str, Any], *, candidate_id_value: str, disposition: str,
    reason: str, independent_receipt: str | None = None,
) -> dict[str, Any]:
    if disposition not in DISPOSITIONS:
        raise ValueError("DISPOSITION_INVALID")
    out = json.loads(json.dumps(ledger))
    records = out.get("records") or {}
    cid = _canon(candidate_id_value)
    if cid not in records:
        raise ValueError("CANDIDATE_NOT_FOUND")
    if disposition == "VERIFIED_SUFFICIENT" and not _canon(independent_receipt):
        raise ValueError("VERIFIED_SUFFICIENT_REQUIRES_INDEPENDENT_RECEIPT")
    rec = records[cid]
    rec["disposition"] = disposition
    rec.setdefault("disposition_history", []).append({"disposition": disposition, "reason": _canon(reason)})
    if independent_receipt:
        receipt = _canon(independent_receipt)
        if receipt not in rec.setdefault("independent_verification_receipts", []):
            rec["independent_verification_receipts"].append(receipt)
    out["candidate_count"] = len(records)
    out["removed_candidate_count"] = 0
    out["monotonic_retention"] = True
    return out

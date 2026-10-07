"""Lossless compiler for the explicit finite P2 semantic-contract source class.

This owns one parameterized subregion:
the authoritative raw task source is itself a strict JSON encoding of exactly the
load-bearing P2 semantic fields. No extra task/evidence/edit fields are accepted,
because an extra field could be a load-bearing semantic dimension omitted by P2.

This does not parse free-form professional language and does not claim global
AA-Briefcase/GDPval coverage. It proves membership only for the explicit source
class it validates.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "BRAIN_P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
MAX_BYTES = 2_000_000
IDENT = re.compile(r"^[A-Za-z0-9_.:-]+$")
TASK_KEYS = {"audience", "required_topics", "evidence", "edit_candidates", "edit_budget"}
EVIDENCE_KEYS = {"fact_id"}
EDIT_KEYS = {"id", "analysis_kind", "topic", "claims", "intended_audience", "cost"}


class MembershipError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise MembershipError("DUPLICATE_JSON_KEY:" + str(k))
        out[k] = v
    return out


def _token(v: Any, label: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise MembershipError(label + "_INVALID")
    return v.strip()


def _string_list(v: Any, label: str, *, unique: bool = True) -> list[str]:
    if not isinstance(v, list) or any(not isinstance(x, str) or not x.strip() for x in v):
        raise MembershipError(label + "_INVALID")
    out = [x.strip() for x in v]
    if unique and len(out) != len(set(out)):
        raise MembershipError(label + "_DUPLICATE")
    return out


def compile_membership(raw_source: str | bytes, *, source_id: str) -> dict[str, Any]:
    try:
        sid = _token(source_id, "SOURCE_ID")
        raw = raw_source.encode("utf-8") if isinstance(raw_source, str) else raw_source
        if not isinstance(raw, bytes):
            raise MembershipError("RAW_SOURCE_MUST_BE_TEXT_OR_BYTES")
        if not raw:
            raise MembershipError("RAW_SOURCE_EMPTY")
        if len(raw) > MAX_BYTES:
            raise MembershipError("RAW_SOURCE_TOO_LARGE")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MembershipError("RAW_SOURCE_NOT_UTF8") from exc
        try:
            doc = json.loads(text, object_pairs_hook=_pairs)
        except MembershipError:
            raise
        except Exception as exc:
            raise MembershipError("RAW_SOURCE_JSON_INVALID") from exc

        if not isinstance(doc, Mapping) or set(doc) != {"contract", "task"}:
            raise MembershipError("TOP_LEVEL_KEYS_INVALID")
        if doc.get("contract") != P2:
            raise MembershipError("P2_CONTRACT_REQUIRED")
        task = doc.get("task")
        if not isinstance(task, Mapping) or set(task) != TASK_KEYS:
            raise MembershipError("TASK_KEYS_NOT_EXACT_P2_BASIS")

        audience = _token(task.get("audience"), "AUDIENCE")
        required_topics = _string_list(task.get("required_topics"), "REQUIRED_TOPICS")
        if not required_topics:
            raise MembershipError("REQUIRED_TOPICS_EMPTY")

        evidence = task.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise MembershipError("EVIDENCE_INVALID_OR_EMPTY")
        facts = []
        fact_ids = set()
        for i, row in enumerate(evidence):
            if not isinstance(row, Mapping) or set(row) != EVIDENCE_KEYS:
                raise MembershipError(f"EVIDENCE_ROW_KEYS_INVALID:{i}")
            fid = _token(row.get("fact_id"), f"FACT_ID:{i}")
            if not IDENT.fullmatch(fid):
                raise MembershipError(f"FACT_ID_FORMAT_INVALID:{i}")
            if fid in fact_ids:
                raise MembershipError("FACT_ID_DUPLICATE:" + fid)
            fact_ids.add(fid)
            facts.append({"fact_id": fid})

        edits_raw = task.get("edit_candidates")
        if not isinstance(edits_raw, list) or not edits_raw:
            raise MembershipError("EDIT_CANDIDATES_INVALID_OR_EMPTY")
        edits = []
        edit_ids = set()
        for i, row in enumerate(edits_raw):
            if not isinstance(row, Mapping) or set(row) != EDIT_KEYS:
                raise MembershipError(f"EDIT_ROW_KEYS_INVALID:{i}")
            eid = _token(row.get("id"), f"EDIT_ID:{i}")
            if not IDENT.fullmatch(eid):
                raise MembershipError(f"EDIT_ID_FORMAT_INVALID:{i}")
            if eid in edit_ids:
                raise MembershipError("EDIT_ID_DUPLICATE:" + eid)
            edit_ids.add(eid)
            analysis = _token(row.get("analysis_kind"), f"EDIT_ANALYSIS_KIND:{eid}")
            topic = _token(row.get("topic"), f"EDIT_TOPIC:{eid}")
            intended = _token(row.get("intended_audience"), f"EDIT_AUDIENCE:{eid}")
            claims = _string_list(row.get("claims"), f"EDIT_CLAIMS:{eid}")
            if not claims:
                raise MembershipError("EDIT_CLAIMS_EMPTY:" + eid)
            cost = row.get("cost")
            if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0:
                raise MembershipError("EDIT_COST_INVALID:" + eid)
            edits.append({
                "id": eid,
                "analysis_kind": analysis,
                "topic": topic,
                "claims": claims,
                "intended_audience": intended,
                "cost": cost,
            })

        budget = task.get("edit_budget")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
            raise MembershipError("EDIT_BUDGET_INVALID")

        public = {
            "contract": P2,
            "task": {
                "audience": audience,
                "required_topics": required_topics,
                "evidence": facts,
                "edit_candidates": edits,
                "edit_budget": budget,
            },
        }
        raw_sha = sha256(raw).hexdigest()
        normalized = json.dumps(public, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        normalized_sha = sha256(normalized).hexdigest()
        receipt = "P2MEM:" + sha256(
            (sid + "\0" + raw_sha + "\0" + normalized_sha).encode("utf-8")
        ).hexdigest()
        return {
            "schema": SCHEMA,
            "status": "PASS__LOSSLESS_EXPLICIT_P2_SOURCE_MEMBERSHIP",
            "pass": True,
            "source_id": sid,
            "raw_source_sha256": raw_sha,
            "normalized_public_sha256": normalized_sha,
            "membership_receipt": receipt,
            "public": public,
            "field_basis": [
                "FINITE_UNIQUE_EVIDENCE_FACT_IDS",
                "FINITE_UNIQUE_EDIT_IDS",
                "AUDIENCE",
                "REQUIRED_TOPICS",
                "EDIT_TOPIC",
                "EDIT_CLAIM_FACT_IDS",
                "EDIT_INTENDED_AUDIENCE",
                "EDIT_ANALYSIS_KIND",
                "INTEGER_EDIT_COST",
                "NONNEGATIVE_EDIT_BUDGET",
            ],
            "extra_source_semantic_fields_permitted": False,
            "terminal_authority": False,
            "scope": "STRICT_EXPLICIT_P2_JSON_SOURCE_CLASS_ONLY",
        }
    except MembershipError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [str(exc)],
            "terminal_authority": False,
        }

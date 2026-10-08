"""Bounded exact set-membership support v1.

Deterministic categorical relation checker over the controlled entity/field/value
surface. Supported claim forms:
  <entity> <field> is in {a, b, c}.
  <entity> <field> is not in {a, b, c}.
  <entity> <field> is one of {a, b, c}.
  <entity> <field> is not one of {a, b, c}.

Evidence must resolve to one exact entity/field/value fact using the existing
bounded fact grammar. No ontology expansion, synonymy, hierarchy, fuzzy category,
source authority, or world knowledge is inferred.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import bounded_claim_support as facts

SCHEMA = "PROJECT_BRAIN_BOUNDED_SET_MEMBERSHIP_SUPPORT_V1"

_PREFIX = re.compile(
    r"^(?P<entity>[A-Za-z][A-Za-z0-9_ -]*?)\s+"
    r"(?P<field>[A-Za-z][A-Za-z0-9_ -]*?)\s+"
    r"is\s+(?P<neg>not\s+)?(?:(?:one\s+of)|in)\s+"
    r"\{(?P<items>[^{}]+)\}\s*\.?$",
    re.I,
)


def _norm_words(x: str) -> str:
    return " ".join(x.strip().lower().split())


def _norm_value(x: str) -> str:
    return " ".join(x.strip().lower().split())


def parse_set_membership_claim(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TEXT_REQUIRED", "claim_in_scope": False}
    raw = " ".join(text.strip().split())
    m = _PREFIX.fullmatch(raw)
    if not m:
        return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "CLAIM_OUTSIDE_SET_MEMBERSHIP_GRAMMAR", "claim_in_scope": False}
    items = [_norm_value(x) for x in m.group("items").split(",")]
    if any(not x for x in items) or len(items) != len(set(items)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SET_ITEMS_INVALID_OR_DUPLICATE", "claim_in_scope": True}
    if len(items) > 64:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SET_TOO_LARGE", "claim_in_scope": True}
    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "claim_in_scope": True,
        "entity": _norm_words(m.group("entity")),
        "field": _norm_words(m.group("field")),
        "operator": "NOT_IN" if m.group("neg") else "IN",
        "members": sorted(items),
        "terminal_authority": False,
    }


def classify_support(claim_text: str, evidence_text: str, *, evidence_id: str | None = None) -> dict[str, Any]:
    claim = parse_set_membership_claim(claim_text)
    if claim.get("status") != "RESOLVED":
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": "UNKNOWN",
            "claim_in_scope": bool(claim.get("claim_in_scope")),
            "reason": claim.get("reason"),
            "terminal_authority": False,
        }

    ev = facts.parse_fact(evidence_text, default_source=evidence_id or "EVIDENCE")
    if ev.get("status") != "RESOLVED":
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": "UNKNOWN",
            "claim_in_scope": True,
            "reason": "EVIDENCE_OUTSIDE_EXACT_FACT_GRAMMAR",
            "terminal_authority": False,
        }
    fact = ev["fact"]
    if fact["entity"] != claim["entity"] or fact["field"] != claim["field"]:
        relation = "UNRELATED"
    else:
        inside = fact["value"] in set(claim["members"])
        holds = inside if claim["operator"] == "IN" else not inside
        relation = "SUPPORTS" if holds else "CONFLICTS"

    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "relation": relation,
        "claim_in_scope": True,
        "claim": {
            "entity": claim["entity"],
            "field": claim["field"],
            "operator": claim["operator"],
            "members": claim["members"],
        },
        "evidence": {
            "entity": fact["entity"],
            "field": fact["field"],
            "value": fact["value"],
            "source": fact["source"],
        },
        "terminal_authority": False,
        "scope": "EXACT_SET_MEMBERSHIP_OVER_CONTROLLED_ENTITY_FIELD_VALUE_FACT_SURFACE_ONLY",
    }

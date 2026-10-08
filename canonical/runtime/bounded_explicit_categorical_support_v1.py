"""Bounded explicit categorical support v1.

Deterministic support for an intentionally tiny categorical language:
- "<entity> is a member of <class>"
- "<entity> is an instance of <class>"
- negated variants of those forms
- "<class> is a subclass of <class>"
- "<class> is a subset of <class>"
- negated variants of those forms

Positive subclass edges may be composed transitively. Positive membership propagates
upward through verified positive subclass edges. Explicit negative membership propagates
downward: if A is a subclass of B and x is not a member of B, then x is not a
member of A. The reverse negative inference is forbidden.

This module evaluates support within the supplied evidence set. It does not infer
synonymy, taxonomy from names, world knowledge, source authority, or closed-world
negation. Category-shaped evidence that cannot be parsed remains UNKNOWN.
"""
from __future__ import annotations

from collections import deque
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUNDED_EXPLICIT_CATEGORICAL_SUPPORT_V1"

_PREFIXES = (
    re.compile(r"^(?P<source>.+?)\s+(?:reports|states)\s+(?:that\s+)?(?P<body>.+)$", re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$", re.I),
)
_TOKEN = r"[A-Za-z0-9][A-Za-z0-9 _'-]{0,159}"
_MEMBER = re.compile(
    rf"^(?P<subject>{_TOKEN}?)\s+is\s+(?P<neg>not\s+)?(?:a\s+)?"
    rf"(?P<kind>member|instance)\s+of\s+(?P<object>{_TOKEN})$",
    re.I,
)
_SUBCLASS = re.compile(
    rf"^(?P<subject>{_TOKEN}?)\s+is\s+(?P<neg>not\s+)?(?:a\s+)?"
    rf"(?P<kind>subclass|subset)\s+of\s+(?P<object>{_TOKEN})$",
    re.I,
)
_HINT = re.compile(r"\b(?:member|instance|subclass|subset)\s+of\b", re.I)


def _canon(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split()).casefold()


def _surface(text: str) -> tuple[str, str | None]:
    raw = " ".join(str(text if text is not None else "").strip().split())
    if raw.endswith("."):
        raw = raw[:-1].rstrip()
    source = None
    body = raw
    for pat in _PREFIXES:
        m = pat.fullmatch(raw)
        if m:
            source = " ".join(m.group("source").split())
            body = m.group("body").strip()
            break
    return body, source


def parse_categorical_statement(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TEXT_REQUIRED", "claim_in_scope": False}
    body, source = _surface(text)
    for regex, relation in ((_MEMBER, "MEMBERSHIP"), (_SUBCLASS, "SUBCLASS")):
        m = regex.fullmatch(body)
        if not m:
            continue
        subject = _canon(m.group("subject"))
        obj = _canon(m.group("object"))
        if not subject or not obj:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EMPTY_RELATION_ARGUMENT", "claim_in_scope": True}
        positive = m.group("neg") is None
        return {
            "schema": SCHEMA,
            "status": "RESOLVED",
            "claim_in_scope": True,
            "relation_kind": relation,
            "positive": positive,
            "subject": subject,
            "object": obj,
            "source": source,
            "surface": body,
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED",
        "reason": "OUTSIDE_EXPLICIT_CATEGORICAL_GRAMMAR",
        "claim_in_scope": bool(_HINT.search(body)),
        "terminal_authority": False,
    }


def parse_categorical_claim(text: str) -> dict[str, Any]:
    return parse_categorical_statement(text)


def _path(
    edges: Mapping[str, Sequence[tuple[str, str]]],
    start: str,
    target: str,
) -> list[str] | None:
    if start == target:
        return []
    q = deque([(start, [])])
    seen = {start}
    while q:
        node, proof = q.popleft()
        for nxt, eid in sorted(edges.get(node, ()), key=lambda x: (x[0], x[1])):
            if nxt == target:
                return proof + [eid]
            if nxt in seen:
                continue
            seen.add(nxt)
            q.append((nxt, proof + [eid]))
    return None


def evaluate_support(claim_text: str, evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    claim = parse_categorical_claim(claim_text)
    if claim.get("status") != "RESOLVED":
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": "UNKNOWN",
            "claim_in_scope": bool(claim.get("claim_in_scope")),
            "reason": claim.get("reason"),
            "terminal_authority": False,
        }
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "relation": "UNKNOWN", "reason": "EVIDENCE_SEQUENCE_REQUIRED", "terminal_authority": False}

    parsed: list[dict[str, Any]] = []
    malformed: list[str] = []
    unrelated_ids: list[str] = []
    for i, row in enumerate(evidence):
        if not isinstance(row, Mapping):
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "relation": "UNKNOWN", "reason": f"EVIDENCE_ROW_INVALID:{i}", "terminal_authority": False}
        eid = row.get("evidence_id")
        text = row.get("text")
        if not isinstance(eid, str) or not eid.strip() or not isinstance(text, str) or not text.strip():
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "relation": "UNKNOWN", "reason": f"EVIDENCE_FIELDS_REQUIRED:{i}", "terminal_authority": False}
        out = parse_categorical_statement(text)
        if out.get("status") == "RESOLVED":
            parsed.append({**out, "evidence_id": eid})
        elif out.get("claim_in_scope") is True:
            malformed.append(eid)
        else:
            unrelated_ids.append(eid)

    if malformed:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": "UNKNOWN",
            "claim_in_scope": True,
            "reason": "CATEGORY_SHAPED_EVIDENCE_OUTSIDE_CHECKED_GRAMMAR",
            "unresolved_evidence_ids": sorted(malformed),
            "terminal_authority": False,
        }

    pos_edges: dict[str, list[tuple[str, str]]] = {}
    neg_subclass: list[tuple[str, str, str]] = []
    pos_members: list[tuple[str, str, str]] = []
    neg_members: list[tuple[str, str, str]] = []
    for row in parsed:
        a, b, eid = row["subject"], row["object"], row["evidence_id"]
        if row["relation_kind"] == "SUBCLASS":
            if row["positive"]:
                pos_edges.setdefault(a, []).append((b, eid))
            else:
                neg_subclass.append((a, b, eid))
        else:
            (pos_members if row["positive"] else neg_members).append((a, b, eid))

    support_paths: list[list[str]] = []
    conflict_paths: list[list[str]] = []
    kind = claim["relation_kind"]
    positive = bool(claim["positive"])
    a, b = claim["subject"], claim["object"]

    if kind == "SUBCLASS":
        path = _path(pos_edges, a, b)
        direct_negative = [[eid] for x, y, eid in neg_subclass if x == a and y == b]
        if positive:
            if path is not None and path:
                support_paths.append(path)
            conflict_paths.extend(direct_negative)
        else:
            support_paths.extend(direct_negative)
            if path is not None and path:
                conflict_paths.append(path)
    else:
        if positive:
            for entity, cls, eid in pos_members:
                if entity != a:
                    continue
                p = _path(pos_edges, cls, b)
                if cls == b:
                    p = []
                if p is not None:
                    support_paths.append([eid] + p)
            for entity, superclass, eid in neg_members:
                if entity != a:
                    continue
                p = _path(pos_edges, b, superclass)
                if b == superclass:
                    p = []
                if p is not None:
                    conflict_paths.append([eid] + p)
        else:
            for entity, superclass, eid in neg_members:
                if entity != a:
                    continue
                p = _path(pos_edges, b, superclass)
                if b == superclass:
                    p = []
                if p is not None:
                    support_paths.append([eid] + p)
            for entity, cls, eid in pos_members:
                if entity != a:
                    continue
                p = _path(pos_edges, cls, b)
                if cls == b:
                    p = []
                if p is not None:
                    conflict_paths.append([eid] + p)

    support_ids = sorted({eid for path in support_paths for eid in path})
    conflict_ids = sorted({eid for path in conflict_paths for eid in path})
    audit = []
    for eid in support_ids:
        audit.append({"evidence_id": eid, "relation": "SUPPORTS", "grammar": "EXPLICIT_CATEGORICAL_RELATION_V1"})
    for eid in conflict_ids:
        audit.append({"evidence_id": eid, "relation": "CONFLICTS", "grammar": "EXPLICIT_CATEGORICAL_RELATION_V1"})
    for eid in unrelated_ids:
        audit.append({"evidence_id": eid, "relation": "UNRELATED", "grammar": "NONCATEGORICAL_EVIDENCE"})
    audit.sort(key=lambda x: (x["evidence_id"], x["relation"], x["grammar"]))

    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "relation": (
            "BOTH" if support_ids and conflict_ids
            else "SUPPORTS" if support_ids
            else "CONFLICTS" if conflict_ids
            else "UNRELATED"
        ),
        "claim_in_scope": True,
        "claim": {
            "relation_kind": kind,
            "positive": positive,
            "subject": a,
            "object": b,
        },
        "support_evidence_ids": support_ids,
        "conflict_evidence_ids": conflict_ids,
        "support_proof_paths": sorted(support_paths),
        "conflict_proof_paths": sorted(conflict_paths),
        "relation_audit": audit,
        "terminal_authority": False,
        "scope": (
            "EXPLICIT_MEMBER_INSTANCE_SUBCLASS_SUBSET_GRAMMAR_ONLY__"
            "POSITIVE_SUBCLASS_TRANSITIVE_CLOSURE__POSITIVE_MEMBERSHIP_UPWARD__"
            "NEGATIVE_MEMBERSHIP_DOWNWARD__NO_CLOSED_WORLD_NEGATION_OR_LEXICAL_TAXONOMY"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    args = args or {}
    return evaluate_support(str(args.get("claim_text") or ""), args.get("evidence") or [])

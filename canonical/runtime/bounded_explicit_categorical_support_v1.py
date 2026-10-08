"""Bounded explicit categorical support v1.

Deterministic support for one deliberately narrow categorical surface:
- X is [not] a member of C
- X is [not] an instance of C
- A is [not] a subclass of B
- A is [not] a subset of B

Evidence may carry the same source prefixes already used by the bounded support
portfolio ("reports that", "states that", or "SOURCE: ...").

The checker performs only set-theoretically sound graph closure:
- subclass is transitive;
- membership propagates upward through subclass edges;
- explicit non-membership propagates downward from a superclass to its subclasses.

It does not infer synonyms, plurality, "every X is Y", lexical class identity,
disjointness, complement classes, closed-world negation, or world knowledge.
Anything outside the checked grammar remains unresolved.
"""
from __future__ import annotations

from collections import deque
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUNDED_EXPLICIT_CATEGORICAL_SUPPORT_V1"

_PREFIXES = (
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+that\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$", re.I),
)

_TERM = r"[A-Za-z][A-Za-z0-9_:' -]{0,160}?"
_MEMBER = re.compile(
    rf"^(?P<subject>{_TERM})\s+is\s+(?P<neg>not\s+)?(?:a\s+)?(?P<kind>member|instance)\s+of\s+(?P<category>{_TERM})$",
    re.I,
)
_SUBCLASS = re.compile(
    rf"^(?P<sub>{_TERM})\s+is\s+(?P<neg>not\s+)?(?:a\s+)?(?P<kind>subclass|subset)\s+of\s+(?P<super>{_TERM})$",
    re.I,
)

def _norm(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split()).casefold()

def parse_relation(text: str, *, default_source: str | None = None) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TEXT_REQUIRED"}

    raw = " ".join(text.strip().split())
    source = default_source
    body = raw
    for pattern in _PREFIXES:
        m = pattern.fullmatch(raw)
        if m:
            source = " ".join(m.group("source").split())
            body = m.group("body")
            break

    body = body.strip()
    if body.endswith("."):
        body = body[:-1].rstrip()

    m = _MEMBER.fullmatch(body)
    if m:
        subject = _term(m.group("subject"))
        category = _term(m.group("category"))
        if not subject or not category:
            return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "UNSAFE_OR_CONTEXT_DEPENDENT_CATEGORICAL_TERM", "claim_in_scope": False, "terminal_authority": False}
        return {
            "schema": SCHEMA,
            "status": "RESOLVED",
            "claim_in_scope": True,
            "relation_type": "NOT_MEMBER" if m.group("neg") else "MEMBER",
            "subject": subject,
            "category": category,
            "source": source,
            "source_text": raw,
            "terminal_authority": False,
        }

    m = _SUBCLASS.fullmatch(body)
    if m:
        sub = _term(m.group("sub"))
        sup = _term(m.group("super"))
        if not sub or not sup:
            return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "UNSAFE_OR_CONTEXT_DEPENDENT_CATEGORICAL_TERM", "claim_in_scope": False, "terminal_authority": False}
        return {
            "schema": SCHEMA,
            "status": "RESOLVED",
            "claim_in_scope": True,
            "relation_type": "NOT_SUBCLASS" if m.group("neg") else "SUBCLASS",
            "subclass": sub,
            "superclass": sup,
            "source": source,
            "source_text": raw,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED",
        "reason": "OUTSIDE_EXPLICIT_CATEGORICAL_GRAMMAR",
        "claim_in_scope": False,
        "terminal_authority": False,
    }

def _shortest_path(
    edges: Mapping[str, list[tuple[str, str]]],
    start: str,
    target: str,
) -> list[str] | None:
    if start == target:
        return []
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        node, proof = queue.popleft()
        for nxt, evidence_id in sorted(edges.get(node, []), key=lambda x: (x[0], x[1])):
            if nxt in seen:
                continue
            new_proof = proof + [evidence_id]
            if nxt == target:
                return new_proof
            seen.add(nxt)
            queue.append((nxt, new_proof))
    return None

def _all_reachable_with_paths(
    edges: Mapping[str, list[tuple[str, str]]],
    start: str,
) -> dict[str, list[str]]:
    out = {start: []}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        base = out[node]
        for nxt, evidence_id in sorted(edges.get(node, []), key=lambda x: (x[0], x[1])):
            if nxt in out:
                continue
            out[nxt] = base + [evidence_id]
            queue.append(nxt)
    return out

def classify_support(
    claim_text: str,
    evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    claim = parse_relation(claim_text, default_source="CLAIM")
    if claim.get("status") != "RESOLVED":
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": "UNKNOWN",
            "claim_in_scope": False,
            "reason": claim.get("reason"),
            "terminal_authority": False,
        }
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "relation": "UNKNOWN",
            "claim_in_scope": True,
            "reason": "EVIDENCE_SEQUENCE_REQUIRED",
            "terminal_authority": False,
        }

    parsed: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    pos_member: list[tuple[str, str, str]] = []
    neg_member: list[tuple[str, str, str]] = []
    subclass_edges: dict[str, list[tuple[str, str]]] = {}
    neg_subclass: set[tuple[str, str, str]] = set()

    seen: set[str] = set()
    for i, row in enumerate(evidence):
        if not isinstance(row, Mapping):
            return {
                "schema": SCHEMA, "status": "FAIL_CLOSED", "relation": "UNKNOWN",
                "claim_in_scope": True, "reason": f"EVIDENCE_ROW_INVALID:{i}",
                "terminal_authority": False,
            }
        eid = row.get("evidence_id")
        text = row.get("text")
        if not isinstance(eid, str) or not eid.strip() or eid in seen:
            return {
                "schema": SCHEMA, "status": "FAIL_CLOSED", "relation": "UNKNOWN",
                "claim_in_scope": True, "reason": "EVIDENCE_ID_INVALID_OR_DUPLICATE",
                "terminal_authority": False,
            }
        seen.add(eid)
        out = parse_relation(text, default_source=eid)
        if out.get("status") != "RESOLVED":
            unresolved.append(eid)
            continue
        parsed[eid] = out
        typ = out["relation_type"]
        if typ == "MEMBER":
            pos_member.append((out["subject"], out["category"], eid))
        elif typ == "NOT_MEMBER":
            neg_member.append((out["subject"], out["category"], eid))
        elif typ == "SUBCLASS":
            subclass_edges.setdefault(out["subclass"], []).append((out["superclass"], eid))
        else:
            neg_subclass.add((out["subclass"], out["superclass"], eid))

    support_paths: list[list[str]] = []
    conflict_paths: list[list[str]] = []
    ctype = claim["relation_type"]

    if ctype == "MEMBER":
        subject, target = claim["subject"], claim["category"]
        for s, category, eid in pos_member:
            if s != subject:
                continue
            path = _shortest_path(subclass_edges, category, target)
            if path is not None:
                support_paths.append([eid] + path)
        target_supers = _all_reachable_with_paths(subclass_edges, target)
        for s, category, eid in neg_member:
            if s == subject and category in target_supers:
                conflict_paths.append([eid] + target_supers[category])

    elif ctype == "NOT_MEMBER":
        subject, target = claim["subject"], claim["category"]
        target_supers = _all_reachable_with_paths(subclass_edges, target)
        for s, category, eid in neg_member:
            if s == subject and category in target_supers:
                support_paths.append([eid] + target_supers[category])
        for s, category, eid in pos_member:
            if s != subject:
                continue
            path = _shortest_path(subclass_edges, category, target)
            if path is not None:
                conflict_paths.append([eid] + path)

    elif ctype in ("SUBCLASS", "NOT_SUBCLASS"):
        sub, sup = claim["subclass"], claim["superclass"]
        # A strict non-inclusion of a class in itself is impossible.
        if ctype == "NOT_SUBCLASS" and sub == sup:
            return {
                "schema": SCHEMA, "status": "UNRESOLVED",
                "relation": "UNKNOWN", "claim_in_scope": True,
                "reason": "SELF_NOT_SUBCLASS_CONTRADICTS_SET_SEMANTICS",
                "terminal_authority": False,
            }
        positive_path = _shortest_path(subclass_edges, sub, sup)
        negative_paths = []
        for a, b, eid in neg_subclass:
            # A !subset B, A subset X, Y subset B imply X !subset Y.
            # Every contributing edge is retained in the proof path.
            left = _shortest_path(subclass_edges, a, sub)
            right = _shortest_path(subclass_edges, sup, b)
            if left is not None and right is not None:
                negative_paths.append(left + [eid] + right)
        if ctype == "SUBCLASS":
            if positive_path is not None:
                support_paths.append(positive_path)
            conflict_paths.extend(negative_paths)
        else:
            support_paths.extend(negative_paths)
            if positive_path is not None:
                conflict_paths.append(positive_path)

    def _best(paths: list[list[str]]) -> list[str]:
        if not paths:
            return []
        return min((list(dict.fromkeys(p)) for p in paths), key=lambda p: (len(p), tuple(p)))

    support_ids = _best(support_paths)
    conflict_ids = _best(conflict_paths)
    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "relation": (
            "SUPPORTS" if support_ids and not conflict_ids
            else "CONFLICTS" if conflict_ids and not support_ids
            else "BOTH" if support_ids and conflict_ids
            else "UNRELATED"
        ),
        "claim_in_scope": True,
        "claim": claim,
        "parsed_evidence_ids": sorted(parsed),
        "unresolved_evidence_ids": sorted(unresolved),
        "support_evidence_ids": support_ids,
        "conflict_evidence_ids": conflict_ids,
        "support_proof_paths": sorted(support_paths, key=lambda p: (len(p), tuple(p))),
        "conflict_proof_paths": sorted(conflict_paths, key=lambda p: (len(p), tuple(p))),
        "terminal_authority": False,
        "scope": (
            "EXPLICIT_MEMBER_INSTANCE_SUBCLASS_SUBSET_RELATIONS_ONLY__"
            "TRANSITIVE_SUBCLASS__UPWARD_POSITIVE_MEMBERSHIP__"
            "DOWNWARD_EXPLICIT_NONMEMBERSHIP__NO_CLOSED_WORLD_OR_LEXICAL_ONTOLOGY"
        ),
    }

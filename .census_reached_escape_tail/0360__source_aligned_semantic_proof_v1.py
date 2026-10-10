"""Source-aligned proof checker for a tiny explicit-semantic fragment.

Untrusted callers may propose operator facts. This checker recomputes the
operators from the exact source and accepts only claims matching the Brain-owned
deterministic recognizer. Accepted claims are emitted as canonical semantic
constraint atoms suitable for the monotone semantic constraint kernel.

This module intentionally proves very little. Incompleteness is safe; an
unproved semantic claim simply remains absent. It has no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime.semantic_operator_counterfactuals import extract_semantic_operators
from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V1"


def _operator_class_atom(operator_id: str, semantic_class: str) -> str:
    return f"OPERATOR_CLASS::{operator_id}::{semantic_class}"


def _operator_bound_atom(operator_id: str, semantic_class: str, bound_value: float) -> str:
    return f"OPERATOR_BOUND::{operator_id}::{semantic_class}::{bound_value!r}"


def _literal_atom(source_id: str, start: int, end: int, digest: str) -> str:
    return f"SOURCE_LITERAL::{source_id}::{start}:{end}::{digest}"


def _scope_relation_atom(parsed: Mapping[str, Any]) -> str:
    return (
        "SCOPE_RELATION::"
        f"{parsed['scope_id']}::{parsed['relation']}::"
        f"{parsed['left_role']}:{parsed['left_text_sha256']}::"
        f"{parsed['right_role']}:{parsed['right_text_sha256']}"
    )


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(source_text, str) or not source_text:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"], "terminal_authority": False}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_ID_MISSING"], "terminal_authority": False}
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["CLAIMS_INVALID"], "terminal_authority": False}

    operators = extract_semantic_operators(source_text, source=source_id)
    by_id = {op.operator_id: op for op in operators}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_claim_ids: set[str] = set()

    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen_claim_ids:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}")
            continue
        seen_claim_ids.add(cid)

        kind = claim.get("kind")
        if kind == "OPERATOR_CLASS":
            oid = str(claim.get("operator_id") or "")
            cls = str(claim.get("semantic_class") or "")
            op = by_id.get(oid)
            if op is None:
                rejected.append({"claim_id": cid, "reason": "UNKNOWN_OPERATOR_ID"})
                continue
            if cls != op.semantic_class:
                rejected.append({
                    "claim_id": cid,
                    "reason": "OPERATOR_CLASS_MISMATCH",
                    "expected": op.semantic_class,
                    "claimed": cls,
                })
                continue
            accepted.append({
                "claim_id": cid,
                "kind": kind,
                "operator_id": oid,
                "semantic_class": cls,
                "source_span": [op.start, op.end],
                "source_text": op.text,
                "constraint": {"op": "ATOM", "id": _operator_class_atom(oid, cls)},
            })

        elif kind == "OPERATOR_BOUND":
            oid = str(claim.get("operator_id") or "")
            cls = str(claim.get("semantic_class") or "")
            op = by_id.get(oid)
            if op is None:
                rejected.append({"claim_id": cid, "reason": "UNKNOWN_OPERATOR_ID"})
                continue
            if cls != op.semantic_class:
                rejected.append({"claim_id": cid, "reason": "OPERATOR_CLASS_MISMATCH"})
                continue
            if op.bound_value is None:
                rejected.append({"claim_id": cid, "reason": "OPERATOR_HAS_NO_NUMERIC_BOUND"})
                continue
            try:
                bound = float(claim.get("bound_value"))
            except (TypeError, ValueError):
                rejected.append({"claim_id": cid, "reason": "BOUND_VALUE_INVALID"})
                continue
            if bound != op.bound_value:
                rejected.append({
                    "claim_id": cid,
                    "reason": "BOUND_VALUE_MISMATCH",
                    "expected": op.bound_value,
                    "claimed": bound,
                })
                continue
            accepted.append({
                "claim_id": cid,
                "kind": kind,
                "operator_id": oid,
                "semantic_class": cls,
                "bound_value": op.bound_value,
                "source_span": [op.start, op.end],
                "source_text": op.text,
                "constraint": {
                    "op": "ATOM",
                    "id": _operator_bound_atom(oid, cls, op.bound_value),
                },
            })

        elif kind == "SCOPE_RELATION":
            scoped = parse_scope(source_text, source=source_id)
            if scoped.get("status") != "PARSED":
                rejected.append({
                    "claim_id": cid,
                    "reason": "SCOPE_NOT_CERTIFIABLY_PARSED",
                    "scope_status": scoped.get("status"),
                    "scope_reason": scoped.get("reason"),
                })
                continue
            parsed = scoped["parse"]
            checks = {
                "scope_id": str(claim.get("scope_id") or ""),
                "relation": str(claim.get("relation") or ""),
                "left_role": str(claim.get("left_role") or ""),
                "right_role": str(claim.get("right_role") or ""),
                "left_text_sha256": str(claim.get("left_text_sha256") or ""),
                "right_text_sha256": str(claim.get("right_text_sha256") or ""),
            }
            expected = {k: str(parsed[k]) for k in checks}
            mismatch = [k for k in checks if checks[k] != expected[k]]
            if mismatch:
                rejected.append({
                    "claim_id": cid,
                    "reason": "SCOPE_RELATION_MISMATCH",
                    "mismatch_fields": mismatch,
                    "expected": expected,
                    "claimed": checks,
                })
                continue
            accepted.append({
                "claim_id": cid,
                "kind": kind,
                **expected,
                "left_span": list(parsed["left_span"]),
                "right_span": list(parsed["right_span"]),
                "operator_span": list(parsed["operator_span"]),
                "constraint": {"op": "ATOM", "id": _scope_relation_atom(parsed)},
            })

        elif kind == "SOURCE_LITERAL":
            start = claim.get("start")
            end = claim.get("end")
            if (
                not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or start < 0 or end <= start or end > len(source_text)
            ):
                rejected.append({"claim_id": cid, "reason": "SOURCE_SPAN_INVALID"})
                continue
            actual = source_text[start:end]
            digest = sha256(actual.encode("utf-8")).hexdigest()
            claimed_digest = str(claim.get("text_sha256") or "")
            if claimed_digest != digest:
                rejected.append({"claim_id": cid, "reason": "SOURCE_LITERAL_HASH_MISMATCH"})
                continue
            accepted.append({
                "claim_id": cid,
                "kind": kind,
                "source_span": [start, end],
                "source_text": actual,
                "text_sha256": digest,
                "constraint": {
                    "op": "ATOM",
                    "id": _literal_atom(source_id, start, end, digest),
                },
            })

        else:
            rejected.append({"claim_id": cid, "reason": f"CLAIM_KIND_UNSUPPORTED:{kind}"})

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "accepted_claims": [],
            "rejected_claims": rejected,
            "terminal_authority": False,
        }

    constraints = [row["constraint"] for row in accepted]
    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "recognized_operator_count": len(operators),
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": constraints,
        "proved_constraint_ids": [c["id"] for c in constraints],
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_EXACT_SOURCE_LITERALS_EXPLICIT_OPERATOR_CLASS_OR_BOUND_FACTS_AND_CERTIFIED_SCOPE_RELATIONS_ARE_PROVED;"
            "ARGUMENT_SCOPE_REFERENCE_RESOLUTION_DOMAIN_MEANING_AND_POLICY_ADEQUACY_ARE_NOT_PROVED"
        ),
    }

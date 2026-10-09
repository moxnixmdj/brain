"""Exact bounded semantic-relation proof kernel V1.

This kernel proves only extensional relations on a caller-bound finite semantic
universe. It is intentionally stronger than lexical similarity and weaker than
open-world linguistic identity.

If the universe and both denotations are complete for the declared scope, set
relations are exact:
  left == right       -> logical equivalence in scope
  left subset right   -> LEFT_ENTAILS_RIGHT
  right subset left   -> RIGHT_ENTAILS_LEFT
  witnesses           -> corresponding entailment/equivalence is disproved

The evidence package is content-addressed. Its factual/ontology authority is
separate and is not self-authenticated by this checker.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUNDED_SEMANTIC_RELATION_PROOF_V1"
EVIDENCE_SCHEMA = "PROJECT_BRAIN_BOUNDED_SEMANTIC_RELATION_EVIDENCE_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def evidence_sha256(value: Mapping[str, Any]) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "semantic_truth_authority": False,
        "source_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _str_set(value: Any, label: str) -> tuple[set[str] | None, str | None]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None, label + "_NOT_SEQUENCE"
    out: set[str] = set()
    for i, raw in enumerate(value):
        if not isinstance(raw, str) or not raw.strip():
            return None, f"{label}_ITEM_INVALID:{i}"
        item = raw.strip()
        if item in out:
            return None, f"{label}_DUPLICATE:{item}"
        out.add(item)
    return out, None


def prove(
    evidence: Mapping[str, Any],
    *,
    expected_evidence_sha256: str,
) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        return _fail("EVIDENCE_SCHEMA_INVALID")
    if _SHA256.fullmatch(str(expected_evidence_sha256 or "")) is None:
        return _fail("EXPECTED_EVIDENCE_SHA256_INVALID")

    actual_sha = evidence_sha256(evidence)
    if actual_sha != expected_evidence_sha256:
        return _fail(
            "EVIDENCE_CONTENT_ADDRESS_MISMATCH",
            expected_evidence_sha256=expected_evidence_sha256,
            actual_evidence_sha256=actual_sha,
        )

    scope_id = str(evidence.get("scope_id") or "").strip()
    left_id = str(evidence.get("left_id") or "").strip()
    right_id = str(evidence.get("right_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")
    if not left_id or not right_id or left_id == right_id:
        return _fail("DISTINCT_LEFT_RIGHT_IDS_REQUIRED")

    if evidence.get("universe_complete") is not True:
        return _fail("UNIVERSE_COMPLETENESS_UNPROVED")
    if evidence.get("left_extension_complete") is not True:
        return _fail("LEFT_EXTENSION_COMPLETENESS_UNPROVED")
    if evidence.get("right_extension_complete") is not True:
        return _fail("RIGHT_EXTENSION_COMPLETENESS_UNPROVED")

    universe, err = _str_set(evidence.get("universe"), "UNIVERSE")
    if err:
        return _fail(err)
    left, err = _str_set(evidence.get("left_members"), "LEFT_MEMBERS")
    if err:
        return _fail(err)
    right, err = _str_set(evidence.get("right_members"), "RIGHT_MEMBERS")
    if err:
        return _fail(err)
    assert universe is not None and left is not None and right is not None

    if not left <= universe:
        return _fail(
            "LEFT_EXTENSION_OUTSIDE_UNIVERSE",
            offending=sorted(left - universe),
        )
    if not right <= universe:
        return _fail(
            "RIGHT_EXTENSION_OUTSIDE_UNIVERSE",
            offending=sorted(right - universe),
        )

    left_not_right = sorted(left - right)
    right_not_left = sorted(right - left)
    intersection = sorted(left & right)

    left_entails_right = not left_not_right
    right_entails_left = not right_not_left
    equivalent = left_entails_right and right_entails_left
    disjoint = not intersection

    if equivalent:
        strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
    elif left_entails_right:
        strongest = "LEFT_ENTAILS_RIGHT"
    elif right_entails_left:
        strongest = "RIGHT_ENTAILS_LEFT"
    elif disjoint:
        strongest = "DISJOINT"
    else:
        strongest = "PARTIAL_OVERLAP_OR_INCOMPARABLE"

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_BOUNDED_EXTENSION_RELATION_PROVED",
        "pass": True,
        "scope_id": scope_id,
        "left_id": left_id,
        "right_id": right_id,
        "evidence_sha256": actual_sha,
        "strongest_proved_relation": strongest,
        "logical_equivalence_in_scope": equivalent,
        "left_entails_right": left_entails_right,
        "right_entails_left": right_entails_left,
        "left_entails_right_disproved": bool(left_not_right),
        "right_entails_left_disproved": bool(right_not_left),
        "logical_equivalence_disproved": bool(left_not_right or right_not_left),
        "left_not_right_witnesses": left_not_right,
        "right_not_left_witnesses": right_not_left,
        "intersection_members": intersection,
        "universe_size": len(universe),
        "left_extension_size": len(left),
        "right_extension_size": len(right),
        "semantic_truth_authority": False,
        "source_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "theorem_boundary": (
            "EXACT_ONLY_IF_THE_DECLARED_UNIVERSE_AND_BOTH_DENOTATION_EXTENSIONS_"
            "ARE_COMPLETE_AND_AUTHENTIC_FOR_THE_BOUND_SCOPE"
        ),
    }

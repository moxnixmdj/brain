"""Scoped semantic entailment DAG proof kernel V1.

This kernel closes a gap between:
- exact explicit/source identity, and
- exact finite complete-denotation set proofs.

It can prove directional entailment or scoped logical equivalence from a graph of
independently authenticated local entailment edges without requiring a complete
open-world denotation universe.

The checker itself never authenticates lexical/model output. Every load-bearing
edge or counterexample must pass the caller-provided authority verifier and bind
the exact scope, endpoint ids, relation kind, and content-addressed evidence.

Sound rules in V1:
  A entails B, B entails C  => A entails C
  A entails B, B entails A  => A and B are logically equivalent in scope
  authenticated NOT_ENTAILS(A,B) disproves A entails B

If a proved entailment path conflicts with an authenticated counterexample, the
evidence set fails closed.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SCOPED_SEMANTIC_ENTAILMENT_DAG_PROOF_V1"
EVIDENCE_SCHEMA = "PROJECT_BRAIN_SCOPED_SEMANTIC_ENTAILMENT_DAG_EVIDENCE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_RECEIPT_V1"
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
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _verify_receipt(
    raw: Any,
    *,
    scope_id: str,
    relation: str,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, Mapping) or not callable(verifier):
        return None, "RELATION_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(raw)))
    if not isinstance(out, Mapping):
        return None, "RELATION_VERIFIER_RETURNED_NO_RECEIPT"
    out = deepcopy(dict(out))

    source_id = str(out.get("source_id") or "").strip()
    target_id = str(out.get("target_id") or "").strip()
    required = {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "scope_id": scope_id,
        "relation": relation,
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
    }
    bad = [key for key, value in required.items() if out.get(key) != value]
    if not source_id or not target_id or source_id == target_id:
        bad.append("source_id_or_target_id")
    for key in ("evidence_sha256", "receipt_sha256"):
        if _SHA256.fullmatch(str(out.get(key) or "")) is None:
            bad.append(key)
    if bad:
        return None, "RELATION_RECEIPT_BINDING_INVALID:" + ",".join(sorted(set(bad)))
    return out, None


def _path(
    adjacency: Mapping[str, set[str]],
    start: str,
    target: str,
) -> list[str] | None:
    if start == target:
        return [start]
    queue = deque([start])
    prior: dict[str, str | None] = {start: None}
    while queue:
        cur = queue.popleft()
        for nxt in sorted(adjacency.get(cur, set())):
            if nxt in prior:
                continue
            prior[nxt] = cur
            if nxt == target:
                rev = [target]
                node: str | None = target
                while node is not None and prior[node] is not None:
                    node = prior[node]
                    assert node is not None
                    rev.append(node)
                return list(reversed(rev))
            queue.append(nxt)
    return None


def _closure_pairs(adjacency: Mapping[str, set[str]]) -> set[tuple[str, str]]:
    nodes = set(adjacency)
    for values in adjacency.values():
        nodes.update(values)
    pairs: set[tuple[str, str]] = set()
    for source in nodes:
        queue = deque([source])
        seen = {source}
        while queue:
            cur = queue.popleft()
            for nxt in adjacency.get(cur, set()):
                if nxt in seen:
                    continue
                seen.add(nxt)
                pairs.add((source, nxt))
                queue.append(nxt)
    return pairs


def prove(
    evidence: Mapping[str, Any],
    *,
    expected_evidence_sha256: str,
    relation_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
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

    edge_rows = evidence.get("entailment_receipts", [])
    counter_rows = evidence.get("counterexample_receipts", [])
    if not isinstance(edge_rows, Sequence) or isinstance(edge_rows, (str, bytes)):
        return _fail("ENTAILMENT_RECEIPTS_NOT_SEQUENCE")
    if not isinstance(counter_rows, Sequence) or isinstance(counter_rows, (str, bytes)):
        return _fail("COUNTEREXAMPLE_RECEIPTS_NOT_SEQUENCE")

    adjacency: dict[str, set[str]] = {}
    accepted_edges: list[dict[str, Any]] = []
    disproved_pairs: set[tuple[str, str]] = set()
    accepted_counterexamples: list[dict[str, Any]] = []

    for i, raw in enumerate(edge_rows):
        receipt, error = _verify_receipt(
            raw,
            scope_id=scope_id,
            relation="ENTAILS",
            verifier=relation_verifier,
        )
        if error is not None or receipt is None:
            return _fail("ENTAILMENT_RECEIPT_INVALID:" + str(i) + ":" + str(error))
        source = str(receipt["source_id"])
        target = str(receipt["target_id"])
        adjacency.setdefault(source, set()).add(target)
        accepted_edges.append(receipt)

    for i, raw in enumerate(counter_rows):
        receipt, error = _verify_receipt(
            raw,
            scope_id=scope_id,
            relation="NOT_ENTAILS",
            verifier=relation_verifier,
        )
        if error is not None or receipt is None:
            return _fail("COUNTEREXAMPLE_RECEIPT_INVALID:" + str(i) + ":" + str(error))
        pair = (str(receipt["source_id"]), str(receipt["target_id"]))
        disproved_pairs.add(pair)
        accepted_counterexamples.append(receipt)

    closure = _closure_pairs(adjacency)
    conflicts = sorted([list(pair) for pair in closure & disproved_pairs])
    if conflicts:
        return _fail(
            "CONTRADICTORY_ENTAILMENT_AND_COUNTEREXAMPLE_EVIDENCE",
            conflicting_pairs=conflicts,
        )

    left_path = _path(adjacency, left_id, right_id)
    right_path = _path(adjacency, right_id, left_id)
    left_entails = left_path is not None
    right_entails = right_path is not None
    left_disproved = (left_id, right_id) in disproved_pairs
    right_disproved = (right_id, left_id) in disproved_pairs

    if left_entails and right_entails:
        strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
    elif left_entails:
        strongest = "LEFT_ENTAILS_RIGHT"
    elif right_entails:
        strongest = "RIGHT_ENTAILS_LEFT"
    else:
        strongest = "UNKNOWN"

    return {
        "schema": SCHEMA,
        "status": "PASS__SCOPED_ENTAILMENT_DAG_CHECKED",
        "pass": True,
        "scope_id": scope_id,
        "left_id": left_id,
        "right_id": right_id,
        "evidence_sha256": actual_sha,
        "strongest_proved_relation": strongest,
        "logical_equivalence_in_scope": left_entails and right_entails,
        "left_entails_right": left_entails,
        "right_entails_left": right_entails,
        "left_entails_right_disproved": left_disproved,
        "right_entails_left_disproved": right_disproved,
        "logical_equivalence_disproved": left_disproved or right_disproved,
        "left_to_right_path": left_path,
        "right_to_left_path": right_path,
        "accepted_entailment_edge_count": len(accepted_edges),
        "accepted_counterexample_count": len(accepted_counterexamples),
        "semantic_truth_authority": False,
        "source_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "theorem_boundary": (
            "EXACT_ONLY_RELATIVE_TO_INDEPENDENTLY_AUTHENTICATED_SCOPED_ENTAILMENT_"
            "AND_COUNTEREXAMPLE_RECEIPTS__NO_COMPLETE_OPEN_WORLD_DENOTATION_REQUIRED"
        ),
    }

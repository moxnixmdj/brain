"""Decision-relative proof-carrying semantic relation control V1.

The goal is not global synonym detection. The goal is to derive the weakest sound
semantic relation sufficient for the current task while refusing false merges.

Candidate generators (embeddings, LLMs, lexical similarity, thesauri) have zero
semantic authority. Positive relations are admitted only from checked,
content-addressed proof records or from exact complete terminal signatures.

Supported proof facts:
- EXPLICIT_SCOPED_EQUIVALENCE
- SAME_AUTHORITY_CONCEPT_ID
- LEFT_ENTAILS_RIGHT
- RIGHT_ENTAILS_LEFT

Supported counterexamples:
- IDENTITY_COUNTEREXAMPLE
- LEFT_ENTAILMENT_COUNTEREXAMPLE
- RIGHT_ENTAILMENT_COUNTEREXAMPLE
- TERMINAL_SUBSTITUTION_COUNTEREXAMPLE

Task-relative substitution is established independently by equality of complete
terminal signatures, using the Brain's existing terminal semantic quotient.

No proof here grants execution, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.terminal_semantic_quotient_v1 import compile_minimal_quotient

SCHEMA = "PROJECT_BRAIN_DECISION_RELATIVE_SEMANTIC_RELATION_CONTROL_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

POSITIVE_KINDS = {
    "EXPLICIT_SCOPED_EQUIVALENCE",
    "SAME_AUTHORITY_CONCEPT_ID",
    "LEFT_ENTAILS_RIGHT",
    "RIGHT_ENTAILS_LEFT",
}
NEGATIVE_KINDS = {
    "IDENTITY_COUNTEREXAMPLE",
    "LEFT_ENTAILMENT_COUNTEREXAMPLE",
    "RIGHT_ENTAILMENT_COUNTEREXAMPLE",
    "TERMINAL_SUBSTITUTION_COUNTEREXAMPLE",
}
REQUIRED_RELATIONS = {
    "SEMANTIC_IDENTITY",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
    "LEFT_ENTAILS_RIGHT",
    "RIGHT_ENTAILS_LEFT",
    "CURRENT_DECISION_SUBSTITUTION",
}


class SemanticRelationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _valid_sha(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "")))


def make_proof_record(
    *,
    kind: str,
    scope_id: str,
    verifier_id: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Helper for tests/tools. Verification still recomputes the digest."""
    payload = {
        "kind": str(kind),
        "scope_id": str(scope_id),
        "verified": True,
        "verifier_id": str(verifier_id),
        "evidence": deepcopy(dict(evidence)),
        "verification_authority_mutated": False,
    }
    payload["evidence_sha256"] = _sha(payload["evidence"])
    payload["proof_sha256"] = _sha(payload)
    return payload


def _proof_ok(
    row: Any,
    *,
    expected_scope: str,
    allowed_kinds: set[str],
) -> tuple[bool, str | None]:
    if not isinstance(row, Mapping):
        return False, "PROOF_RECORD_NOT_OBJECT"
    kind = str(row.get("kind") or "")
    if kind not in allowed_kinds:
        return False, "PROOF_KIND_INVALID:" + kind
    if str(row.get("scope_id") or "") != expected_scope:
        return False, "PROOF_SCOPE_MISMATCH:" + kind
    if row.get("verified") is not True:
        return False, "PROOF_NOT_VERIFIED:" + kind
    if row.get("verification_authority_mutated") is not False:
        return False, "PROOF_AUTHORITY_MUTATED:" + kind
    verifier_id = str(row.get("verifier_id") or "").strip()
    if not verifier_id:
        return False, "PROOF_VERIFIER_ID_REQUIRED:" + kind
    evidence = row.get("evidence")
    if not isinstance(evidence, Mapping):
        return False, "PROOF_EVIDENCE_REQUIRED:" + kind
    evidence_sha = str(row.get("evidence_sha256") or "")
    proof_sha = str(row.get("proof_sha256") or "")
    if not _valid_sha(evidence_sha) or evidence_sha != _sha(evidence):
        return False, "PROOF_EVIDENCE_DIGEST_INVALID:" + kind
    core = {str(k): deepcopy(v) for k, v in row.items() if str(k) != "proof_sha256"}
    if not _valid_sha(proof_sha) or proof_sha != _sha(core):
        return False, "PROOF_DIGEST_INVALID:" + kind
    return True, None


def _terminal_equivalence(
    left_id: str,
    right_id: str,
    terminal_rows: Any,
) -> dict[str, Any]:
    if terminal_rows is None:
        return {
            "available": False,
            "proved": False,
            "reason": "NO_TERMINAL_SIGNATURE_ROWS",
        }
    if not isinstance(terminal_rows, Sequence) or isinstance(
        terminal_rows, (str, bytes)
    ):
        return {
            "available": True,
            "proved": False,
            "reason": "TERMINAL_SIGNATURE_ROWS_INVALID",
        }
    rows = [deepcopy(dict(x)) for x in terminal_rows if isinstance(x, Mapping)]
    if len(rows) != len(terminal_rows):
        return {
            "available": True,
            "proved": False,
            "reason": "TERMINAL_SIGNATURE_ROW_INVALID",
        }
    ids = [str(x.get("raw_id") or "") for x in rows]
    if set(ids) != {left_id, right_id} or len(ids) != 2:
        return {
            "available": True,
            "proved": False,
            "reason": "TERMINAL_SIGNATURE_DOMAIN_MUST_BE_EXACT_PAIR",
        }
    quotient = compile_minimal_quotient(rows)
    if quotient.get("pass") is not True:
        return {
            "available": True,
            "proved": False,
            "reason": str(quotient.get("reason") or quotient.get("status") or "UNKNOWN"),
            "quotient": quotient,
        }
    same = quotient["raw_to_class"][left_id] == quotient["raw_to_class"][right_id]
    return {
        "available": True,
        "proved": same,
        "reason": (
            "COMPLETE_TERMINAL_SIGNATURES_EQUAL"
            if same
            else "COMPLETE_TERMINAL_SIGNATURES_DIFFER"
        ),
        "quotient": quotient,
    }


def _relation_satisfies(
    required: str,
    *,
    semantic_identity: bool,
    logical_equivalence: bool,
    left_entails_right: bool,
    right_entails_left: bool,
    task_equivalent: bool,
) -> bool:
    if required == "SEMANTIC_IDENTITY":
        return semantic_identity
    if required == "LOGICAL_EQUIVALENCE_IN_SCOPE":
        return semantic_identity or logical_equivalence
    if required == "LEFT_ENTAILS_RIGHT":
        return semantic_identity or logical_equivalence or left_entails_right
    if required == "RIGHT_ENTAILS_LEFT":
        return semantic_identity or logical_equivalence or right_entails_left
    if required == "CURRENT_DECISION_SUBSTITUTION":
        return semantic_identity or logical_equivalence or task_equivalent
    return False


def resolve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PROBLEM_NOT_OBJECT",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    allowed = {
        "left_id",
        "right_id",
        "scope_id",
        "required_relation",
        "proof_records",
        "terminal_signature_rows",
        "candidate_relations",
    }
    extra = set(problem) - allowed
    if extra:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    left_id = str(problem.get("left_id") or "").strip()
    right_id = str(problem.get("right_id") or "").strip()
    scope_id = str(problem.get("scope_id") or "").strip()
    required = str(problem.get("required_relation") or "").strip().upper()
    if not left_id or not right_id or left_id == right_id:
        raise SemanticRelationError("DISTINCT_LEFT_RIGHT_IDS_REQUIRED")
    if not scope_id:
        raise SemanticRelationError("SCOPE_ID_REQUIRED")
    if required not in REQUIRED_RELATIONS:
        raise SemanticRelationError("REQUIRED_RELATION_INVALID")

    raw_records = problem.get("proof_records", [])
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
        raise SemanticRelationError("PROOF_RECORDS_NOT_SEQUENCE")

    records: list[Mapping[str, Any]] = []
    for i, row in enumerate(raw_records):
        ok, reason = _proof_ok(
            row,
            expected_scope=scope_id,
            allowed_kinds=POSITIVE_KINDS | NEGATIVE_KINDS,
        )
        if not ok:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__INVALID_PROOF_RECORD",
                "reason": f"{i}:{reason}",
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        records.append(row)

    kinds = {str(x["kind"]) for x in records}
    explicit_eq = "EXPLICIT_SCOPED_EQUIVALENCE" in kinds
    same_concept = "SAME_AUTHORITY_CONCEPT_ID" in kinds
    l2r = "LEFT_ENTAILS_RIGHT" in kinds
    r2l = "RIGHT_ENTAILS_LEFT" in kinds

    identity_counter = "IDENTITY_COUNTEREXAMPLE" in kinds
    l2r_counter = "LEFT_ENTAILMENT_COUNTEREXAMPLE" in kinds
    r2l_counter = "RIGHT_ENTAILMENT_COUNTEREXAMPLE" in kinds
    terminal_counter = "TERMINAL_SUBSTITUTION_COUNTEREXAMPLE" in kinds

    conflicts = []
    if (explicit_eq or same_concept) and identity_counter:
        conflicts.append("IDENTITY_POSITIVE_AND_COUNTEREXAMPLE")
    if l2r and l2r_counter:
        conflicts.append("LEFT_ENTAILMENT_POSITIVE_AND_COUNTEREXAMPLE")
    if r2l and r2l_counter:
        conflicts.append("RIGHT_ENTAILMENT_POSITIVE_AND_COUNTEREXAMPLE")

    terminal = _terminal_equivalence(
        left_id,
        right_id,
        problem.get("terminal_signature_rows"),
    )
    if terminal.get("proved") is True and terminal_counter:
        conflicts.append("TERMINAL_EQUIVALENCE_AND_COUNTEREXAMPLE")

    if conflicts:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__SEMANTIC_EVIDENCE_CONFLICT",
            "reason": conflicts,
            "required_relation": required,
            "scope_id": scope_id,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    semantic_identity = (explicit_eq or same_concept) and not identity_counter
    # Identity entails both directions within the bound scope.
    left_entails_right = semantic_identity or (l2r and not l2r_counter)
    right_entails_left = semantic_identity or (r2l and not r2l_counter)
    logical_equivalence = (
        left_entails_right
        and right_entails_left
        and not l2r_counter
        and not r2l_counter
    )
    task_equivalent = terminal.get("proved") is True and not terminal_counter

    if semantic_identity:
        strongest = "SEMANTIC_IDENTITY"
    elif logical_equivalence:
        strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
    elif task_equivalent:
        strongest = "CURRENT_DECISION_SUBSTITUTION"
    elif left_entails_right and not right_entails_left:
        strongest = "LEFT_ENTAILS_RIGHT"
    elif right_entails_left and not left_entails_right:
        strongest = "RIGHT_ENTAILS_LEFT"
    else:
        strongest = "UNKNOWN"

    satisfied = _relation_satisfies(
        required,
        semantic_identity=semantic_identity,
        logical_equivalence=logical_equivalence,
        left_entails_right=left_entails_right,
        right_entails_left=right_entails_left,
        task_equivalent=task_equivalent,
    )

    candidates = problem.get("candidate_relations", [])
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise SemanticRelationError("CANDIDATE_RELATIONS_NOT_SEQUENCE")
    candidate_snapshot = [
        deepcopy(dict(x)) for x in candidates if isinstance(x, Mapping)
    ]
    if len(candidate_snapshot) != len(candidates):
        raise SemanticRelationError("CANDIDATE_RELATION_NOT_OBJECT")

    proved_facts = {
        "semantic_identity": semantic_identity,
        "logical_equivalence_in_scope": logical_equivalence,
        "left_entails_right": left_entails_right,
        "right_entails_left": right_entails_left,
        "current_decision_substitution": task_equivalent,
    }

    if satisfied:
        status = "PASS__REQUIRED_SEMANTIC_RELATION_PROVED"
        action = "USE_PROVED_RELATION_WITHIN_BOUND_SCOPE"
    else:
        status = "OPEN__REQUIRED_SEMANTIC_RELATION_NOT_PROVED"
        action = "PRESERVE_DISTINCT_MEANINGS_AND_ACQUIRE_ONLY_DECISION_RELEVANT_EVIDENCE"

    return {
        "schema": SCHEMA,
        "pass": satisfied,
        "status": status,
        "action": action,
        "left_id": left_id,
        "right_id": right_id,
        "scope_id": scope_id,
        "required_relation": required,
        "strongest_proved_relation": strongest,
        "proved_facts": proved_facts,
        "terminal_equivalence": terminal,
        "proof_record_count": len(records),
        "candidate_relation_count": len(candidate_snapshot),
        "candidate_relations_are_authority": False,
        "similarity_or_model_consensus_can_certify_equivalence": False,
        "scope_leakage_authorized": False,
        "transitive_promotion_outside_scope_authorized": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

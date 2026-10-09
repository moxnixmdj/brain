"""Source-aligned semantic edge authority V1.

Produces authenticated scoped ENTAILS receipts from:
1. source constraints independently recomputed by source_aligned_semantic_proof_v8,
2. an independently authenticated exact concept-definition formula, and
3. mechanical entailment in monotone_semantic_constraint_kernel_v1.

V1 supports two directions:
- SOURCE_TO_TARGET may use partial source semantics. Extra opaque source meaning
  cannot invalidate a proved source=>target entailment.
- TARGET_TO_SOURCE additionally requires an independent completeness receipt
  binding the exact proved source-constraint set. Without that, reverse
  entailment remains UNKNOWN.

Failure to prove entailment is never treated as NOT_ENTAILS. Counterexamples
remain a separate authority route.

This module grants semantic-edge authority only. It grants no execution,
acceptance, policy-adequacy, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    resolve_common_policy,
)
from canonical.runtime.source_aligned_semantic_proof_v8 import (
    verify_proof as verify_source_proof,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    RECEIPT_SCHEMA as EDGE_RECEIPT_SCHEMA,
)

SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_SEMANTIC_EDGE_AUTHORITY_V1"
EVIDENCE_SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_SEMANTIC_EDGE_EVIDENCE_V1"
CONCEPT_SEMANTICS_RECEIPT_SCHEMA = (
    "PROJECT_BRAIN_CONCEPT_SEMANTICS_AUTHORITY_RECEIPT_V1"
)
SOURCE_COMPLETENESS_RECEIPT_SCHEMA = (
    "PROJECT_BRAIN_SOURCE_SEMANTICS_COMPLETENESS_AUTHORITY_RECEIPT_V1"
)
DIRECTIONS = {"SOURCE_TO_TARGET", "TARGET_TO_SOURCE"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _raw_sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _mention_id(source_id: str, scope_id: str, raw_span: str) -> str:
    return "MENTION:" + sha256(
        (source_id + "\n" + scope_id + "\n" + raw_span).encode("utf-8")
    ).hexdigest()


def _and(formulas: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(x)) for x in formulas]
    if not rows:
        return {"op": "TRUE"}
    if len(rows) == 1:
        return rows[0]
    return {"op": "AND", "args": rows}


def _atoms(formula: Any) -> set[str]:
    if not isinstance(formula, Mapping):
        return set()
    op = formula.get("op")
    if op == "ATOM":
        atom = formula.get("id")
        return {atom} if isinstance(atom, str) and atom else set()
    if op == "NOT":
        return _atoms(formula.get("arg"))
    if op in {"AND", "OR", "XOR"}:
        out: set[str] = set()
        args = formula.get("args")
        if isinstance(args, Sequence) and not isinstance(args, (str, bytes)):
            for arg in args:
                out.update(_atoms(arg))
        return out
    if op == "IMPLIES":
        return _atoms(formula.get("if")) | _atoms(formula.get("then"))
    return set()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "edge_receipt": None,
        "semantic_edge_authority": False,
        "source_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _verify_concept_semantics(
    *,
    target_concept_id: str,
    scope_id: str,
    target_formula: Mapping[str, Any],
    receipt: Mapping[str, Any] | None,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(receipt, Mapping) or not callable(verifier):
        return None, "CONCEPT_SEMANTICS_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(receipt)))
    if not isinstance(out, Mapping):
        return None, "CONCEPT_SEMANTICS_VERIFIER_RETURNED_NO_RECEIPT"
    out = deepcopy(dict(out))
    required = {
        "pass": True,
        "schema": CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
        "scope_id": scope_id,
        "concept_id": target_concept_id,
        "formula_sha256": _sha(target_formula),
        "definition_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
        "concept_semantics_authenticated": True,
        "formula_semantics_authenticated": True,
        "verification_authority_mutated": False,
    }
    bad = [key for key, value in required.items() if out.get(key) != value]
    if _SHA256.fullmatch(str(out.get("receipt_sha256") or "")) is None:
        bad.append("receipt_sha256")
    if bad:
        return (
            None,
            "CONCEPT_SEMANTICS_RECEIPT_BINDING_INVALID:"
            + ",".join(sorted(set(bad))),
        )
    return out, None


def _verify_source_completeness(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    proved_constraints: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(receipt, Mapping) or not callable(verifier):
        return None, "SOURCE_COMPLETENESS_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(receipt)))
    if not isinstance(out, Mapping):
        return None, "SOURCE_COMPLETENESS_VERIFIER_RETURNED_NO_RECEIPT"
    out = deepcopy(dict(out))
    required = {
        "pass": True,
        "schema": SOURCE_COMPLETENESS_RECEIPT_SCHEMA,
        "source_id": source_id,
        "scope_id": scope_id,
        "raw_span_sha256": _raw_sha(raw_span),
        "proved_constraints_sha256": _sha(list(proved_constraints)),
        "decision_relevant_semantics_complete": True,
        "source_constraints_semantics_authenticated": True,
        "verification_authority_mutated": False,
    }
    bad = [key for key, value in required.items() if out.get(key) != value]
    if _SHA256.fullmatch(str(out.get("receipt_sha256") or "")) is None:
        bad.append("receipt_sha256")
    if bad:
        return (
            None,
            "SOURCE_COMPLETENESS_RECEIPT_BINDING_INVALID:"
            + ",".join(sorted(set(bad))),
        )
    return out, None


def _edge_receipt(
    *,
    scope_id: str,
    source_node_id: str,
    target_node_id: str,
    evidence_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = {
        "pass": True,
        "schema": EDGE_RECEIPT_SCHEMA,
        "scope_id": scope_id,
        "source_id": source_node_id,
        "target_id": target_node_id,
        "relation": "ENTAILS",
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": _sha(evidence_bundle),
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


def prove(
    raw_span: str,
    *,
    source_id: str,
    scope_id: str,
    target_concept_id: str,
    direction: str,
    source_claims: Sequence[Mapping[str, Any]],
    target_formula: Mapping[str, Any],
    concept_semantics_receipt: Mapping[str, Any] | None,
    concept_semantics_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None,
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
    source_completeness_receipt: Mapping[str, Any] | None = None,
    source_completeness_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    source_proof_verifier: Callable[..., Mapping[str, Any]] = verify_source_proof,
) -> dict[str, Any]:
    """Prove one scoped semantic entailment edge.

    SOURCE_TO_TARGET:
      independently proved source constraints => authenticated concept formula.

    TARGET_TO_SOURCE:
      authenticated concept formula => complete source constraint conjunction,
      but only after an independent source-completeness receipt binds the exact
      raw bytes and exact proved-constraint set.
    """
    try:
        if not isinstance(raw_span, str) or not raw_span.strip():
            return _base("FAIL_CLOSED", reason="RAW_SPAN_REQUIRED")
        source_id = str(source_id or "").strip()
        scope_id = str(scope_id or "").strip()
        target_concept_id = str(target_concept_id or "").strip()
        direction = str(direction or "").strip().upper()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if not scope_id:
            return _base("FAIL_CLOSED", reason="SCOPE_ID_REQUIRED")
        if not target_concept_id:
            return _base("FAIL_CLOSED", reason="TARGET_CONCEPT_ID_REQUIRED")
        if direction not in DIRECTIONS:
            return _base("FAIL_CLOSED", reason="DIRECTION_INVALID")
        if not isinstance(source_claims, Sequence) or isinstance(
            source_claims, (str, bytes)
        ):
            return _base("FAIL_CLOSED", reason="SOURCE_CLAIMS_INVALID")
        if not isinstance(target_formula, Mapping):
            return _base("FAIL_CLOSED", reason="TARGET_FORMULA_INVALID")
        if not callable(source_proof_verifier):
            return _base("FAIL_CLOSED", reason="SOURCE_PROOF_VERIFIER_REQUIRED")

        source_proof = source_proof_verifier(
            raw_span,
            source_id=source_id,
            claims=deepcopy(list(source_claims)),
            typed_context=deepcopy(dict(typed_context))
            if isinstance(typed_context, Mapping)
            else typed_context,
            expected_typed_context_sha256=expected_typed_context_sha256,
            fact_source=fact_source,
            fact_source_id=fact_source_id,
        )
        if not isinstance(source_proof, Mapping):
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_PROOF_VERIFIER_RETURNED_NO_RESULT",
            )
        source_proof = deepcopy(dict(source_proof))
        if source_proof.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_PROOF_FAIL_CLOSED",
                source_proof=source_proof,
            )

        proved_constraints = source_proof.get("proved_constraints", [])
        if not isinstance(proved_constraints, Sequence) or isinstance(
            proved_constraints, (str, bytes)
        ):
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_PROVED_CONSTRAINTS_INVALID",
                source_proof=source_proof,
            )
        constraints: list[dict[str, Any]] = []
        for i, row in enumerate(proved_constraints):
            if not isinstance(row, Mapping):
                return _base(
                    "FAIL_CLOSED",
                    reason=f"SOURCE_PROVED_CONSTRAINT_NOT_OBJECT:{i}",
                    source_proof=source_proof,
                )
            constraints.append(deepcopy(dict(row)))

        concept_authority, concept_error = _verify_concept_semantics(
            target_concept_id=target_concept_id,
            scope_id=scope_id,
            target_formula=target_formula,
            receipt=concept_semantics_receipt,
            verifier=concept_semantics_verifier,
        )
        if concept_error is not None or concept_authority is None:
            return _base(
                "FAIL_CLOSED",
                reason=concept_error,
                source_proof=source_proof,
            )

        mention = _mention_id(source_id, scope_id, raw_span)
        source_formula = _and(constraints)
        completeness = None

        if direction == "TARGET_TO_SOURCE":
            completeness, completeness_error = _verify_source_completeness(
                raw_span=raw_span,
                source_id=source_id,
                scope_id=scope_id,
                proved_constraints=constraints,
                receipt=source_completeness_receipt,
                verifier=source_completeness_verifier,
            )
            if completeness_error is not None or completeness is None:
                return _base(
                    "UNKNOWN__SOURCE_SEMANTICS_COMPLETENESS_REQUIRED",
                    reason=completeness_error,
                    source_proof=source_proof,
                    concept_semantics_authority=concept_authority,
                    proved_constraints=constraints,
                )

        if direction == "SOURCE_TO_TARGET":
            state_constraints = constraints
            target_condition = deepcopy(dict(target_formula))
            source_node_id = mention
            target_node_id = target_concept_id
            policy_id = "TARGET_CONCEPT"
        else:
            state_constraints = [deepcopy(dict(target_formula))]
            target_condition = source_formula
            source_node_id = target_concept_id
            target_node_id = mention
            policy_id = "SOURCE_MEANING"

        basis = sorted(
            set().union(
                *[_atoms(x) for x in state_constraints],
                _atoms(target_condition),
            )
        )
        if not basis:
            return _base(
                "UNKNOWN__NO_DECISION_BASIS_ATOMS",
                source_proof=source_proof,
                concept_semantics_authority=concept_authority,
                source_completeness_authority=completeness,
                proved_constraints=constraints,
            )

        entailment = resolve_common_policy(
            basis,
            {policy_id: target_condition},
            formal_source_constraints=state_constraints,
            proposed_refinements=state_constraints,
        )
        if entailment.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="MONOTONE_ENTAILMENT_KERNEL_FAIL_CLOSED",
                source_proof=source_proof,
                concept_semantics_authority=concept_authority,
                source_completeness_authority=completeness,
                entailment_result=entailment,
            )

        proved = policy_id in (entailment.get("certified_common_policies") or [])
        if not proved:
            return _base(
                "UNKNOWN__ENTAILMENT_NOT_PROVED",
                source_proof=source_proof,
                concept_semantics_authority=concept_authority,
                source_completeness_authority=completeness,
                proved_constraints=constraints,
                source_formula=source_formula,
                target_formula=deepcopy(dict(target_formula)),
                entailment_result=entailment,
                nonentailment_authority=False,
                boundary=(
                    "FAILURE_TO_PROVE_ENTAILMENT_IS_UNKNOWN__NOT_NOT_ENTAILS"
                ),
            )

        evidence_bundle = {
            "direction": direction,
            "source_document_id": source_id,
            "raw_span_sha256": _raw_sha(raw_span),
            "scope_id": scope_id,
            "mention_id": mention,
            "target_concept_id": target_concept_id,
            "proved_constraints": constraints,
            "source_formula": source_formula,
            "target_formula": deepcopy(dict(target_formula)),
            "concept_semantics_authority": concept_authority,
            "source_completeness_authority": completeness,
            "entailment_state_sha256": entailment.get("state_sha256"),
            "certified_common_policies": entailment.get(
                "certified_common_policies"
            ),
        }
        receipt = _edge_receipt(
            scope_id=scope_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            evidence_bundle=evidence_bundle,
        )

        return _base(
            "PASS__SOURCE_ALIGNED_SEMANTIC_ENTAILMENT_EDGE",
            passed=True,
            edge_receipt=receipt,
            semantic_edge_authority=True,
            direction=direction,
            source_document_id=source_id,
            raw_span_sha256=_raw_sha(raw_span),
            mention_id=mention,
            target_concept_id=target_concept_id,
            proved_constraints=constraints,
            source_formula=source_formula,
            target_formula=deepcopy(dict(target_formula)),
            source_proof=source_proof,
            concept_semantics_authority=concept_authority,
            source_completeness_authority=completeness,
            entailment_result=entailment,
            boundary=(
                "SCOPED_ENTAILMENT_EDGE_ONLY__SOURCE_TO_TARGET_MAY_USE_PARTIAL_"
                "SOURCE_SEMANTICS__TARGET_TO_SOURCE_REQUIRES_INDEPENDENT_EXACT_"
                "SOURCE_COMPLETENESS__NO_NOT_ENTAILS_FROM_PROOF_FAILURE__NO_"
                "POLICY_ACCEPTANCE_EXECUTION_PROMOTION_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )



def evaluate_edge_evidence(
    payload: Mapping[str, Any],
    *,
    concept_semantics_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None,
    source_completeness_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    source_proof_verifier: Callable[..., Mapping[str, Any]] = verify_source_proof,
) -> dict[str, Any]:
    """Recompute one edge from a proof envelope.

    The envelope is proposal/evidence material, never authority by itself.
    This function is the intended bridge for semantic_relation_entailment_dag_v1:
    the DAG may pass an envelope to a relation verifier, and this checker returns
    a canonical edge only if every load-bearing component recomputes.
    """
    if not isinstance(payload, Mapping):
        return _base("FAIL_CLOSED", reason="EDGE_EVIDENCE_NOT_OBJECT")
    allowed = {
        "schema",
        "raw_span",
        "source_id",
        "scope_id",
        "target_concept_id",
        "direction",
        "source_claims",
        "target_formula",
        "concept_semantics_receipt",
        "typed_context",
        "expected_typed_context_sha256",
        "fact_source",
        "fact_source_id",
        "source_completeness_receipt",
    }
    extra = set(payload) - allowed
    if extra:
        return _base(
            "FAIL_CLOSED",
            reason="UNMODELED_EDGE_EVIDENCE_FIELDS:"
            + ",".join(sorted(str(x) for x in extra)),
        )
    if payload.get("schema") != EVIDENCE_SCHEMA:
        return _base("FAIL_CLOSED", reason="EDGE_EVIDENCE_SCHEMA_INVALID")

    return prove(
        payload.get("raw_span"),
        source_id=payload.get("source_id"),
        scope_id=payload.get("scope_id"),
        target_concept_id=payload.get("target_concept_id"),
        direction=payload.get("direction"),
        source_claims=payload.get("source_claims", ()),
        target_formula=payload.get("target_formula"),
        concept_semantics_receipt=payload.get("concept_semantics_receipt"),
        concept_semantics_verifier=concept_semantics_verifier,
        typed_context=payload.get("typed_context"),
        expected_typed_context_sha256=payload.get(
            "expected_typed_context_sha256"
        ),
        fact_source=payload.get("fact_source"),
        fact_source_id=payload.get("fact_source_id"),
        source_completeness_receipt=payload.get(
            "source_completeness_receipt"
        ),
        source_completeness_verifier=source_completeness_verifier,
        source_proof_verifier=source_proof_verifier,
    )


def verify_edge_evidence(
    payload: Mapping[str, Any],
    *,
    concept_semantics_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None,
    source_completeness_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    source_proof_verifier: Callable[..., Mapping[str, Any]] = verify_source_proof,
) -> Mapping[str, Any] | None:
    """Return only a recomputed canonical DAG edge receipt, or None."""
    result = evaluate_edge_evidence(
        payload,
        concept_semantics_verifier=concept_semantics_verifier,
        source_completeness_verifier=source_completeness_verifier,
        source_proof_verifier=source_proof_verifier,
    )
    receipt = result.get("edge_receipt") if isinstance(result, Mapping) else None
    if result.get("pass") is not True or not isinstance(receipt, Mapping):
        return None
    return deepcopy(dict(receipt))

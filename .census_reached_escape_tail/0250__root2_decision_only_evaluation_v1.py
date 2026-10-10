from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.blind_threshold_receipt_v1 import compile_blind_threshold_receipt
from canonical.runtime.threshold_proof_dag_v1 import compile_threshold_proof_dag

INPUT_SCHEMA = "PROJECT_BRAIN_ROOT2_DECISION_ONLY_EVALUATION_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_ROOT2_DECISION_ONLY_EVALUATION_OUTPUT_V1"

class DecisionOnlyEvaluationError(ValueError):
    pass

def _mapping_or_none(v: Any, field: str) -> Mapping[str, Any] | None:
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise DecisionOnlyEvaluationError(field + "_MAPPING_REQUIRED")
    return v

def compile_decision_only_evaluation(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping):
            raise DecisionOnlyEvaluationError("DOCUMENT_MAPPING_REQUIRED")
        if doc.get("schema") != INPUT_SCHEMA:
            raise DecisionOnlyEvaluationError("SCHEMA_MISMATCH")

        predicate_id = doc.get("predicate_id")
        if not isinstance(predicate_id, str) or not predicate_id:
            raise DecisionOnlyEvaluationError("PREDICATE_ID_REQUIRED")

        blind_doc = _mapping_or_none(doc.get("blind_threshold_doc"), "BLIND_THRESHOLD_DOC")
        dag_doc = _mapping_or_none(doc.get("threshold_dag_doc"), "THRESHOLD_DAG_DOC")
        if blind_doc is None and dag_doc is None:
            raise DecisionOnlyEvaluationError("AT_LEAST_ONE_DECISION_ROUTE_REQUIRED")

        attempts: list[dict[str, Any]] = []

        # Precedence: authenticated owner/platform one-bit verdict first because it can
        # settle the exact frozen inequality with zero score or dataset disclosure.
        if blind_doc is not None:
            blind = compile_blind_threshold_receipt(blind_doc)
            attempts.append({"route": "BLIND_THRESHOLD_RECEIPT", "result": blind})
            if blind.get("status", "").startswith("PASS__BLIND_THRESHOLD"):
                bpid = blind.get("predicate_id")
                if bpid != predicate_id:
                    raise DecisionOnlyEvaluationError("BLIND_PREDICATE_ID_DRIFT")
                verdict = blind.get("verdict")
                if verdict in {"PASS", "FAIL"}:
                    return {
                        "schema": OUTPUT_SCHEMA,
                        "status": "DECIDED__AUTHENTICATED_ONE_BIT_THRESHOLD_CERTIFICATE",
                        "predicate_id": predicate_id,
                        "verdict": verdict,
                        "decision_route": "BLIND_THRESHOLD_RECEIPT",
                        "exact_score_required": False,
                        "dataset_disclosure_required": False,
                        "attempts": attempts,
                        "acceptance_credit_delta": 0,
                        "family_credit_delta": 0,
                        "capability_credit_delta": 0,
                        "ownership_credit_delta": 0,
                        "execution_authority": False,
                        "fresh_reality_authority": False,
                        "promotion_authority": False,
                    }

        # Otherwise use exact lower/upper-bound algebra and the dependency-aware
        # minimum proof cut. This can settle a predicate without full benchmark
        # completion and blocks fresh-reality actions unless separately authorized.
        if dag_doc is not None:
            dag = compile_threshold_proof_dag(dag_doc)
            attempts.append({"route": "THRESHOLD_PROOF_DAG", "result": dag})
            if dag.get("status") == "FAIL_CLOSED":
                return {
                    "schema": OUTPUT_SCHEMA,
                    "status": "FAIL_CLOSED",
                    "predicate_id": predicate_id,
                    "errors": ["THRESHOLD_DAG_FAIL_CLOSED"],
                    "attempts": attempts,
                    "acceptance_credit_delta": 0,
                    "family_credit_delta": 0,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                    "execution_authority": False,
                    "fresh_reality_authority": False,
                    "promotion_authority": False,
                }
            compiled = dag.get("compiled")
            if not isinstance(compiled, Mapping):
                raise DecisionOnlyEvaluationError("THRESHOLD_DAG_COMPILED_RESULT_REQUIRED")
            verdict = compiled.get("verdict")
            if verdict in {"PASS", "FAIL"}:
                return {
                    "schema": OUTPUT_SCHEMA,
                    "status": "DECIDED__THRESHOLD_CERTIFICATE",
                    "predicate_id": predicate_id,
                    "verdict": verdict,
                    "decision_route": "THRESHOLD_PROOF_DAG",
                    "exact_score_required": False,
                    "full_benchmark_required": False,
                    "attempts": attempts,
                    "acceptance_credit_delta": 0,
                    "family_credit_delta": 0,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                    "execution_authority": False,
                    "fresh_reality_authority": False,
                    "promotion_authority": False,
                }
            if verdict == "OPEN":
                return {
                    "schema": OUTPUT_SCHEMA,
                    "status": "OPEN__MINIMUM_CERTIFICATE_CUT_COMPILED",
                    "predicate_id": predicate_id,
                    "verdict": "OPEN",
                    "decision_route": "THRESHOLD_PROOF_DAG",
                    "minimum_pass_cut": compiled.get("minimum_pass_cut"),
                    "minimum_fail_cut": compiled.get("minimum_fail_cut"),
                    "blocked_fresh_reality_actions": dag.get("blocked_fresh_reality_actions", []),
                    "full_benchmark_required": False if compiled.get("minimum_pass_cut") is not None or compiled.get("minimum_fail_cut") is not None else None,
                    "attempts": attempts,
                    "acceptance_credit_delta": 0,
                    "family_credit_delta": 0,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                    "execution_authority": False,
                    "fresh_reality_authority": False,
                    "promotion_authority": False,
                }
            raise DecisionOnlyEvaluationError("THRESHOLD_DAG_VERDICT_INVALID")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "OPEN__NO_ADMISSIBLE_DECISION_CERTIFICATE",
            "predicate_id": predicate_id,
            "verdict": "OPEN",
            "attempts": attempts,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    except DecisionOnlyEvaluationError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }

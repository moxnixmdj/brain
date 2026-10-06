from __future__ import annotations

from typing import Any, Mapping
import re

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_CASE_ISOLATION_RESET_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_CASE_ISOLATION_RESET_OUTPUT_V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IsolationError(ValueError):
    pass


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise IsolationError(name + "_INVALID")
    return value


def _true(row: Mapping[str, Any], key: str, prefix: str) -> None:
    if row.get(key) is not True:
        raise IsolationError(prefix + "_" + key.upper() + "_NOT_TRUE")


def compile_isolation(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise IsolationError("SCHEMA_INVALID")

        base = doc.get("base")
        if not isinstance(base, Mapping):
            raise IsolationError("BASE_INVALID")
        base_sha = _sha(base.get("immutable_base_state_sha256"), "BASE_STATE_SHA256")
        for key in (
            "brain_runtime_frozen",
            "opus_interface_frozen",
            "tool_authority_frozen",
            "read_only_shared_dependencies_only",
            "cross_case_persistent_memory_disabled",
            "cross_case_mutable_cache_disabled",
            "outbound_effects_case_namespaced",
            "case_namespace_destroyed_after_case",
            "external_mutable_services_resettable",
        ):
            _true(base, key, "BASE")

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            raise IsolationError("CASES_INVALID")

        seen_ids: set[str] = set()
        seen_namespaces: set[str] = set()
        case_receipts: list[dict[str, Any]] = []

        for index, raw in enumerate(cases):
            if not isinstance(raw, Mapping):
                raise IsolationError(f"CASE_{index}_INVALID")
            cid = raw.get("case_id")
            if not isinstance(cid, str) or not cid.strip():
                raise IsolationError(f"CASE_{index}_ID_INVALID")
            cid = cid.strip()
            if cid in seen_ids:
                raise IsolationError("CASE_ID_DUPLICATE:" + cid)
            seen_ids.add(cid)

            if _sha(raw.get("immutable_base_state_sha256"), f"CASE_{index}_BASE_SHA256") != base_sha:
                raise IsolationError(f"CASE_{index}_BASE_STATE_MISMATCH")

            namespace = _sha(raw.get("mutable_namespace_sha256"), f"CASE_{index}_NAMESPACE_SHA256")
            if namespace in seen_namespaces:
                raise IsolationError("MUTABLE_NAMESPACE_REUSED:" + namespace)
            seen_namespaces.add(namespace)

            initial = _sha(raw.get("case_initial_state_sha256"), f"CASE_{index}_INITIAL_STATE_SHA256")
            brain_initial = _sha(raw.get("brain_initial_state_sha256"), f"CASE_{index}_BRAIN_INITIAL_SHA256")
            opus_initial = _sha(raw.get("opus_initial_state_sha256"), f"CASE_{index}_OPUS_INITIAL_SHA256")
            if not (initial == brain_initial == opus_initial):
                raise IsolationError(f"CASE_{index}_INITIAL_STATE_NOT_IDENTICAL")

            prior_inputs = raw.get("prior_case_ids_consumed")
            if prior_inputs != []:
                raise IsolationError(f"CASE_{index}_PRIOR_CASE_DEPENDENCY")

            for key in (
                "namespace_created_from_clean_base",
                "brain_run_confined_to_namespace",
                "future_opus_run_confined_to_same_namespace_semantics",
                "all_mutable_sinks_namespaced_or_restored",
                "post_case_namespace_destroyed",
                "external_mutable_state_restored",
                "no_result_dependent_case_generation",
                "no_result_dependent_runtime_mutation",
            ):
                _true(raw, key, f"CASE_{index}")

            post_reset = _sha(raw.get("post_reset_base_state_sha256"), f"CASE_{index}_POST_RESET_SHA256")
            if post_reset != base_sha:
                raise IsolationError(f"CASE_{index}_RESET_NOT_EQUIVALENT")

            receipt = raw.get("receipt")
            if not isinstance(receipt, Mapping):
                raise IsolationError(f"CASE_{index}_RECEIPT_INVALID")
            _sha(receipt.get("receipt_sha256"), f"CASE_{index}_RECEIPT_SHA256")
            _true(receipt, "independent_or_objective", f"CASE_{index}_RECEIPT")

            case_receipts.append({
                "case_id": cid,
                "mutable_namespace_sha256": namespace,
                "case_initial_state_sha256": initial,
                "post_reset_base_state_sha256": post_reset,
                "receipt_sha256": receipt["receipt_sha256"],
            })

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__CASE_ISOLATED_OR_RESET_EQUIVALENT",
            "case_count": len(case_receipts),
            "immutable_base_state_sha256": base_sha,
            "case_receipts": case_receipts,
            "residual_only_comparator_counterfactual_preserved": True,
            "cross_case_state_dependency_detected": False,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except IsolationError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

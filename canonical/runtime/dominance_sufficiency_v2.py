from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime.dominance_sufficiency_v1 import (
    INPUT_SCHEMA as V1_INPUT_SCHEMA,
    compile_dominance_sufficiency as compile_v1,
)

INPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_INPUT_V2"
OUTPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_OUTPUT_V2"


def _validate(doc: Mapping[str, Any]) -> dict[str, Any]:
    target_sha = bind.sha256_value(doc.get("target_contract_sha256"), "TARGET_CONTRACT_SHA256")
    metric_id = bind.token(doc.get("metric_id"), "METRIC_ID")
    live = bind.live_ids(doc.get("hypotheses"))
    live_sha = bind.live_digest(live)

    target = doc.get("target_contract_receipt")
    if not isinstance(target, Mapping):
        raise bind.BindingError("TARGET_CONTRACT_RECEIPT_INVALID")
    target_path, target_blob = bind.content_binding(target, "TARGET_CONTRACT_RECEIPT")
    bind.same_sha256(target, "target_contract_sha256", target_sha, "TARGET_CONTRACT_RECEIPT")
    bind.same(target, "metric_id", metric_id, "TARGET_CONTRACT_RECEIPT")
    bind.require_true(target, "load_bearing_dimensions_complete", "TARGET_CONTRACT_RECEIPT")
    bind.require_true(target, "acceptance_relation_sound", "TARGET_CONTRACT_RECEIPT")
    bind.require_true(target, "independent_or_objective", "TARGET_CONTRACT_RECEIPT")

    coverage = doc.get("hypothesis_coverage_receipt")
    if not isinstance(coverage, Mapping):
        raise bind.BindingError("HYPOTHESIS_COVERAGE_RECEIPT_INVALID")
    cov_path, cov_blob = bind.content_binding(coverage, "HYPOTHESIS_COVERAGE_RECEIPT")
    bind.same_sha256(coverage, "target_contract_sha256", target_sha, "HYPOTHESIS_COVERAGE_RECEIPT")
    bind.same(coverage, "metric_id", metric_id, "HYPOTHESIS_COVERAGE_RECEIPT")
    bind.same_sha256(
        coverage,
        "live_hypothesis_set_sha256",
        live_sha,
        "HYPOTHESIS_COVERAGE_RECEIPT",
    )
    bind.require_true(coverage, "scope_complete", "HYPOTHESIS_COVERAGE_RECEIPT")
    bind.require_true(coverage, "independent_or_objective", "HYPOTHESIS_COVERAGE_RECEIPT")

    configs = doc.get("configurations")
    if not isinstance(configs, list) or not configs:
        raise bind.BindingError("CONFIGURATIONS_INVALID")

    normalized = []
    seen: set[str] = set()
    for i, raw in enumerate(configs):
        if not isinstance(raw, Mapping):
            raise bind.BindingError(f"CONFIGURATION_{i}_INVALID")
        cid = bind.token(raw.get("id"), f"CONFIGURATION_{i}_ID")
        if cid in seen:
            raise bind.BindingError("CONFIGURATION_ID_DUPLICATE:" + cid)
        seen.add(cid)
        owned = raw.get("brain_owned")
        if not isinstance(owned, bool):
            raise bind.BindingError(f"CONFIGURATION_{i}_BRAIN_OWNED_INVALID")

        if not owned:
            normalized.append({"id": cid, "brain_owned": False})
            continue

        ownership = raw.get("ownership_receipt")
        if not isinstance(ownership, Mapping):
            raise bind.BindingError(f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT_INVALID")
        own_path, own_blob = bind.content_binding(
            ownership, f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT"
        )
        bind.same(
            ownership,
            "configuration_id",
            cid,
            f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT",
        )
        bind.same_sha256(
            ownership,
            "target_contract_sha256",
            target_sha,
            f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT",
        )
        bind.require_true(
            ownership, "donor_independent", f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT"
        )
        bind.require_true(
            ownership,
            "independent_or_objective",
            f"CONFIGURATION_{i}_OWNERSHIP_RECEIPT",
        )

        bounds = raw.get("bounds")
        if not isinstance(bounds, Mapping) or set(map(str, bounds.keys())) != set(live):
            raise bind.BindingError(f"CONFIGURATION_{i}_LIVE_BOUND_SET_MISMATCH")

        normalized_bounds = {}
        for hid in live:
            cell = bounds.get(hid)
            if not isinstance(cell, Mapping):
                raise bind.BindingError(f"CONFIGURATION_{i}_{hid}_BOUND_INVALID")
            brain_lower = bind.number(
                cell.get("brain_lower"), f"CONFIGURATION_{i}_{hid}_BRAIN_LOWER"
            )
            comparator_upper = bind.number(
                cell.get("comparator_upper"),
                f"CONFIGURATION_{i}_{hid}_COMPARATOR_UPPER",
            )

            proof = cell.get("bound_receipt")
            if not isinstance(proof, Mapping):
                raise bind.BindingError(f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_INVALID")
            proof_path, proof_blob = bind.content_binding(
                proof, f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT"
            )
            bind.same(
                proof,
                "configuration_id",
                cid,
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            bind.same(
                proof,
                "hypothesis_id",
                hid,
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            bind.same_sha256(
                proof,
                "target_contract_sha256",
                target_sha,
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            bind.same(
                proof,
                "metric_id",
                metric_id,
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            if bind.number(
                proof.get("brain_lower"),
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_BRAIN_LOWER",
            ) != brain_lower:
                raise bind.BindingError(
                    f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_BRAIN_LOWER_MISMATCH"
                )
            if bind.number(
                proof.get("comparator_upper"),
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_COMPARATOR_UPPER",
            ) != comparator_upper:
                raise bind.BindingError(
                    f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_COMPARATOR_UPPER_MISMATCH"
                )
            bind.require_true(
                proof,
                "evaluator_relation_proved",
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            bind.require_true(
                proof, "scope_complete", f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT"
            )
            bind.require_true(
                proof,
                "independent_or_objective",
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT",
            )
            normalized_bounds[hid] = {
                "brain_lower": str(brain_lower),
                "comparator_upper": str(comparator_upper),
                "bound_receipt": {
                    "path": proof_path,
                    "git_blob_sha": proof_blob,
                    "scope_complete": True,
                    "independent_or_objective": True,
                },
            }

        normalized.append(
            {
                "id": cid,
                "brain_owned": True,
                "ownership_receipt": {
                    "path": own_path,
                    "git_blob_sha": own_blob,
                    "donor_independent": True,
                    "independent_or_objective": True,
                },
                "bounds": normalized_bounds,
            }
        )

    return {
        "target_contract_sha256": target_sha,
        "metric_id": metric_id,
        "live_hypothesis_set_sha256": live_sha,
        "target_contract_receipt": {"path": target_path, "git_blob_sha": target_blob},
        "hypothesis_coverage_receipt": {"path": cov_path, "git_blob_sha": cov_blob},
        "normalized_v1": {
            "schema": V1_INPUT_SCHEMA,
            "hypothesis_coverage_receipt": {
                "path": cov_path,
                "git_blob_sha": cov_blob,
                "scope_complete": True,
                "independent_or_objective": True,
            },
            "hypotheses": list(doc.get("hypotheses") or []),
            "configurations": normalized,
        },
    }


def compile_dominance_sufficiency_v2(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise bind.BindingError("SCHEMA_INVALID")
        validated = _validate(doc)
        core = compile_v1(validated["normalized_v1"])
        if core.get("status") == "FAIL_CLOSED":
            return {
                "schema": OUTPUT_SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["V1_ARITHMETIC_CORE_FAILED"] + list(core.get("errors") or []),
                "execution_authority": False,
                "promotion_authority": False,
                "acceptance_credit_delta": 0,
            }
        passed = str(core.get("status") or "").startswith("PASS__DOMINANCE_SUFFICIENT")
        return {
            "schema": OUTPUT_SCHEMA,
            "status": (
                "PASS__EXACTLY_BOUND_DOMINANCE_SUFFICIENT"
                if passed
                else "OPEN__NO_EXACTLY_BOUND_ROBUST_WITNESS"
            ),
            "target_contract_sha256": validated["target_contract_sha256"],
            "metric_id": validated["metric_id"],
            "live_hypothesis_set_sha256": validated["live_hypothesis_set_sha256"],
            "selected_configuration": core.get("selected_configuration") if passed else None,
            "worst_case_margin": core.get("worst_case_margin") if passed else None,
            "core": core,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except bind.BindingError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

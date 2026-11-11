from __future__ import annotations

import copy
from typing import Any, Mapping

from canonical.runtime import dominance_binding_v2 as bind2
from canonical.runtime import dominance_semantic_binding_v3 as sem
from canonical.runtime.dominance_sufficiency_v2 import (
    INPUT_SCHEMA as V2_INPUT_SCHEMA,
    compile_dominance_sufficiency_v2 as compile_v2,
)

INPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_INPUT_V3"
OUTPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_OUTPUT_V3"


def _validate_semantics(doc: Mapping[str, Any]) -> dict[str, Any]:
    rows = sem.live_worlds(doc.get("hypotheses"))
    world_sha = sem.live_world_digest(rows)
    semantic_map = sem.semantic_by_id(rows)

    for i, raw in enumerate(doc.get("hypotheses") or []):
        if raw.get("plausible") is not True:
            continue
        hid = bind2.token(raw.get("id"), f"HYPOTHESIS_{i}_ID")
        semantic = semantic_map[hid]
        receipt = raw.get("definition_receipt")
        if not isinstance(receipt, Mapping):
            raise sem.SemanticBindingError(
                f"HYPOTHESIS_{i}_DEFINITION_RECEIPT_INVALID"
            )
        bind2.content_binding(receipt, f"HYPOTHESIS_{i}_DEFINITION_RECEIPT")
        bind2.same(
            receipt,
            "hypothesis_id",
            hid,
            f"HYPOTHESIS_{i}_DEFINITION_RECEIPT",
        )
        bind2.same_sha256(
            receipt,
            "semantic_sha256",
            semantic,
            f"HYPOTHESIS_{i}_DEFINITION_RECEIPT",
        )
        bind2.require_true(
            receipt,
            "independent_or_objective",
            f"HYPOTHESIS_{i}_DEFINITION_RECEIPT",
        )

    coverage = doc.get("hypothesis_coverage_receipt")
    if not isinstance(coverage, Mapping):
        raise sem.SemanticBindingError("HYPOTHESIS_COVERAGE_RECEIPT_INVALID")
    if bind2.sha256_value(
        coverage.get("live_world_set_sha256"),
        "HYPOTHESIS_COVERAGE_RECEIPT_LIVE_WORLD_SET_SHA256",
    ) != world_sha:
        raise sem.SemanticBindingError(
            "HYPOTHESIS_COVERAGE_RECEIPT_LIVE_WORLD_SET_SHA256_MISMATCH"
        )

    configs = doc.get("configurations")
    if not isinstance(configs, list):
        raise sem.SemanticBindingError("CONFIGURATIONS_INVALID")
    for i, config in enumerate(configs):
        if not isinstance(config, Mapping) or config.get("brain_owned") is not True:
            continue
        bounds = config.get("bounds")
        if not isinstance(bounds, Mapping):
            raise sem.SemanticBindingError(f"CONFIGURATION_{i}_BOUNDS_INVALID")
        for hid, semantic in rows:
            cell = bounds.get(hid)
            if not isinstance(cell, Mapping):
                raise sem.SemanticBindingError(
                    f"CONFIGURATION_{i}_{hid}_BOUND_INVALID"
                )
            proof = cell.get("bound_receipt")
            if not isinstance(proof, Mapping):
                raise sem.SemanticBindingError(
                    f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_INVALID"
                )
            if bind2.sha256_value(
                proof.get("hypothesis_semantic_sha256"),
                f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_HYPOTHESIS_SEMANTIC_SHA256",
            ) != semantic:
                raise sem.SemanticBindingError(
                    f"CONFIGURATION_{i}_{hid}_BOUND_RECEIPT_HYPOTHESIS_SEMANTIC_SHA256_MISMATCH"
                )

    return {
        "rows": rows,
        "world_sha": world_sha,
        "semantic_map": semantic_map,
    }


def compile_dominance_sufficiency_v3(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise sem.SemanticBindingError("SCHEMA_INVALID")

        semantic = _validate_semantics(doc)

        shadow = copy.deepcopy(dict(doc))
        shadow["schema"] = V2_INPUT_SCHEMA
        live_ids = [hid for hid, _ in semantic["rows"]]
        shadow["hypothesis_coverage_receipt"]["live_hypothesis_set_sha256"] = (
            bind2.live_digest(live_ids)
        )

        v2 = compile_v2(shadow)
        if v2.get("status") == "FAIL_CLOSED":
            return {
                "schema": OUTPUT_SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["V2_EXACT_BINDING_CORE_FAILED"] + list(v2.get("errors") or []),
                "execution_authority": False,
                "promotion_authority": False,
                "acceptance_credit_delta": 0,
            }

        passed = v2.get("status") == "PASS__EXACTLY_BOUND_DOMINANCE_SUFFICIENT"
        return {
            "schema": OUTPUT_SCHEMA,
            "status": (
                "PASS__SEMANTICALLY_BOUND_DOMINANCE_SUFFICIENT"
                if passed
                else "OPEN__NO_SEMANTICALLY_BOUND_ROBUST_WITNESS"
            ),
            "live_world_set_sha256": semantic["world_sha"],
            "live_worlds": [
                {"id": hid, "semantic_sha256": semantic_hash}
                for hid, semantic_hash in semantic["rows"]
            ],
            "selected_configuration": v2.get("selected_configuration") if passed else None,
            "worst_case_margin": v2.get("worst_case_margin") if passed else None,
            "v2": v2,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except (sem.SemanticBindingError, bind2.BindingError) as exc:
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

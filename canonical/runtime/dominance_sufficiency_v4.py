from __future__ import annotations

import copy
from typing import Any, Mapping

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime import dominance_semantic_binding_v4 as sem4
from canonical.runtime.dominance_sufficiency_v2 import (
    INPUT_SCHEMA as V2_INPUT_SCHEMA,
    compile_dominance_sufficiency_v2 as compile_v2,
)

INPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_INPUT_V4"
OUTPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_OUTPUT_V4"


def _validate_configuration_identity(
    doc: Mapping[str, Any],
    rows: list[Mapping[str, str]],
) -> dict[str, str]:
    configs = doc.get("configurations")
    if not isinstance(configs, list) or not configs:
        raise sem4.SemanticBindingV4Error("CONFIGURATIONS_INVALID")

    worlds = sem4.world_by_id(rows)
    live_ids = set(worlds)
    identity_by_id: dict[str, str] = {}
    seen: set[str] = set()

    for index, raw in enumerate(configs):
        if not isinstance(raw, Mapping):
            raise sem4.SemanticBindingV4Error(f"CONFIGURATION_{index}_INVALID")

        cid = bind.token(raw.get("id"), f"CONFIGURATION_{index}_ID")
        if cid in seen:
            raise sem4.SemanticBindingV4Error("CONFIGURATION_ID_DUPLICATE:" + cid)
        seen.add(cid)

        owned = raw.get("brain_owned")
        if not isinstance(owned, bool):
            raise sem4.SemanticBindingV4Error(
                f"CONFIGURATION_{index}_BRAIN_OWNED_INVALID"
            )
        if not owned:
            continue

        config_sha = bind.sha256_value(
            raw.get("configuration_sha256"),
            f"CONFIGURATION_{index}_CONFIGURATION_SHA256",
        )

        definition = raw.get("configuration_definition_receipt")
        if not isinstance(definition, Mapping):
            raise sem4.SemanticBindingV4Error(
                f"CONFIGURATION_{index}_DEFINITION_RECEIPT_INVALID"
            )
        bind.content_binding(
            definition, f"CONFIGURATION_{index}_DEFINITION_RECEIPT"
        )
        bind.same(
            definition,
            "configuration_id",
            cid,
            f"CONFIGURATION_{index}_DEFINITION_RECEIPT",
        )
        bind.same_sha256(
            definition,
            "configuration_sha256",
            config_sha,
            f"CONFIGURATION_{index}_DEFINITION_RECEIPT",
        )
        bind.require_true(
            definition,
            "independent_or_objective",
            f"CONFIGURATION_{index}_DEFINITION_RECEIPT",
        )

        ownership = raw.get("ownership_receipt")
        if not isinstance(ownership, Mapping):
            raise sem4.SemanticBindingV4Error(
                f"CONFIGURATION_{index}_OWNERSHIP_RECEIPT_INVALID"
            )
        bind.same_sha256(
            ownership,
            "configuration_sha256",
            config_sha,
            f"CONFIGURATION_{index}_OWNERSHIP_RECEIPT",
        )

        bounds = raw.get("bounds")
        if not isinstance(bounds, Mapping):
            raise sem4.SemanticBindingV4Error(
                f"CONFIGURATION_{index}_BOUNDS_INVALID"
            )
        if set(map(str, bounds.keys())) != live_ids:
            raise sem4.SemanticBindingV4Error(
                f"CONFIGURATION_{index}_LIVE_BOUND_SET_MISMATCH"
            )

        for hid in sorted(live_ids):
            cell = bounds.get(hid)
            if not isinstance(cell, Mapping):
                raise sem4.SemanticBindingV4Error(
                    f"CONFIGURATION_{index}_{hid}_BOUND_INVALID"
                )
            proof = cell.get("bound_receipt")
            if not isinstance(proof, Mapping):
                raise sem4.SemanticBindingV4Error(
                    f"CONFIGURATION_{index}_{hid}_BOUND_RECEIPT_INVALID"
                )
            bind.same_sha256(
                proof,
                "configuration_sha256",
                config_sha,
                f"CONFIGURATION_{index}_{hid}_BOUND_RECEIPT",
            )
            bind.same_sha256(
                proof,
                "hypothesis_semantic_sha256",
                worlds[hid]["semantic_sha256"],
                f"CONFIGURATION_{index}_{hid}_BOUND_RECEIPT",
            )

        identity_by_id[cid] = config_sha

    return identity_by_id


def compile_dominance_sufficiency_v4(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise sem4.SemanticBindingV4Error("SCHEMA_INVALID")

        rows = sem4.live_worlds(doc.get("hypotheses"))
        world_sha = sem4.live_world_digest(rows)

        coverage = doc.get("hypothesis_coverage_receipt")
        if not isinstance(coverage, Mapping):
            raise sem4.SemanticBindingV4Error(
                "HYPOTHESIS_COVERAGE_RECEIPT_INVALID"
            )
        if bind.sha256_value(
            coverage.get("live_world_set_sha256"),
            "HYPOTHESIS_COVERAGE_RECEIPT_LIVE_WORLD_SET_SHA256",
        ) != world_sha:
            raise sem4.SemanticBindingV4Error(
                "HYPOTHESIS_COVERAGE_RECEIPT_LIVE_WORLD_SET_SHA256_MISMATCH"
            )

        config_identity = _validate_configuration_identity(doc, rows)

        shadow = copy.deepcopy(dict(doc))
        shadow["schema"] = V2_INPUT_SCHEMA

        v2 = compile_v2(shadow)
        if v2.get("status") == "FAIL_CLOSED":
            return {
                "schema": OUTPUT_SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["V2_EXACT_BINDING_CORE_FAILED"]
                + list(v2.get("errors") or []),
                "execution_authority": False,
                "promotion_authority": False,
                "fresh_reality_authority": False,
                "acceptance_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }

        passed = v2.get("status") == "PASS__EXACTLY_BOUND_DOMINANCE_SUFFICIENT"
        selected = v2.get("selected_configuration") if passed else None
        selected_sha = (
            config_identity.get(str(selected))
            if selected is not None
            else None
        )
        if passed and selected_sha is None:
            raise sem4.SemanticBindingV4Error(
                "SELECTED_CONFIGURATION_IDENTITY_MISSING"
            )

        return {
            "schema": OUTPUT_SCHEMA,
            "status": (
                "PASS__CONTENT_BOUND_DOMINANCE_SUFFICIENT"
                if passed
                else "OPEN__NO_CONTENT_BOUND_ROBUST_WITNESS"
            ),
            "live_world_set_sha256": world_sha,
            "live_worlds": rows,
            "selected_configuration": selected,
            "selected_configuration_sha256": selected_sha,
            "worst_case_margin": (
                v2.get("worst_case_margin") if passed else None
            ),
            "v2": v2,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except (
        sem4.SemanticBindingV4Error,
        bind.BindingError,
    ) as exc:
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

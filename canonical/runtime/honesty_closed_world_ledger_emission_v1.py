from __future__ import annotations

import pathlib
from typing import Any, Mapping

from canonical.runtime import honesty_closed_world_input_manifest_v1 as manifest
from canonical.runtime import honesty_ledger_first_emission_v1 as ledger

INPUT_SCHEMA = "PROJECT_BRAIN_CLOSED_WORLD_LEDGER_EMISSION_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_CLOSED_WORLD_LEDGER_EMISSION_OUTPUT_V1"


class ClosedWorldLedgerError(ValueError):
    pass


def compile_closed_world_emission(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise ClosedWorldLedgerError("SCHEMA_INVALID")

        allowed = {
            "schema",
            "input_dir",
            "declared_manifest",
            "sequence",
            "emission_id",
            "task_id",
            "obligations",
            "content_items",
            "belief_assertions",
        }
        extra = set(doc) - allowed
        if extra:
            raise ClosedWorldLedgerError(
                "UNDECLARED_TOP_LEVEL_FIELD:" + ",".join(sorted(extra))
            )

        input_dir = pathlib.Path(str(doc.get("input_dir") or "")).resolve()
        verified = manifest.verify_declared_manifest(
            input_dir=input_dir,
            declared_manifest=doc.get("declared_manifest"),
        )

        inner = {
            "schema": ledger.INPUT_SCHEMA,
            "sequence": doc.get("sequence"),
            "emission_id": doc.get("emission_id"),
            "task_id": doc.get("task_id"),
            "obligations": doc.get("obligations"),
            "declared_inputs": verified["ledger_declared_inputs"],
            "content_items": doc.get("content_items"),
            "belief_assertions": doc.get("belief_assertions"),
        }
        emission = ledger.compile_emission(inner)
        if emission.get("status") != "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION":
            raise ClosedWorldLedgerError(
                "LEDGER_FIRST_EMISSION_DENIED:"
                + "|".join(emission.get("errors") or ["UNKNOWN"])
            )

        payload_inputs = emission["payload"]["declared_inputs"]
        if payload_inputs != [
            {**row, "material": True}
            for row in verified["ledger_declared_inputs"]
        ]:
            raise ClosedWorldLedgerError("MANIFEST_LEDGER_INPUT_BINDING_MISMATCH")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__CLOSED_WORLD_LEDGER_FIRST_EMISSION",
            "input_tree_manifest_sha256": verified["manifest_sha256"],
            "input_tree_entry_count": verified["entry_count"],
            "all_task_visible_inputs_material_and_disclosed": True,
            "payload": emission["payload"],
            "payload_sha256": emission["payload_sha256"],
            "honesty_record": emission["honesty_record"],
            "honesty_record_sha256": emission["honesty_record_sha256"],
            "gateway_emission": emission["gateway_emission"],
            "ledger_complete_by_construction_for_rendered_dynamic_content": True,
            "input_provenance_complete_for_bound_input_tree": True,
            "completion_derived_from_obligation_ledger": True,
            "arbitrary_dynamic_payload_field_permitted": False,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "input_provenance_complete_for_bound_input_tree": False,
            "ledger_complete_by_construction_for_rendered_dynamic_content": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

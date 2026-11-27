from pathlib import Path

from canonical.runtime.root3_native_extension_surface_v1 import classify


def test_current_native_extension_surface_is_small_and_fail_closed():
    root=Path(__file__).resolve().parents[2]
    out=classify(root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
    ids={x["capability_id"] for x in out["definite_or_reachable_in_process_native_capabilities"]}
    assert ids=={
        "auto.pypi.msgpack",
        "docx.document.create_from_json_record",
        "docx.document.create.python_docx",
        "xlsx.table.verify_against_json_records",
    }
    assert set(out["risky_adapter_modules"])=={
        "python_library_codec",
        "docx_report_from_json",
        "python_document_builder",
        "xlsx_verify_openpyxl",
    }
    assert out["native_extension_internal_effect_totality_proved"] is False
    assert out["c1_native_extension_scope_complete"] is False
    assert out["acceptance_credit_delta"]==0


def test_packaging_pure_is_not_promoted_to_native_totality():
    root=Path(__file__).resolve().parents[2]
    out=classify(root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
    assert out["packaging_level_non_native_but_source_audit_open"]
    assert all(
        x["source_level_dynamic_native_loader_audit_still_required"] is True
        for x in out["packaging_level_non_native_but_source_audit_open"]
    )

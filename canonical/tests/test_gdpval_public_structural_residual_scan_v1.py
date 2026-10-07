import json
from pathlib import Path

from canonical.runtime.gdpval_public_structural_residual_scan_v1 import scan_pages


def _row(task_id="t1", criterion="Overall formatting and style of the deliverable"):
    return {
        "task_id":task_id,
        "reference_files":[],
        "deliverable_files":["deliverable_files/x/report.docx"],
        "rubric_json":json.dumps([{"criterion":criterion}]),
    }


def _write(tmp_path, rows):
    p=tmp_path/"rows.json"
    p.write_text(json.dumps({"rows":[{"row":x} for x in rows]}),encoding="utf-8")
    return p


def test_literal_style_and_native_artifact_signals(tmp_path):
    p=_write(tmp_path,[_row()])
    out=scan_pages([p])
    assert out["status"]=="PASS__DIAGNOSTIC_ONLY"
    assert out["row_count"]==1
    assert out["counts"]["overall_format_style"]==1
    assert out["counts"]["has_gold_deliverables"]==1
    assert out["deliverable_extension_counts"]["docx"]==1


def test_no_signal_remains_uncategorized(tmp_path):
    p=_write(tmp_path,[_row(criterion="The answer states the required conclusion.")])
    out=scan_pages([p])
    assert out["tasks_with_any_explicit_structural_signal"]==0
    assert out["tasks_without_explicit_structural_signal"]==1


def test_duplicate_task_id_fails_closed(tmp_path):
    p=_write(tmp_path,[_row("dup"),_row("dup")])
    out=scan_pages([p])
    assert out["status"]=="FAIL_CLOSED"
    assert "DUPLICATE_TASK_ID" in out["errors"]


def test_bad_rubric_json_fails_closed(tmp_path):
    x=_row()
    x["rubric_json"]="{"
    p=_write(tmp_path,[x])
    out=scan_pages([p])
    assert out["status"]=="FAIL_CLOSED"
    assert any(x.startswith("RUBRIC_INVALID") for x in out["errors"])


def test_invalid_row_wrapper_fails_closed(tmp_path):
    p=tmp_path/"rows.json"
    p.write_text(json.dumps({"rows":[{"bad":1}]}),encoding="utf-8")
    out=scan_pages([p])
    assert out["status"]=="FAIL_CLOSED"
    assert any(x.startswith("ROW_WRAPPER_INVALID") for x in out["errors"])

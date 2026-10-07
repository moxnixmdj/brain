import hashlib

from canonical.runtime.bounded_task_source_set_gate_v1 import (
    compile_required_source_set,
    verify_source_coverage,
)


def task():
    return {
        "task_id": "w1_t2",
        "task_md_path": "tasks/w1_t2.md",
        "scenario_overview_path": "summary/scenario.md",
        "week_overview_path": "summary/week1.md",
        "shared_files": ["shared/a.xlsx", "shared/b.docx"],
        "week_files": ["week/c.json"],
    }


def receipts(payloads):
    out = {}
    for path, value in payloads.items():
        data = value.encode() if isinstance(value, str) else value
        out[path] = {
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "status": "PARSED",
            "parser_id": "parser-for-" + path.rsplit(".", 1)[-1],
            "parser_receipt_id": "receipt-" + path,
        }
    return out


def payloads():
    return {
        "tasks/w1_t2.md": "task",
        "summary/scenario.md": "scenario",
        "summary/week1.md": "week",
        "shared/a.xlsx": b"xlsx-bytes",
        "shared/b.docx": b"docx-bytes",
        "week/c.json": "{}",
    }


def test_bounded_manifest_enumerates_every_declared_path():
    out = compile_required_source_set(task())
    assert out["pass"] is True
    assert out["source_count"] == 6


def test_complete_materialization_and_parse_coverage_passes():
    p = payloads()
    out = verify_source_coverage(task(), materialized_sources=p, parse_receipts=receipts(p))
    assert out["pass"] is True, out
    assert out["bounded_source_discovery_false_negative_closed"] is True


def test_retrieved_but_unparsed_xlsx_blocks():
    p = payloads()
    r = receipts(p)
    r["shared/a.xlsx"]["status"] = "UNSUPPORTED"
    out = verify_source_coverage(task(), materialized_sources=p, parse_receipts=r)
    assert out["pass"] is False
    assert any(x.startswith("DECLARED_SOURCE_NOT_PARSED:shared/a.xlsx") for x in out["errors"])


def test_missing_declared_source_blocks():
    p = payloads()
    del p["shared/a.xlsx"]
    out = verify_source_coverage(task(), materialized_sources=p, parse_receipts=receipts(p))
    assert out["pass"] is False
    assert "DECLARED_SOURCE_NOT_MATERIALIZED:shared/a.xlsx" in out["errors"]


def test_parse_receipt_must_bind_exact_source_bytes():
    p = payloads()
    r = receipts(p)
    r["shared/b.docx"]["source_sha256"] = "0" * 64
    out = verify_source_coverage(task(), materialized_sources=p, parse_receipts=r)
    assert out["pass"] is False
    assert "PARSE_RECEIPT_SOURCE_HASH_MISMATCH:shared/b.docx" in out["errors"]


def test_undeclared_payload_is_rejected_not_silently_added():
    p = payloads()
    p["mystery/extra.txt"] = "x"
    out = verify_source_coverage(task(), materialized_sources=p, parse_receipts=receipts(p))
    assert out["pass"] is False
    assert "UNDECLARED_SOURCE_PAYLOAD:mystery/extra.txt" in out["errors"]

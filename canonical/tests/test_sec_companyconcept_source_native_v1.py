from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.bound_capabilities import sec_companyconcept_source_native as p
from canonical.runtime import sec_companyconcept_source_native_verify_v1 as v
from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir


def _payload():
    return {
        "cik": 320193,
        "taxonomy": "us-gaap",
        "tag": "GrossProfit",
        "label": "Gross Profit",
        "description": "Revenue less cost of goods and services sold.",
        "entityName": "Apple Inc.",
        "units": {
            "USD": [
                {
                    "start": "2025-09-29",
                    "end": "2026-09-26",
                    "val": 100,
                    "accn": "0000320193-26-000001",
                    "fy": 2026,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-10-01",
                    "frame": "CY2026",
                }
            ]
        },
    }


def _config():
    return {
        "cik": 320193,
        "taxonomy": "us-gaap",
        "tag": "GrossProfit",
        "sec_user_agent": "ProjectBrain research@example.com",
    }


def _write_config(root: Path, config=None):
    path = root / "canonical/tmp/sec_companyconcept_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config or _config()), encoding="utf-8")
    return path


def _args():
    return {
        "config_path": "canonical/tmp/sec_companyconcept_config.json",
        "raw_output_path": "canonical/tmp/sec_companyconcept_raw.json",
        "semantic_output_path": "canonical/tmp/sec_companyconcept_semantic.json",
    }


def _fake_fetch(payload=None, *, final_url=None, content_type="application/json"):
    raw = json.dumps(payload or _payload(), separators=(",", ":")).encode("utf-8")

    def fetch(url, user_agent, timeout, max_bytes):
        return raw, final_url or url, content_type, 200

    return fetch


def test_standard_concept_emits_source_traceable_semantics(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    monkeypatch.setattr(p, "_fetch", _fake_fetch())
    out = p.run(_args(), tmp_path)
    assert out["output_verified"] is True
    assert out["concept_qname"] == "us-gaap:GrossProfit"
    assert out["source_native_identity_extracted"] is True
    assert out["semantic_authority_claimed"] is False
    assert out["custom_taxonomy_covered"] is False
    assert out["raw_prose_wsd_claimed"] is False
    semantic = json.loads((tmp_path / _args()["semantic_output_path"]).read_text())
    ir = compile_semantic_ir(semantic["semantic_contract"])
    assert ir["status"] == "COMPILED"
    check = v.verify(
        root=tmp_path,
        raw_path=_args()["raw_output_path"],
        semantic_path=_args()["semantic_output_path"],
    )
    assert check["verified"] is True, check
    assert check["concept_qname"] == "us-gaap:GrossProfit"


def test_custom_taxonomy_is_outside_v1(monkeypatch, tmp_path: Path):
    config = _config()
    config.update({"taxonomy": "aroc", "tag": "GrossMargin"})
    _write_config(tmp_path, config)
    monkeypatch.setattr(p, "_fetch", _fake_fetch())
    try:
        p.run(_args(), tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "TAXONOMY_OUTSIDE_V1_STANDARD_SCOPE"
    else:
        raise AssertionError("custom taxonomy must fail closed")


def test_declared_sec_user_agent_contact_is_required(monkeypatch, tmp_path: Path):
    config = _config()
    config["sec_user_agent"] = "ProjectBrain"
    _write_config(tmp_path, config)
    monkeypatch.setattr(p, "_fetch", _fake_fetch())
    try:
        p.run(_args(), tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED"
    else:
        raise AssertionError("undeclared automated client must fail closed")


def test_payload_identity_mismatch_fails_closed(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    payload = _payload()
    payload["tag"] = "OperatingIncomeLoss"
    monkeypatch.setattr(p, "_fetch", _fake_fetch(payload))
    try:
        p.run(_args(), tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "PAYLOAD_TAG_MISMATCH"
    else:
        raise AssertionError("payload identity mismatch must fail closed")


def test_redirect_away_from_canonical_endpoint_fails_closed(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    monkeypatch.setattr(
        p,
        "_fetch",
        _fake_fetch(final_url="https://www.sec.gov/not-the-companyconcept-endpoint"),
    )
    try:
        p.run(_args(), tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "SEC_FINAL_URL_MISMATCH"
    else:
        raise AssertionError("redirected source identity must fail closed")


def test_verifier_rejects_semantic_identity_tamper(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    monkeypatch.setattr(p, "_fetch", _fake_fetch())
    p.run(_args(), tmp_path)
    semantic_path = tmp_path / _args()["semantic_output_path"]
    semantic = json.loads(semantic_path.read_text())
    semantic["concept_qname"] = "us-gaap:OperatingIncomeLoss"
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")
    check = v.verify(
        root=tmp_path,
        raw_path=_args()["raw_output_path"],
        semantic_path=_args()["semantic_output_path"],
    )
    assert check["verified"] is False
    assert "SEMANTIC_FIELD_MISMATCH:concept_qname" in check["errors"]


def test_verifier_rejects_raw_byte_tamper(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    monkeypatch.setattr(p, "_fetch", _fake_fetch())
    p.run(_args(), tmp_path)
    raw_path = tmp_path / _args()["raw_output_path"]
    payload = json.loads(raw_path.read_text())
    payload["entityName"] = "Tampered Entity"
    raw_path.write_text(json.dumps(payload), encoding="utf-8")
    check = v.verify(
        root=tmp_path,
        raw_path=_args()["raw_output_path"],
        semantic_path=_args()["semantic_output_path"],
    )
    assert check["verified"] is False
    assert "SEMANTIC_FIELD_MISMATCH:source_sha256" in check["errors"]


def test_fact_row_limit_fails_instead_of_truncating(monkeypatch, tmp_path: Path):
    _write_config(tmp_path)
    payload = _payload()
    payload["units"]["USD"].append(
        dict(payload["units"]["USD"][0], accn="0000320193-26-000002")
    )
    monkeypatch.setattr(p, "_fetch", _fake_fetch(payload))
    args = _args()
    args["max_rows"] = 1
    try:
        p.run(args, tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "FACT_ROW_LIMIT_EXCEEDED"
    else:
        raise AssertionError("row limit must fail, never silently truncate")

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from canonical.runtime.bound_capabilities import sec_inline_xbrl_fact_anchor_v1 as p
from canonical.runtime import sec_inline_xbrl_fact_anchor_verify_v1 as v
from canonical.runtime import source_traceable_semantic_ir as semantic_ir


URL = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"
UA = "Project Brain test contact@example.com"


def _raw(*, custom: bool = True) -> bytes:
    extra_ns = ' xmlns:aapl="https://www.apple.com/20250927"' if custom else ""
    extra_fact = (
        '<ix:nonNumeric id="f2" name="aapl:CustomDisclosure" '
        'contextRef="c2">bounded custom text</ix:nonNumeric>'
        if custom
        else ""
    )
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
        'xmlns:us-gaap="http://fasb.org/us-gaap/2025"'
        + extra_ns
        + '><body>'
        '<div>Gross margin</div>'
        '<ix:nonFraction id="f1" name="us-gaap:GrossProfit" '
        'contextRef="c1" unitRef="USD" decimals="-6">195201000000</ix:nonFraction>'
        + extra_fact
        + '</body></html>'
    ).encode("utf-8")


class _Response:
    def __init__(
        self,
        raw: bytes,
        *,
        url: str = URL,
        content_type: str = "text/html; charset=utf-8",
        status: int = 200,
    ):
        self.raw = raw
        self.url = url
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self.raw if n < 0 else self.raw[:n]

    def geturl(self):
        return self.url


def _config(root: Path, url: str = URL) -> Path:
    path = root / "canonical/tmp/ix_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"filing_url": url, "sec_user_agent": UA}),
        encoding="utf-8",
    )
    return path


def _args():
    return {
        "config_path": "canonical/tmp/ix_config.json",
        "raw_output_path": "canonical/tmp/filing.htm",
        "semantic_output_path": "canonical/tmp/ix_semantic.json",
    }


def _run(root: Path, raw: bytes | None = None):
    raw = _raw() if raw is None else raw
    _config(root)
    with patch.object(
        p.urllib.request,
        "urlopen",
        return_value=_Response(raw),
    ):
        return p.run(_args(), root)


def test_standard_and_custom_fact_occurrences_bind_exact_qnames(tmp_path: Path):
    out = _run(tmp_path)
    assert out["fact_anchor_count"] == 2
    assert out["source_native_fact_identity_proved"] is True
    assert out["anchors"][0]["lexical_qname"] == "us-gaap:GrossProfit"
    assert out["anchors"][0]["namespace_uri"] == "http://fasb.org/us-gaap/2025"
    assert out["anchors"][1]["lexical_qname"] == "aapl:CustomDisclosure"
    assert out["anchors"][1]["namespace_uri"] == "https://www.apple.com/20250927"


def test_custom_identity_does_not_mint_custom_domain_semantics(tmp_path: Path):
    out = _run(tmp_path)
    assert out["custom_concept_domain_semantics_claimed"] is False
    assert out["semantic_truth_authority"] is False
    contract = out["semantic_contract"]
    predicates = {x["predicate"] for x in contract["facts"]}
    assert "profit_related" not in predicates
    assert "ontology_class" not in predicates


def test_nearby_visible_label_is_not_claimed_as_semantic_identity(tmp_path: Path):
    out = _run(tmp_path)
    assert out["nearby_visible_label_semantics_claimed"] is False
    dumped = json.dumps(out["semantic_contract"], sort_keys=True)
    assert "Gross margin" not in dumped
    assert "source_declares_xbrl_concept" in dumped


def test_independent_verifier_rederives_complete_contract(tmp_path: Path):
    _run(tmp_path)
    verdict = v.verify(
        root=tmp_path,
        raw_path="canonical/tmp/filing.htm",
        semantic_path="canonical/tmp/ix_semantic.json",
    )
    assert verdict["verified"] is True, verdict
    assert verdict["producer_independent"] is True
    assert verdict["full_contract_rederived_from_raw_bytes"] is True
    assert verdict["fact_anchor_count"] == 2


def test_source_traceable_semantic_ir_accepts_anchor_contract(tmp_path: Path):
    out = _run(tmp_path)
    compiled = semantic_ir.compile_semantic_ir(out["semantic_contract"])
    assert compiled["status"] == "COMPILED", compiled
    relations = compiled["relations"]
    assert any(
        x["predicate"] == "source_declares_xbrl_concept"
        and "GrossProfit" in x["object"]
        for x in relations
    )


def test_tampered_qname_contract_is_rejected(tmp_path: Path):
    _run(tmp_path)
    semantic_path = tmp_path / "canonical/tmp/ix_semantic.json"
    doc = json.loads(semantic_path.read_text(encoding="utf-8"))
    doc["anchors"][0]["local_name"] = "OperatingIncomeLoss"
    semantic_path.write_text(json.dumps(doc), encoding="utf-8")
    verdict = v.verify(
        root=tmp_path,
        raw_path="canonical/tmp/filing.htm",
        semantic_path="canonical/tmp/ix_semantic.json",
    )
    assert verdict["verified"] is False
    assert "SEMANTIC_FIELD_MISMATCH:anchors" in verdict["errors"]


def test_tampered_relation_is_rejected(tmp_path: Path):
    _run(tmp_path)
    semantic_path = tmp_path / "canonical/tmp/ix_semantic.json"
    doc = json.loads(semantic_path.read_text(encoding="utf-8"))
    doc["semantic_contract"]["relations"][0]["object"] = (
        "XBRL_CONCEPT:{http://fasb.org/us-gaap/2025}OperatingIncomeLoss"
    )
    semantic_path.write_text(json.dumps(doc), encoding="utf-8")
    verdict = v.verify(
        root=tmp_path,
        raw_path="canonical/tmp/filing.htm",
        semantic_path="canonical/tmp/ix_semantic.json",
    )
    assert verdict["verified"] is False
    assert "SEMANTIC_CONTRACT_NOT_EXACTLY_DERIVED_FROM_SOURCE_BYTES" in verdict["errors"]


def test_unbound_qname_prefix_fails_closed(tmp_path: Path):
    raw = _raw(custom=False).replace(
        b'name="us-gaap:GrossProfit"',
        b'name="unknown:GrossProfit"',
    )
    _config(tmp_path)
    with patch.object(p.urllib.request, "urlopen", return_value=_Response(raw)):
        with pytest.raises(p.InlineXbrlError, match="QNAME_PREFIX_UNBOUND"):
            p.run(_args(), tmp_path)


def test_namespace_rebinding_fails_closed(tmp_path: Path):
    raw = _raw(custom=False).replace(
        b"<body>",
        b'<body xmlns:us-gaap="https://evil.example/gaap">',
    )
    _config(tmp_path)
    with patch.object(p.urllib.request, "urlopen", return_value=_Response(raw)):
        with pytest.raises(p.InlineXbrlError, match="NESTED_NAMESPACE_DECLARATION_OUTSIDE_V1"):
            p.run(_args(), tmp_path)



def test_late_namespace_declaration_cannot_retroactively_bind_prefix(tmp_path: Path):
    raw = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body>'
        '<ix:nonFraction name="late:GrossProfit" contextRef="c1">1</ix:nonFraction>'
        '<div xmlns:late="http://fasb.org/us-gaap/2025"></div>'
        '</body></html>'
    ).encode()
    _config(tmp_path)
    with patch.object(p.urllib.request, "urlopen", return_value=_Response(raw)):
        with pytest.raises(p.InlineXbrlError, match="NESTED_NAMESPACE_DECLARATION_OUTSIDE_V1"):
            p.run(_args(), tmp_path)

def test_redirect_is_rejected(tmp_path: Path):
    _config(tmp_path)
    redirected = URL.replace("www.sec.gov", "example.com")
    with patch.object(
        p.urllib.request,
        "urlopen",
        return_value=_Response(_raw(), url=redirected),
    ):
        with pytest.raises(p.InlineXbrlError, match="SEC_FINAL_URL_MISMATCH"):
            p.run(_args(), tmp_path)


def test_non_sec_source_is_rejected_before_network(tmp_path: Path):
    _config(tmp_path, "https://example.com/aapl.htm")
    with patch.object(p.urllib.request, "urlopen") as call:
        with pytest.raises(p.InlineXbrlError, match="SEC_ARCHIVE_INLINE_FILING_URL_REQUIRED"):
            p.run(_args(), tmp_path)
        call.assert_not_called()


def test_no_inline_fact_fails_closed(tmp_path: Path):
    raw = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        "<body>Gross margin 195201</body></html>"
    ).encode()
    _config(tmp_path)
    with patch.object(p.urllib.request, "urlopen", return_value=_Response(raw)):
        with pytest.raises(p.InlineXbrlError, match="NO_SUPPORTED_INLINE_XBRL_FACTS"):
            p.run(_args(), tmp_path)


def test_scope_flags_cannot_be_self_promoted_without_verifier_failure(tmp_path: Path):
    _run(tmp_path)
    semantic_path = tmp_path / "canonical/tmp/ix_semantic.json"
    doc = json.loads(semantic_path.read_text(encoding="utf-8"))
    doc["raw_prose_wsd_claimed"] = True
    doc["policy_adequacy_authority"] = True
    semantic_path.write_text(json.dumps(doc), encoding="utf-8")
    verdict = v.verify(
        root=tmp_path,
        raw_path="canonical/tmp/filing.htm",
        semantic_path="canonical/tmp/ix_semantic.json",
    )
    assert verdict["verified"] is False
    assert "AUTHORITY_BOUNDARY_INVALID:raw_prose_wsd_claimed" in verdict["errors"]
    assert "AUTHORITY_BOUNDARY_INVALID:policy_adequacy_authority" in verdict["errors"]

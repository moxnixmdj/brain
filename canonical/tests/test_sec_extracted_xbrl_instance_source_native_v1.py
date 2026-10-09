from __future__ import annotations

import json
from unittest.mock import patch
import pytest

from canonical.runtime.bound_capabilities import sec_extracted_xbrl_instance_source_native_v1 as p
from canonical.runtime import sec_extracted_xbrl_instance_source_native_verify_v1 as v

URL = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927_htm.xml"
UA = "ProjectBrain test@example.com"

RAW = b'''<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
 xmlns:us-gaap="http://fasb.org/us-gaap/2025"
 xmlns:aapl="https://www.apple.com/20250927"
 xmlns:dei="http://xbrl.sec.gov/dei/2025">
 <xbrli:context id="c1">
   <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>
   <xbrli:period><xbrli:startDate>2024-09-29</xbrli:startDate><xbrli:endDate>2025-09-27</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <xbrli:context id="c2">
   <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>
    <xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">aapl:ExampleMember</xbrldi:explicitMember></xbrli:segment>
   </xbrli:entity>
   <xbrli:period><xbrli:instant>2025-09-27</xbrli:instant></xbrli:period>
 </xbrli:context>
 <xbrli:context id="c3">
   <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>
    <xbrli:segment><xbrldi:typedMember dimension="aapl:TypedAxis"><aapl:TypedDomain>Alpha</aapl:TypedDomain></xbrldi:typedMember></xbrli:segment>
   </xbrli:entity>
   <xbrli:period><xbrli:forever/></xbrli:period>
 </xbrli:context>
 <xbrli:unit id="USD"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
 <xbrli:unit id="USDPerShare"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>
 <us-gaap:GrossProfit contextRef="c1" unitRef="USD" decimals="-6">195201000000</us-gaap:GrossProfit>
 <aapl:CustomMetric contextRef="c2" unitRef="USDPerShare" decimals="2">1.25</aapl:CustomMetric>
 <dei:EntityPublicFloat contextRef="c3" xsi:nil="true"/>
</xbrli:xbrl>
'''

class Response:
    def __init__(self, raw=RAW, url=URL, status=200, ctype="application/xml"):
        self.raw, self.url, self.status = raw, url, status
        self.headers = {"Content-Type": ctype}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read(self, n=-1): return self.raw if n < 0 else self.raw[:n]

def setup(tmp_path, raw=RAW, final_url=URL, ctype="application/xml"):
    (tmp_path/"cfg.json").write_text(json.dumps({"instance_url": URL, "sec_user_agent": UA}))
    def fake(req, timeout=30):
        return Response(raw, final_url, 200, ctype)
    with patch.object(p.urllib.request, "urlopen", side_effect=fake):
        return p.run(
            {"config_path":"cfg.json","raw_output_path":"raw.xml","semantic_output_path":"sem.json"},
            tmp_path,
        )

def test_exact_qnames_context_period_and_numeric_normalization(tmp_path):
    out = setup(tmp_path)
    assert out["fact_count"] == 3
    g = out["facts"][0]
    assert g["concept_qname"] == "{http://fasb.org/us-gaap/2025}GrossProfit"
    assert g["context"]["entity"]["identifier"] == "0000320193"
    assert g["context"]["period"] == {"kind":"duration","start":"2024-09-29","end":"2025-09-27"}
    assert g["normalized_decimal"] == "195201000000"

def test_custom_fact_explicit_dimension_and_divide_unit(tmp_path):
    out = setup(tmp_path)
    f = out["facts"][1]
    assert f["concept_qname"] == "{https://www.apple.com/20250927}CustomMetric"
    d = f["context"]["dimensions"][0]
    assert d["dimension"] == "{http://fasb.org/us-gaap/2025}StatementBusinessSegmentsAxis"
    assert d["member"] == "{https://www.apple.com/20250927}ExampleMember"
    assert f["unit"]["kind"] == "divide"
    assert f["unit"]["denominator"] == ["{http://www.xbrl.org/2003/instance}shares"]
    assert out["custom_concept_domain_semantics_claimed"] is False

def test_typed_dimension_forever_and_nil(tmp_path):
    out = setup(tmp_path)
    f = out["facts"][2]
    assert f["context"]["period"] == {"kind":"forever"}
    d = f["context"]["dimensions"][0]
    assert d["kind"] == "typed"
    assert d["typed_value_qname"] == "{https://www.apple.com/20250927}TypedDomain"
    assert d["typed_text"] == "Alpha"
    assert f["nil"] is True and f["normalized_decimal"] is None

def test_independent_verifier_rederives_exact_contract(tmp_path):
    setup(tmp_path)
    got = v.verify(root=tmp_path, raw_path="raw.xml", semantic_path="sem.json")
    assert got["verified"], got
    assert got["fact_count"] == 3
    assert got["producer_independent"] is True

def test_tampered_value_fails_verifier(tmp_path):
    setup(tmp_path)
    sem = json.loads((tmp_path/"sem.json").read_text())
    sem["facts"][0]["lexical_value"] = "1"
    (tmp_path/"sem.json").write_text(json.dumps(sem))
    got = v.verify(root=tmp_path, raw_path="raw.xml", semantic_path="sem.json")
    assert not got["verified"]
    assert "SEMANTIC_FIELD_MISMATCH:facts" in got["errors"]

def test_dtd_entity_rejected(tmp_path):
    bad = b'<!DOCTYPE x [<!ENTITY e "x">]>' + RAW
    with pytest.raises(p.ExtractedInstanceError, match="DTD_OR_ENTITY_FORBIDDEN"):
        setup(tmp_path, bad)

def test_redirect_rejected(tmp_path):
    with pytest.raises(p.ExtractedInstanceError, match="SEC_FINAL_URL_MISMATCH"):
        setup(tmp_path, RAW, "https://www.sec.gov/Archives/edgar/data/1/other_htm.xml")

@pytest.mark.parametrize("url",[
    "http://www.sec.gov/Archives/edgar/data/1/a_htm.xml",
    "https://example.com/Archives/edgar/data/1/a_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1/a.xml",
])
def test_bad_source_url_rejected(tmp_path, url):
    (tmp_path/"cfg.json").write_text(json.dumps({"instance_url":url,"sec_user_agent":UA}))
    with pytest.raises(p.ExtractedInstanceError, match="SEC_ARCHIVE_EXTRACTED_INSTANCE_URL_REQUIRED"):
        p.run({"config_path":"cfg.json","raw_output_path":"raw.xml","semantic_output_path":"sem.json"}, tmp_path)

def test_unbound_dimension_prefix_rejected(tmp_path):
    bad = RAW.replace(b'us-gaap:StatementBusinessSegmentsAxis', b'nope:Axis')
    with pytest.raises(p.ExtractedInstanceError, match="QNAME_PREFIX_UNBOUND"):
        setup(tmp_path, bad)

def test_authority_boundaries_zero(tmp_path):
    out = setup(tmp_path)
    assert out["source_native_instance_fact_semantics_proved"] is True
    for key in [
        "inline_transform_semantics_reimplemented",
        "custom_concept_domain_semantics_claimed",
        "nearby_visible_label_semantics_claimed",
        "raw_prose_wsd_claimed",
        "ontology_classification_claimed",
        "policy_adequacy_authority",
        "semantic_truth_authority",
        "terminal_authority",
    ]:
        assert out[key] is False
    assert out["terminal_credit_delta"] == 0

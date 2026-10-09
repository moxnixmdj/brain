from __future__ import annotations
import json
from unittest.mock import patch
import pytest
from canonical.runtime.bound_capabilities import sec_issuer_extension_concept_semantics_v1 as p
from canonical.runtime import sec_issuer_extension_concept_semantics_verify_v1 as v

XSD_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.xsd"
LAB_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928_lab.xml"
NS="https://www.apple.com/20240928"
LOCAL="LesseeOperatingAndFinanceLeaseLiabilityToBePaid"
DOC="Amount of lessee's undiscounted obligation for lease payments for operating and finance leases."
UA="ProjectBrain test@example.com"
XSD=f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 targetNamespace="{NS}">
 <xs:element id="aapl_{LOCAL}" name="{LOCAL}" type="xbrli:monetaryItemType"
  substitutionGroup="xbrli:item" xbrli:periodType="instant" xbrli:balance="credit"
  abstract="false" nillable="true"/>
</xs:schema>""".encode()
LAB=f"""<?xml version="1.0"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator" xlink:href="aapl-20240928.xsd#aapl_{LOCAL}" xlink:label="loc"/>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="std">Operating and finance lease payments due</link:label>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc">{DOC}</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="std"/>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
</link:linkbase>""".encode()

class Resp:
    def __init__(self,raw,url,ctype="application/xml",status=200):
        self.raw,self.url,self.status=raw,url,status
        self.headers={"Content-Type":ctype}
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n=-1): return self.raw if n<0 else self.raw[:n]
    def geturl(self): return self.url

def args():
    return {
        "config_path":"cfg.json",
        "xsd_output_path":"xsd.xml",
        "label_output_path":"lab.xml",
        "semantic_output_path":"sem.json",
    }

def setup(tmp_path,xsd=XSD,lab=LAB,redirect=False):
    (tmp_path/"cfg.json").write_text(json.dumps({
        "xsd_url":XSD_URL,
        "label_url":LAB_URL,
        "concept_namespace":NS,
        "local_name":LOCAL,
        "sec_user_agent":UA,
    }))
    def fake(req,timeout=30):
        url=req.full_url
        if url==XSD_URL: return Resp(xsd,url)
        if url==LAB_URL: return Resp(lab,"https://example.com/tampered.xml" if redirect else url)
        raise AssertionError(url)
    with patch.object(p.urllib.request,"urlopen",side_effect=fake):
        return p.run(args(),tmp_path)

def test_exact_custom_concept_metadata_and_documentation(tmp_path):
    out=setup(tmp_path)
    assert out["issuer_extension_documentation_semantics_proved"] is True
    assert out["concept_qname"]=="{"+NS+"}"+LOCAL
    assert out["concept_metadata"]["xsd_type"]=="xbrli:monetaryItemType"
    assert out["concept_metadata"]["period_type"]=="instant"
    assert out["concept_metadata"]["balance"]=="credit"
    assert out["documentation_label"]==DOC
    assert out["semantic_truth_authority"] is False

def test_independent_verifier_rederives_raw_bytes(tmp_path):
    setup(tmp_path)
    got=v.verify(root=tmp_path,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
    assert got["verified"] is True,got
    assert got["producer_independent"] is True

def test_namespace_mismatch_fails(tmp_path):
    bad=XSD.replace(NS.encode(),b"https://example.com/wrong")
    with pytest.raises(p.ExtensionConceptError,match="XSD_TARGET_NAMESPACE_MISMATCH"):
        setup(tmp_path,xsd=bad)

def test_missing_concept_fails(tmp_path):
    bad=XSD.replace(LOCAL.encode(),b"OtherConcept")
    with pytest.raises(p.ExtensionConceptError,match="XSD_CONCEPT_NOT_UNIQUE"):
        setup(tmp_path,xsd=bad)

def test_wrong_documentation_locator_fails(tmp_path):
    bad=LAB.replace(("aapl_"+LOCAL).encode(),b"aapl_OtherConcept")
    with pytest.raises(p.ExtensionConceptError,match="DOCUMENTATION_LABEL_NOT_UNIQUE"):
        setup(tmp_path,lab=bad)

def test_conflicting_documentation_fails(tmp_path):
    extra='<link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc2">Different issuer definition.</link:label><link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc2"/>'.encode()
    bad=LAB.replace(b"</link:labelLink>",extra+b"</link:labelLink>")
    with pytest.raises(p.ExtensionConceptError,match="DOCUMENTATION_LABEL_NOT_UNIQUE"):
        setup(tmp_path,lab=bad)

def test_dtd_entity_rejected(tmp_path):
    bad=b'<!DOCTYPE x [<!ENTITY e "x">]>'+XSD
    with pytest.raises(p.ExtensionConceptError,match="XSD_DTD_OR_ENTITY_FORBIDDEN"):
        setup(tmp_path,xsd=bad)

def test_redirect_rejected(tmp_path):
    with pytest.raises(p.ExtensionConceptError,match="LABEL_FINAL_URL_MISMATCH"):
        setup(tmp_path,redirect=True)

def test_cross_directory_pair_rejected(tmp_path):
    cfg={
        "xsd_url":XSD_URL,
        "label_url":"https://www.sec.gov/Archives/edgar/data/320193/OTHER/a_lab.xml",
        "concept_namespace":NS,
        "local_name":LOCAL,
        "sec_user_agent":UA,
    }
    (tmp_path/"cfg.json").write_text(json.dumps(cfg))
    with pytest.raises(p.ExtensionConceptError,match="SEC_EXTENSION_FILES_MUST_SHARE_ARCHIVE_DIRECTORY"):
        p.run(args(),tmp_path)

def test_verifier_rejects_metadata_tamper(tmp_path):
    setup(tmp_path)
    q=tmp_path/"sem.json"
    d=json.loads(q.read_text())
    d["documentation_label"]="invented"
    q.write_text(json.dumps(d))
    got=v.verify(root=tmp_path,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
    assert got["verified"] is False
    assert "SEMANTIC_FIELD_MISMATCH:documentation_label" in got["errors"]

def test_verifier_rejects_authority_self_promotion(tmp_path):
    setup(tmp_path)
    q=tmp_path/"sem.json"
    d=json.loads(q.read_text())
    d["semantic_truth_authority"]=True
    q.write_text(json.dumps(d))
    got=v.verify(root=tmp_path,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
    assert got["verified"] is False
    assert "AUTHORITY_BOUNDARY_INVALID:semantic_truth_authority" in got["errors"]

def test_standard_taxonomy_namespace_is_outside_route(tmp_path):
    cfg={
        "xsd_url":XSD_URL,
        "label_url":LAB_URL,
        "concept_namespace":"http://fasb.org/us-gaap/2024",
        "local_name":LOCAL,
        "sec_user_agent":UA,
    }
    (tmp_path/"cfg.json").write_text(json.dumps(cfg))
    with pytest.raises(p.ExtensionConceptError,match="ISSUER_EXTENSION_NAMESPACE_REQUIRED"):
        p.run(args(),tmp_path)

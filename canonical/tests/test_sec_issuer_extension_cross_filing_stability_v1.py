from __future__ import annotations

import json
from unittest.mock import patch

from canonical.runtime.bound_capabilities import sec_issuer_extension_concept_semantics_v1 as producer
from canonical.runtime import sec_issuer_extension_cross_filing_stability_v1 as stable

LOCAL="LesseeOperatingAndFinanceLeaseLiabilityToBePaid"
DOC="Amount of lessee's undiscounted obligation for lease payments for operating and finance leases."
STD="Lessee, Operating and Finance Lease, Liability, To Be Paid"
UA="ProjectBrain test@example.com"

class Resp:
    def __init__(self,raw,url,ctype="application/xml",status=200):
        self.raw,self.url,self.status=raw,url,status
        self.headers={"Content-Type":ctype}
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n=-1): return self.raw if n<0 else self.raw[:n]
    def geturl(self): return self.url

def xsd(ns,local=LOCAL,balance="credit"):
    return f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 targetNamespace="{ns}">
 <xs:element id="aapl_{local}" name="{local}" type="xbrli:monetaryItemType"
  substitutionGroup="xbrli:item" xbrli:periodType="instant" xbrli:balance="{balance}"
  abstract="false" nillable="true"/>
</xs:schema>""".encode()

def lab(local=LOCAL,doc=DOC,std=STD):
    return f"""<?xml version="1.0"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator" xlink:href="aapl.xsd#aapl_{local}" xlink:label="loc"/>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="std">{std}</link:label>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc">{doc}</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="std"/>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
</link:linkbase>""".encode()

def make(root,name,*,cik="320193",accession,date,local=LOCAL,doc=DOC,std=STD,balance="credit"):
    directory=f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}"
    xu=directory+f"/aapl-{date}.xsd"
    lu=directory+f"/aapl-{date}_lab.xml"
    ns=f"http://www.apple.com/{date}"
    cfg=root/f"{name}-cfg.json"
    cfg.write_text(json.dumps({
        "xsd_url":xu,"label_url":lu,"concept_namespace":ns,
        "local_name":local,"sec_user_agent":UA,
    }))
    xr=xsd(ns,local=local,balance=balance)
    lr=lab(local=local,doc=doc,std=std)
    def fake(req,timeout=30):
        if req.full_url==xu: return Resp(xr,xu)
        if req.full_url==lu: return Resp(lr,lu)
        raise AssertionError(req.full_url)
    with patch.object(producer.urllib.request,"urlopen",side_effect=fake):
        out=producer.run({
            "config_path":cfg.name,
            "xsd_output_path":f"{name}.xsd",
            "label_output_path":f"{name}_lab.xml",
            "semantic_output_path":f"{name}.json",
        },root)
    assert out["issuer_extension_documentation_semantics_proved"] is True
    return {
        "xsd":f"{name}.xsd","label":f"{name}_lab.xml","semantic":f"{name}.json",
        "out":out,
    }

def compare(root,left,right):
    return stable.verify_pair(
        root=root,
        left_xsd_path=left["xsd"],left_label_path=left["label"],left_semantic_path=left["semantic"],
        right_xsd_path=right["xsd"],right_label_path=right["label"],right_semantic_path=right["semantic"],
    )

def test_same_contract_across_distinct_filings_is_proved(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927")
    out=compare(tmp_path,a,b)
    assert out["pass"] is True,out
    assert out["cross_filing_semantic_contract_stable"] is True
    assert out["cross_filing_semantic_stability_authority"] is True
    assert out["relation"]=="SAME_BRAIN_OWNED_SEMANTIC_CONTRACT_ACROSS_TWO_FILINGS"
    assert a["out"]["concept_qname"]!=b["out"]["concept_qname"]
    assert out["concept_identity_authority"] is False
    assert out["future_stability_claimed"] is False

def test_documentation_change_is_detected_not_hidden(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927",doc=DOC+" Changed.")
    out=compare(tmp_path,a,b)
    assert out["pass"] is True,out
    assert out["cross_filing_semantic_contract_stable"] is False
    assert out["relation"]=="SEMANTIC_CONTRACT_DIFFERS_ACROSS_FILINGS"
    assert "documentation_label" in out["differing_fields"]

def test_xsd_semantic_change_is_detected(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927",balance="debit")
    out=compare(tmp_path,a,b)
    assert out["pass"] is True,out
    assert out["cross_filing_semantic_contract_stable"] is False
    assert "semantic_metadata" in out["differing_fields"]

def test_different_local_name_is_out_of_scope(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927",local="OtherConcept")
    out=compare(tmp_path,a,b)
    assert out["pass"] is False
    assert out["reason"]=="LOCAL_NAME_MISMATCH"

def test_cross_issuer_comparison_fails_closed(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",cik="789019",accession="000078901925000001",date="20250927")
    out=compare(tmp_path,a,b)
    assert out["pass"] is False
    assert out["reason"]=="CROSS_ISSUER_COMPARISON_FORBIDDEN"

def test_same_filing_directory_is_not_cross_filing(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019324000123",date="20240928")
    out=compare(tmp_path,a,b)
    assert out["pass"] is False
    assert out["reason"]=="DISTINCT_FILING_DIRECTORIES_REQUIRED"

def test_tampered_semantic_document_cannot_mint_stability(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927")
    p=tmp_path/b["semantic"]
    obj=json.loads(p.read_text())
    obj["documentation_label"]="invented"
    p.write_text(json.dumps(obj))
    out=compare(tmp_path,a,b)
    assert out["pass"] is False
    assert out["reason"]=="UPSTREAM_CONCEPT_SEMANTICS_REDERIVATION_FAILED"

def test_no_identity_standard_equivalence_or_terminal_credit(tmp_path):
    a=make(tmp_path,"a",accession="000032019324000123",date="20240928")
    b=make(tmp_path,"b",accession="000032019325000079",date="20250927")
    out=compare(tmp_path,a,b)
    assert out["pass"] is True,out
    assert out["concept_identity_authority"] is False
    assert out["standard_taxonomy_equivalence_authority"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["acceptance_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0

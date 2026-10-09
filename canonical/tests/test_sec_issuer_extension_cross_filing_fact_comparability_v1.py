from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.bound_capabilities import sec_issuer_extension_concept_semantics_v1 as concept_prod
from canonical.runtime.bound_capabilities import sec_extracted_xbrl_instance_source_native_v1 as instance_prod
from canonical.runtime import sec_issuer_extension_cross_filing_fact_comparability_v1 as compare

LOCAL="CustomMetric"
DOC="Issuer-defined custom metric for the bounded test."
STD="Custom Metric"
UA="ProjectBrain test@example.com"
USD="http://www.xbrl.org/2003/iso4217"
XBRLI="http://www.xbrl.org/2003/instance"

class Resp:
    def __init__(self,raw,url,ctype="application/xml",status=200):
        self.raw,self.url,self.status=raw,url,status
        self.headers={"Content-Type":ctype}
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n=-1): return self.raw if n<0 else self.raw[:n]
    def geturl(self): return self.url

def concept_xsd(ns, balance="credit"):
    return f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xbrli="{XBRLI}" targetNamespace="{ns}">
 <xs:element id="aapl_{LOCAL}" name="{LOCAL}" type="xbrli:monetaryItemType"
  substitutionGroup="xbrli:item" xbrli:periodType="instant" xbrli:balance="{balance}"
  abstract="false" nillable="true"/>
</xs:schema>""".encode()

def concept_lab(doc=DOC,std=STD):
    return f"""<?xml version="1.0"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator" xlink:href="aapl.xsd#aapl_{LOCAL}" xlink:label="loc"/>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="std">{std}</link:label>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc">{doc}</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="std"/>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
</link:linkbase>""".encode()

def instance_xml(ns, instant, value, *, cik="0000320193", unit="USD", dimension=None, duration=None):
    period=(
        f"<xbrli:startDate>{duration[0]}</xbrli:startDate><xbrli:endDate>{duration[1]}</xbrli:endDate>"
        if duration else f"<xbrli:instant>{instant}</xbrli:instant>"
    )
    segment=(
        f'<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">{dimension}</xbrldi:explicitMember></xbrli:segment>'
        if dimension else ""
    )
    measure="iso4217:USD" if unit=="USD" else "iso4217:EUR"
    return f"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="{XBRLI}"
 xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
 xmlns:iso4217="{USD}"
 xmlns:us-gaap="http://fasb.org/us-gaap/2025"
 xmlns:aapl="{ns}">
 <xbrli:context id="c1">
  <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>{segment}</xbrli:entity>
  <xbrli:period>{period}</xbrli:period>
 </xbrli:context>
 <xbrli:unit id="U"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>
 <aapl:{LOCAL} contextRef="c1" unitRef="U" decimals="-6">{value}</aapl:{LOCAL}>
</xbrli:xbrl>""".encode()

def build_side(root, name, accession, date_text, value, *, doc=DOC, balance="credit",
               cik="0000320193", unit="USD", dimension=None, duration=None):
    directory=f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0') or '0'}/{accession}"
    ns=f"http://www.apple.com/{date_text}"
    xu=directory+f"/aapl-{date_text}.xsd"
    lu=directory+f"/aapl-{date_text}_lab.xml"
    iu=directory+f"/aapl-{date_text}_htm.xml"
    cx=concept_xsd(ns,balance=balance); cl=concept_lab(doc=doc)
    ix=instance_xml(ns,date_text,value,cik=cik,unit=unit,dimension=dimension,duration=duration)

    ccfg=root/f"{name}-concept.json"
    ccfg.write_text(json.dumps({"xsd_url":xu,"label_url":lu,"concept_namespace":ns,"local_name":LOCAL,"sec_user_agent":UA}))
    def cfetch(req,timeout=30):
        if req.full_url==xu:return Resp(cx,xu)
        if req.full_url==lu:return Resp(cl,lu)
        raise AssertionError(req.full_url)
    with patch.object(concept_prod.urllib.request,"urlopen",side_effect=cfetch):
        cout=concept_prod.run({
            "config_path":ccfg.name,
            "xsd_output_path":f"{name}.xsd",
            "label_output_path":f"{name}_lab.xml",
            "semantic_output_path":f"{name}_concept.json",
        },root)

    icfg=root/f"{name}-instance.json"
    icfg.write_text(json.dumps({"instance_url":iu,"sec_user_agent":UA}))
    def ifetch(req,timeout=30):
        if req.full_url==iu:return Resp(ix,iu)
        raise AssertionError(req.full_url)
    with patch.object(instance_prod.urllib.request,"urlopen",side_effect=ifetch):
        iout=instance_prod.run({
            "config_path":icfg.name,
            "raw_output_path":f"{name}_instance.xml",
            "semantic_output_path":f"{name}_instance.json",
        },root)
    assert cout["issuer_extension_documentation_semantics_proved"] is True
    assert iout["fact_count"]==1
    return {
        "xsd":f"{name}.xsd","lab":f"{name}_lab.xml","concept":f"{name}_concept.json",
        "raw":f"{name}_instance.xml","instance":f"{name}_instance.json","ordinal":0,
    }

def run_pair(root,left,right):
    return compare.verify_comparable_facts(
        root=root,
        left_instance_raw_path=left["raw"],left_instance_semantic_path=left["instance"],
        right_instance_raw_path=right["raw"],right_instance_semantic_path=right["instance"],
        left_concept_xsd_path=left["xsd"],left_concept_label_path=left["lab"],left_concept_semantic_path=left["concept"],
        right_concept_xsd_path=right["xsd"],right_concept_label_path=right["lab"],right_concept_semantic_path=right["concept"],
        left_fact_ordinal=left["ordinal"],right_fact_ordinal=right["ordinal"],
    )

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def base(self,**right):
        l=build_side(self.root,"l","000032019324000123","2024-09-28","14790000000")
        r=build_side(self.root,"r","000032019325000079","2025-09-27","16304000000",**right)
        return l,r

    def test_reported_increase_with_exact_measurement_shape(self):
        l,r=self.base()
        out=run_pair(self.root,l,r)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["cross_filing_fact_measurement_contract_compatible"])
        self.assertTrue(out["reported_value_relation_authority"])
        self.assertEqual(out["reported_value_relation"],"RIGHT_REPORTED_VALUE_GT_LEFT")
        self.assertEqual(out["reported_decimal_change"],"1514000000")
        self.assertFalse(out["underlying_unrounded_value_relation_claimed"])
        self.assertFalse(out["accounting_policy_comparability_claimed"])

    def test_unit_drift_remains_open(self):
        l,r=self.base(unit="EUR")
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__UNIT_MISMATCH")

    def test_entity_drift_remains_open(self):
        l=build_side(self.root,"l","000032019324000123","2024-09-28","1")
        r=build_side(self.root,"r","000032019325000079","2025-09-27","2",cik="0000320194")
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertIn(out["status"],{"FAIL_CLOSED","OPEN__ENTITY_MISMATCH"})

    def test_dimension_drift_remains_open(self):
        l,r=self.base(dimension="us-gaap:ProductMember")
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__DIMENSION_MISMATCH")

    def test_duration_period_not_claimed_comparable_v1(self):
        l=build_side(self.root,"l","000032019324000123","2024-09-28","1",duration=("2023-10-01","2024-09-28"))
        r=build_side(self.root,"r","000032019325000079","2025-09-27","2",duration=("2024-09-29","2025-09-27"))
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__ONLY_INSTANT_PERIOD_COMPARABILITY_SUPPORTED_V1")

    def test_concept_semantic_drift_blocks_comparison(self):
        l,r=self.base(doc=DOC+" Changed.")
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__CONCEPT_SEMANTIC_CONTRACT_NOT_STABLE")

    def test_tampered_instance_semantics_fail_closed(self):
        l,r=self.base()
        p=self.root/r["instance"]
        obj=json.loads(p.read_text())
        obj["facts"][0]["normalized_decimal"]="999"
        p.write_text(json.dumps(obj))
        out=run_pair(self.root,l,r)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"UPSTREAM_INSTANCE_SEMANTICS_REDERIVATION_FAILED")

    def test_zero_authority_overclaims(self):
        l,r=self.base()
        out=run_pair(self.root,l,r)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["standard_taxonomy_equivalence_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)

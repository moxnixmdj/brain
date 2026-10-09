from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from canonical.runtime import sec_inline_xbrl_fasb_release_metadata_v1 as p
from canonical.runtime import sec_inline_xbrl_fasb_release_metadata_verify_v1 as v
from canonical.runtime import source_traceable_semantic_ir as semantic_ir


NS = "http://fasb.org/us-gaap/2025"
DOC = "Revenue less cost of goods and services sold."


def _anchor(*, namespace=NS, local_name="GrossProfit"):
    return {
        "schema":"PROJECT_BRAIN_SEC_INLINE_XBRL_SOURCE_NATIVE_FACT_ANCHOR_V1",
        "status":"PASS__INLINE_XBRL_FACT_QNAME_ANCHORS_EXTRACTED",
        "source_url":"https://www.sec.gov/Archives/edgar/data/320193/000/a.htm",
        "source_path":"canonical/tmp/filing.htm",
        "source_sha256":"1"*64,
        "anchors":[{
            "ordinal":0,
            "ix_kind":"nonfraction",
            "lexical_qname":"us-gaap:"+local_name,
            "namespace_uri":namespace,
            "local_name":local_name,
            "context_ref":"c1",
            "source_line":10,
            "source_column":4,
            "start_tag_sha256":"2"*64,
        }],
        "source_native_fact_identity_proved":True,
        "nearby_visible_label_semantics_claimed":False,
        "custom_concept_domain_semantics_claimed":False,
        "raw_prose_wsd_claimed":False,
        "policy_adequacy_authority":False,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def _xsd(*, namespace=NS, local_name="GrossProfit"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 targetNamespace="{namespace}">
 <xs:element id="us-gaap_{local_name}" name="{local_name}"
  type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"
  xbrli:periodType="duration" xbrli:balance="credit"
  abstract="false" nillable="true"/>
</xs:schema>""".encode()


def _doc(*, local_name="GrossProfit", documentation=DOC):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator"
   xlink:href="us-gaap-2025.xsd#us-gaap_{local_name}"
   xlink:label="loc_{local_name}"/>
  <link:label xlink:type="resource"
   xlink:role="http://www.xbrl.org/2003/role/documentation"
   xlink:label="doc_{local_name}">{documentation}</link:label>
  <link:labelArc xlink:type="arc"
   xlink:from="loc_{local_name}" xlink:to="doc_{local_name}"/>
 </link:labelLink>
</link:linkbase>""".encode()


def _args():
    return {
        "anchor_semantic_path":"canonical/tmp/anchor.json",
        "fact_ordinal":0,
        "xsd_output_path":"canonical/tmp/us-gaap-2025.xsd",
        "documentation_output_path":"canonical/tmp/us-gaap-doc-2025.xml",
        "metadata_output_path":"canonical/tmp/release_metadata.json",
    }


def _write_anchor(root: Path, anchor=None):
    path=root/"canonical/tmp/anchor.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(anchor or _anchor()),encoding="utf-8")


def _fake_fetch(xsd=None, doc=None, *, redirect_doc=False):
    xsd = _xsd() if xsd is None else xsd
    doc = _doc() if doc is None else doc
    def fetch(url, timeout, max_bytes):
        if url.endswith(".xsd"):
            return xsd, url, "application/xml", 200
        final = "https://example.com/tampered.xml" if redirect_doc else url
        return doc, final, "application/xml", 200
    return fetch


def _run(root: Path, *, xsd=None, doc=None):
    _write_anchor(root)
    with patch.object(p,"_fetch",side_effect=_fake_fetch(xsd,doc)):
        return p.run(_args(),root)


def test_exact_release_metadata_binds_to_occurrence(tmp_path:Path):
    out=_run(tmp_path)
    assert out["release_relative_standard_concept_metadata_proved"] is True
    assert out["namespace_uri"]==NS
    assert out["local_name"]=="GrossProfit"
    assert out["release"]=="2025"
    assert out["concept_metadata"]["element_id"]=="us-gaap_GrossProfit"
    assert out["concept_metadata"]["xsd_type"]=="xbrli:monetaryItemType"
    assert out["concept_metadata"]["period_type"]=="duration"
    assert out["concept_metadata"]["balance"]=="credit"
    assert out["documentation_label"]==DOC
    assert out["semantic_truth_authority"] is False
    assert out["policy_adequacy_authority"] is False


def test_contract_compiles_into_existing_semantic_ir(tmp_path:Path):
    out=_run(tmp_path)
    compiled=semantic_ir.compile_semantic_ir(out["semantic_contract"])
    assert compiled["status"]=="COMPILED",compiled
    assert any(
        row["predicate"]=="documentation_label" and row["object"]==DOC
        for row in compiled["facts"]
    )


def test_independent_verifier_rederives_taxonomy_bytes(tmp_path:Path):
    _run(tmp_path)
    out=v.verify(
        root=tmp_path,
        anchor_semantic_path="canonical/tmp/anchor.json",
        xsd_path="canonical/tmp/us-gaap-2025.xsd",
        documentation_path="canonical/tmp/us-gaap-doc-2025.xml",
        metadata_path="canonical/tmp/release_metadata.json",
    )
    assert out["verified"] is True,out
    assert out["producer_independent"] is True
    assert out["taxonomy_bytes_rederived"] is True
    assert out["upstream_inline_anchor_verification_required"] is True


def test_custom_or_unknown_namespace_is_outside_v1(tmp_path:Path):
    _write_anchor(tmp_path,_anchor(namespace="https://www.apple.com/20250927",local_name="GrossMargin"))
    with patch.object(p,"_fetch") as fetch:
        with pytest.raises(p.TaxonomyMetadataError,match="US_GAAP_NAMESPACE_RELEASE_OUTSIDE_V1"):
            p.run(_args(),tmp_path)
        fetch.assert_not_called()


def test_wrong_xsd_namespace_fails_closed(tmp_path:Path):
    _write_anchor(tmp_path)
    bad=_xsd(namespace="http://fasb.org/us-gaap/2024")
    with patch.object(p,"_fetch",side_effect=_fake_fetch(xsd=bad)):
        with pytest.raises(p.TaxonomyMetadataError,match="XSD_TARGET_NAMESPACE_MISMATCH"):
            p.run(_args(),tmp_path)


def test_missing_concept_fails_closed(tmp_path:Path):
    _write_anchor(tmp_path)
    bad=_xsd(local_name="OperatingIncomeLoss")
    with patch.object(p,"_fetch",side_effect=_fake_fetch(xsd=bad)):
        with pytest.raises(p.TaxonomyMetadataError,match="XSD_CONCEPT_NOT_UNIQUE"):
            p.run(_args(),tmp_path)


def test_documentation_must_bind_exact_element_id(tmp_path:Path):
    _write_anchor(tmp_path)
    bad=_doc(local_name="OperatingIncomeLoss")
    with patch.object(p,"_fetch",side_effect=_fake_fetch(doc=bad)):
        with pytest.raises(p.TaxonomyMetadataError,match="DOCUMENTATION_LABEL_NOT_UNIQUE"):
            p.run(_args(),tmp_path)


def test_xlink_labels_are_scoped_to_each_extended_link(tmp_path:Path):
    _write_anchor(tmp_path)
    scoped = f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator"
   xlink:href="us-gaap-2025.xsd#us-gaap_GrossProfit" xlink:label="loc"/>
  <link:label xlink:type="resource"
   xlink:role="http://www.xbrl.org/2003/role/documentation"
   xlink:label="doc">{DOC}</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator"
   xlink:href="us-gaap-2025.xsd#us-gaap_OperatingIncomeLoss" xlink:label="loc"/>
  <link:label xlink:type="resource"
   xlink:role="http://www.xbrl.org/2003/role/documentation"
   xlink:label="doc">Wrong concept documentation.</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
</link:linkbase>""".encode()
    with patch.object(p,"_fetch",side_effect=_fake_fetch(doc=scoped)):
        out=p.run(_args(),tmp_path)
    assert out["documentation_label"]==DOC


def test_redirect_is_rejected(tmp_path:Path):
    _write_anchor(tmp_path)
    with patch.object(p,"_fetch",side_effect=_fake_fetch(redirect_doc=True)):
        with pytest.raises(p.TaxonomyMetadataError,match="DOC_FINAL_URL_MISMATCH"):
            p.run(_args(),tmp_path)


def test_dtd_or_entity_input_is_rejected(tmp_path:Path):
    _write_anchor(tmp_path)
    bad=b'<!DOCTYPE schema [<!ENTITY x "boom">]><schema/>'
    with patch.object(p,"_fetch",side_effect=_fake_fetch(xsd=bad)):
        with pytest.raises(p.TaxonomyMetadataError,match="XSD_DTD_OR_ENTITY_FORBIDDEN"):
            p.run(_args(),tmp_path)


def test_verifier_rejects_metadata_tamper(tmp_path:Path):
    _run(tmp_path)
    path=tmp_path/"canonical/tmp/release_metadata.json"
    doc=json.loads(path.read_text())
    doc["documentation_label"]="invented meaning"
    path.write_text(json.dumps(doc))
    out=v.verify(
        root=tmp_path,
        anchor_semantic_path="canonical/tmp/anchor.json",
        xsd_path="canonical/tmp/us-gaap-2025.xsd",
        documentation_path="canonical/tmp/us-gaap-doc-2025.xml",
        metadata_path="canonical/tmp/release_metadata.json",
    )
    assert out["verified"] is False
    assert "METADATA_FIELD_MISMATCH:documentation_label" in out["errors"]


def test_verifier_rejects_taxonomy_byte_tamper(tmp_path:Path):
    _run(tmp_path)
    path=tmp_path/"canonical/tmp/us-gaap-doc-2025.xml"
    path.write_bytes(_doc(documentation="Different definition"))
    out=v.verify(
        root=tmp_path,
        anchor_semantic_path="canonical/tmp/anchor.json",
        xsd_path="canonical/tmp/us-gaap-2025.xsd",
        documentation_path="canonical/tmp/us-gaap-doc-2025.xml",
        metadata_path="canonical/tmp/release_metadata.json",
    )
    assert out["verified"] is False
    assert "METADATA_FIELD_MISMATCH:documentation_sha256" in out["errors"]
    assert "METADATA_FIELD_MISMATCH:documentation_label" in out["errors"]


def test_authority_flags_cannot_be_self_promoted(tmp_path:Path):
    _run(tmp_path)
    path=tmp_path/"canonical/tmp/release_metadata.json"
    doc=json.loads(path.read_text())
    doc["semantic_truth_authority"]=True
    doc["free_text_policy_semantics_claimed"]=True
    doc["terminal_authority"]=True
    path.write_text(json.dumps(doc))
    out=v.verify(
        root=tmp_path,
        anchor_semantic_path="canonical/tmp/anchor.json",
        xsd_path="canonical/tmp/us-gaap-2025.xsd",
        documentation_path="canonical/tmp/us-gaap-doc-2025.xml",
        metadata_path="canonical/tmp/release_metadata.json",
    )
    assert out["verified"] is False
    assert "AUTHORITY_BOUNDARY_INVALID:semantic_truth_authority" in out["errors"]
    assert "AUTHORITY_BOUNDARY_INVALID:free_text_policy_semantics_claimed" in out["errors"]
    assert "AUTHORITY_BOUNDARY_INVALID:terminal_authority" in out["errors"]

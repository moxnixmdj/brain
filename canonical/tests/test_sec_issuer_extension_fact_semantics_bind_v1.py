from __future__ import annotations
import json
import pytest
from canonical.runtime import sec_issuer_extension_fact_semantics_bind_v1 as b

INSTANCE_SCHEMA="PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"
CONCEPT_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
DIR="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123"
Q="{https://www.apple.com/20240928}LesseeOperatingAndFinanceLeaseLiabilityToBePaid"

def instance():
    return {
        "schema":INSTANCE_SCHEMA,
        "source_url":DIR+"/aapl-20240928_htm.xml",
        "source_path":"tmp/instance.xml",
        "source_sha256":"1"*64,
        "source_native_instance_fact_semantics_proved":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "facts":[{
            "ordinal":7,
            "concept_qname":Q,
            "namespace_uri":"https://www.apple.com/20240928",
            "local_name":"LesseeOperatingAndFinanceLeaseLiabilityToBePaid",
            "context_ref":"c1",
            "context":{"entity":{"scheme":"http://www.sec.gov/CIK","identifier":"0000320193"},"period":{"kind":"instant","instant":"2024-09-28"},"dimensions":[]},
            "unit_ref":"USD",
            "unit":{"kind":"measure","measures":["{http://www.xbrl.org/2003/iso4217}USD"]},
            "lexical_value":"100",
            "normalized_decimal":"100",
            "nil":False,
        }],
    }

def concept():
    return {
        "schema":CONCEPT_SCHEMA,
        "xsd_url":DIR+"/aapl-20240928.xsd",
        "label_url":DIR+"/aapl-20240928_lab.xml",
        "xsd_path":"tmp/aapl.xsd",
        "label_path":"tmp/aapl_lab.xml",
        "xsd_sha256":"2"*64,
        "label_sha256":"3"*64,
        "concept_namespace":"https://www.apple.com/20240928",
        "local_name":"LesseeOperatingAndFinanceLeaseLiabilityToBePaid",
        "concept_qname":Q,
        "concept_metadata":{"element_id":"aapl_LesseeOperatingAndFinanceLeaseLiabilityToBePaid","xsd_type":"xbrli:monetaryItemType","period_type":"instant","balance":"credit"},
        "standard_label":"Operating and finance lease payments due",
        "documentation_label":"Amount of lessee's undiscounted obligation for lease payments for operating and finance leases.",
        "issuer_extension_documentation_semantics_proved":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }

def write(root,i=None,c=None):
    (root/"instance.json").write_text(json.dumps(i or instance()))
    (root/"concept.json").write_text(json.dumps(c or concept()))

def run(root):
    return b.run({"instance_semantic_path":"instance.json","concept_semantic_path":"concept.json","fact_ordinal":7},root)

def test_exact_qname_same_filing_binds(tmp_path):
    write(tmp_path)
    out=run(tmp_path)
    assert out["pass"] is True
    assert out["fact_bound_to_issuer_documented_concept"] is True
    assert out["concept_qname"]==Q
    assert out["documentation_label"]==concept()["documentation_label"]
    assert out["fact"]["normalized_decimal"]=="100"
    assert out["semantic_truth_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_qname_mismatch_fails_closed(tmp_path):
    i=instance(); i["facts"][0]["concept_qname"]="{https://www.apple.com/20240928}Other"
    write(tmp_path,i=i)
    out=run(tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="FACT_CONCEPT_QNAME_MISMATCH"

def test_cross_filing_taxonomy_fails_closed(tmp_path):
    c=concept(); c["xsd_url"]="https://www.sec.gov/Archives/edgar/data/320193/OTHER/aapl.xsd"; c["label_url"]="https://www.sec.gov/Archives/edgar/data/320193/OTHER/aapl_lab.xml"
    write(tmp_path,c=c)
    out=run(tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="SEC_ARCHIVE_DIRECTORY_MISMATCH"

def test_wrong_instance_proof_flag_fails_closed(tmp_path):
    i=instance(); i["source_native_instance_fact_semantics_proved"]=False
    write(tmp_path,i=i)
    out=run(tmp_path)
    assert out["reason"]=="INSTANCE_SOURCE_NATIVE_PROOF_REQUIRED"

def test_wrong_concept_proof_flag_fails_closed(tmp_path):
    c=concept(); c["issuer_extension_documentation_semantics_proved"]=False
    write(tmp_path,c=c)
    out=run(tmp_path)
    assert out["reason"]=="ISSUER_EXTENSION_SEMANTICS_PROOF_REQUIRED"

def test_nonunique_ordinal_fails_closed(tmp_path):
    i=instance(); i["facts"].append(dict(i["facts"][0]))
    write(tmp_path,i=i)
    out=run(tmp_path)
    assert out["reason"]=="FACT_ORDINAL_NOT_UNIQUE"

def test_authority_self_promotion_upstream_fails_closed(tmp_path):
    c=concept(); c["semantic_truth_authority"]=True
    write(tmp_path,c=c)
    out=run(tmp_path)
    assert out["reason"]=="UPSTREAM_AUTHORITY_BOUNDARY_INVALID"

def test_missing_hash_fails_closed(tmp_path):
    c=concept(); c["xsd_sha256"]=""
    write(tmp_path,c=c)
    out=run(tmp_path)
    assert out["reason"]=="UPSTREAM_CONTENT_ADDRESS_REQUIRED"

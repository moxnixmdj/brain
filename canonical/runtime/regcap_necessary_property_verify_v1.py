"""Independent verifier for bounded regulatory-capital necessary-property results.

This verifier deliberately does not call the producer or
regcap_necessary_property_authority_v1.verify_property_request. It binds its own
small rule table to the pinned source pack and replays the source-fragment
authority directly.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.pinned_https_source_fragment_authority_v1 import verify_pack

SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_VERIFY_V1"
CASE_SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_RESULT_V1"
PACK_SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/REGCAP_NECESSARY_PROPERTY_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="7df4f9a37eb2b1efc8350221d7a94b73fb0ed9fe"
SCOPE_ID="REGCAP_BIS_RBC30_2027_AND_FSB_TLAC_2015_V1"
ROOT=Path(__file__).resolve().parents[2]

RULES={
 ("REGCAP::CCOB","FUNCTION::LOSS_ABSORPTION"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCOB_LOSS_DRAWDOWN",)),
 ("REGCAP::CCOB","COMPOSITION::CET1"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCOB_CET1_ABOVE_MINIMUM",)),
 ("REGCAP::CCOB","POSITION::ABOVE_REGULATORY_MINIMUM"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCOB_CET1_ABOVE_MINIMUM",)),
 ("REGCAP::CCYB","DOMAIN::MACRO_FINANCIAL"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCYB_MACRO_FINANCIAL",)),
 ("REGCAP::CCYB","TRIGGER::EXCESS_CREDIT_GROWTH_SYSTEM_WIDE_RISK"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCYB_SYSTEM_RISK_TRIGGER",)),
 ("REGCAP::CCYB","RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCYB_RELEASE",)),
 ("REGCAP::CCYB","COMPOSITION::CET1"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCYB_CET1",)),
 ("REGCAP::CCYB","RELATION::EXTENDS_CCOB"):("BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",("CCYB_EXTENDS_CCOB",)),
 ("REGCAP::TLAC","SCOPE::G_SIB"):("FSB_TLAC_2015_11_09",("TLAC_GSIB_SCOPE",)),
 ("REGCAP::TLAC","FUNCTION::LOSS_ABSORPTION"):("FSB_TLAC_2015_11_09",("TLAC_LOSS_RECAP_RESOLUTION",)),
 ("REGCAP::TLAC","FUNCTION::RECAPITALISATION"):("FSB_TLAC_2015_11_09",("TLAC_LOSS_RECAP_RESOLUTION",)),
 ("REGCAP::TLAC","REGIME::RESOLUTION"):("FSB_TLAC_2015_11_09",("TLAC_LOSS_RECAP_RESOLUTION",)),
}

def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"verified":False,"producer_independent":True,"reason":reason,
            "terminal_authority":False,**extra}

def verify(case:Mapping[str,Any],result:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    try:
        if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
            return _fail("CASE_SCHEMA_INVALID")
        if set(case)!={"schema","scope_id","concept_id","property_id"}:
            return _fail("CASE_FIELD_SET_INVALID")
        if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
            return _fail("RESULT_SCHEMA_INVALID")
        scope=str(case.get("scope_id") or "")
        concept=str(case.get("concept_id") or "")
        prop=str(case.get("property_id") or "")
        if scope!=SCOPE_ID:
            return _fail("SCOPE_ID_MISMATCH")
        rule=RULES.get((concept,prop))
        if rule is None:
            return _fail("PAIR_NOT_IN_VERIFIER_RULE_SET")
        expected_fields={
            "status":"PROVED_ENTAILS","scope_id":scope,"concept_id":concept,
            "property_id":prop,"relation":"ENTAILS","source_authority":True,
            "semantic_truth_authority":True,"reverse_inference_authorized":False,
            "absence_means_false":False,"open_world_ontology_complete":False,
            "terminal_authority":False,
        }
        for key,value in expected_fields.items():
            if result.get(key)!=value:
                return _fail("RESULT_FIELD_MISMATCH:"+key)

        root=Path(repo_root).resolve() if repo_root is not None else ROOT
        path=(root/PACK_PATH).resolve(strict=True); path.relative_to(root)
        raw=path.read_bytes()
        if _git_blob(raw)!=PACK_GIT_BLOB_SHA:
            return _fail("PACK_GIT_BLOB_DRIFT")
        doc=json.loads(raw.decode("utf-8"))
        if doc.get("schema")!=PACK_SCHEMA or doc.get("scope_id")!=SCOPE_ID:
            return _fail("PACK_IDENTITY_INVALID")
        sources={str(x.get("source_id") or ""):x for x in doc.get("sources") or [] if isinstance(x,Mapping)}
        source_id,fragment_ids=rule
        source=sources.get(source_id)
        if not isinstance(source,Mapping):
            return _fail("RULE_SOURCE_MISSING")
        checked=verify_pack(source)
        if checked.get("pass") is not True:
            return _fail("PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED")
        authenticated=set(str(x) for x in (checked.get("receipt") or {}).get("fragment_ids",[]))
        if not set(fragment_ids).issubset(authenticated):
            return _fail("REQUIRED_FRAGMENT_NOT_AUTHENTICATED")
        edge=result.get("edge_receipt")
        if not isinstance(edge,Mapping):
            return _fail("EDGE_RECEIPT_MISSING")
        if (edge.get("pass") is not True or edge.get("scope_id")!=scope
            or edge.get("source_id")!=concept or edge.get("target_id")!=prop
            or edge.get("relation")!="ENTAILS"
            or edge.get("source_semantics_authenticated") is not True
            or edge.get("target_semantics_authenticated") is not True
            or edge.get("relation_semantics_authenticated") is not True
            or edge.get("verification_authority_mutated") is not False):
            return _fail("EDGE_RECEIPT_INVALID")
        core={k:edge[k] for k in (
            "pass","schema","scope_id","source_id","target_id","relation",
            "source_semantics_authenticated","target_semantics_authenticated",
            "relation_semantics_authenticated","verification_authority_mutated","evidence_sha256"
        )}
        expected_receipt=sha256(json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        if edge.get("receipt_sha256")!=expected_receipt:
            return _fail("EDGE_RECEIPT_SHA256_INVALID")
        return {"schema":SCHEMA,"verified":True,"producer_independent":True,
                "scope_id":scope,"concept_id":concept,"property_id":prop,
                "relation":"ENTAILS","source_id":source_id,
                "required_fragment_ids":list(fragment_ids),
                "source_receipt_sha256":(checked.get("receipt") or {}).get("receipt_sha256"),
                "terminal_authority":False}
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

from __future__ import annotations
from copy import deepcopy
import json, pathlib, re, urllib.parse
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_FACT_SEMANTICS_BIND_V1"
INSTANCE_SCHEMA="PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"
CONCEPT_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
_SHA_RE=re.compile(r"^[0-9a-f]{64}$")

def _fail(reason):
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":reason,
        "fact_bound_to_issuer_documented_concept":False,
        "semantic_truth_authority":False,"policy_adequacy_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load(path):
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,Mapping):
        raise ValueError("SEMANTIC_DOCUMENT_NOT_OBJECT")
    return x

def _dir(url):
    p=urllib.parse.urlsplit(str(url or ""))
    if (
        p.scheme!="https" or p.hostname!="www.sec.gov" or p.username or p.password
        or p.port not in (None,443) or p.query or p.fragment
        or not p.path.startswith("/Archives/edgar/data/")
    ):
        return None
    return p.path.rsplit("/",1)[0]

def _content_addressed(doc,keys):
    return all(isinstance(doc.get(k),str) and _SHA_RE.fullmatch(doc[k]) for k in keys)

def _contract(fact,concept,instance,concept_doc):
    fid="XBRL_INSTANCE_FACT:"+str(fact["ordinal"])
    cid="XBRL_CONCEPT:"+str(concept_doc["concept_qname"])
    isrc={"path":instance["source_path"],"artifact":instance["source_sha256"],"uri":instance["source_url"],"observation_id":fid}
    csrc={"path":concept_doc["xsd_path"],"artifact":concept_doc["xsd_sha256"],"uri":concept_doc["xsd_url"]}
    lsrc={"path":concept_doc["label_path"],"artifact":concept_doc["label_sha256"],"uri":concept_doc["label_url"]}
    facts=[
        {"subject":fid,"predicate":"concept_qname","object":concept_doc["concept_qname"],"source":isrc},
        {"subject":cid,"predicate":"documentation_label","object":concept_doc["documentation_label"],"source":lsrc},
    ]
    if concept_doc.get("standard_label") is not None:
        facts.append({"subject":cid,"predicate":"standard_label","object":concept_doc["standard_label"],"source":lsrc})
    for k,v in concept.items():
        facts.append({"subject":cid,"predicate":k,"object":v,"source":csrc})
    return {
        "entities":[
            {"id":fid,"type":"SOURCE_NATIVE_XBRL_INSTANCE_FACT","source":isrc},
            {"id":cid,"type":"ISSUER_EXTENSION_XBRL_CONCEPT","source":csrc},
        ],
        "facts":facts,
        "relations":[
            {"subject":fid,"predicate":"source_fact_uses_issuer_documented_concept","object":cid,"source":isrc}
        ],
        "templates":[],
        "ambiguities":[],
    }

def run(args:Mapping[str,Any],root:Any)->dict[str,Any]:
    try:
        root=pathlib.Path(root).resolve()
        ip=_safe(root,args.get("instance_semantic_path"))
        cp=_safe(root,args.get("concept_semantic_path"))
        instance=_load(ip)
        concept_doc=_load(cp)
        if instance.get("schema")!=INSTANCE_SCHEMA:
            return _fail("INSTANCE_SCHEMA_INVALID")
        if concept_doc.get("schema")!=CONCEPT_SCHEMA:
            return _fail("CONCEPT_SCHEMA_INVALID")
        if instance.get("source_native_instance_fact_semantics_proved") is not True:
            return _fail("INSTANCE_SOURCE_NATIVE_PROOF_REQUIRED")
        if concept_doc.get("issuer_extension_documentation_semantics_proved") is not True:
            return _fail("ISSUER_EXTENSION_SEMANTICS_PROOF_REQUIRED")
        for doc in (instance,concept_doc):
            if doc.get("semantic_truth_authority") is not False or doc.get("terminal_authority") is not False or doc.get("terminal_credit_delta")!=0:
                return _fail("UPSTREAM_AUTHORITY_BOUNDARY_INVALID")
        if not _content_addressed(instance,("source_sha256",)) or not _content_addressed(concept_doc,("xsd_sha256","label_sha256")):
            return _fail("UPSTREAM_CONTENT_ADDRESS_REQUIRED")
        idir=_dir(instance.get("source_url"))
        xdir=_dir(concept_doc.get("xsd_url"))
        ldir=_dir(concept_doc.get("label_url"))
        if not idir or idir!=xdir or idir!=ldir:
            return _fail("SEC_ARCHIVE_DIRECTORY_MISMATCH")
        ordinal=args.get("fact_ordinal")
        if isinstance(ordinal,bool) or not isinstance(ordinal,int) or ordinal<0:
            return _fail("FACT_ORDINAL_INVALID")
        facts=instance.get("facts")
        if not isinstance(facts,list):
            return _fail("INSTANCE_FACTS_REQUIRED")
        rows=[x for x in facts if isinstance(x,Mapping) and x.get("ordinal")==ordinal]
        if len(rows)!=1:
            return _fail("FACT_ORDINAL_NOT_UNIQUE")
        fact=dict(rows[0])
        q=str(concept_doc.get("concept_qname") or "")
        ns=str(concept_doc.get("concept_namespace") or "")
        local=str(concept_doc.get("local_name") or "")
        if q!="{"+ns+"}"+local:
            return _fail("CONCEPT_QNAME_INTERNAL_MISMATCH")
        if str(fact.get("concept_qname") or "")!=q:
            return _fail("FACT_CONCEPT_QNAME_MISMATCH")
        if str(fact.get("namespace_uri") or "")!=ns or str(fact.get("local_name") or "")!=local:
            return _fail("FACT_QNAME_COMPONENT_MISMATCH")
        md=concept_doc.get("concept_metadata")
        if not isinstance(md,Mapping) or not str(concept_doc.get("documentation_label") or "").strip():
            return _fail("ISSUER_CONCEPT_DOCUMENTATION_REQUIRED")
        out={
            "schema":SCHEMA,
            "status":"PASS__FACT_BOUND_TO_ISSUER_DOCUMENTED_EXTENSION_CONCEPT",
            "pass":True,
            "fact_bound_to_issuer_documented_concept":True,
            "fact_ordinal":ordinal,
            "concept_qname":q,
            "fact":deepcopy(fact),
            "concept_metadata":deepcopy(dict(md)),
            "standard_label":concept_doc.get("standard_label"),
            "documentation_label":concept_doc["documentation_label"],
            "instance_source":{"path":instance["source_path"],"sha256":instance["source_sha256"],"url":instance["source_url"]},
            "concept_sources":{
                "xsd":{"path":concept_doc["xsd_path"],"sha256":concept_doc["xsd_sha256"],"url":concept_doc["xsd_url"]},
                "label":{"path":concept_doc["label_path"],"sha256":concept_doc["label_sha256"],"url":concept_doc["label_url"]},
            },
            "semantic_contract":_contract(fact,dict(md),instance,concept_doc),
            "upstream_independent_raw_byte_verification_required":True,
            "cross_filing_semantic_stability_claimed":False,
            "standard_taxonomy_equivalence_claimed":False,
            "open_world_finance_semantics_complete":False,
            "semantic_truth_authority":False,
            "policy_adequacy_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }
        output=args.get("semantic_output_path")
        if output:
            op=_safe(root,output)
            op.parent.mkdir(parents=True,exist_ok=True)
            op.write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        return out
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

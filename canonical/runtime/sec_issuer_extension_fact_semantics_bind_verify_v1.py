from __future__ import annotations
import json, pathlib, re, urllib.parse
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_FACT_SEMANTICS_BIND_VERIFY_V1"
BIND_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_FACT_SEMANTICS_BIND_V1"
INSTANCE_SCHEMA="PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"
CONCEPT_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
_SHA_RE=re.compile(r"^[0-9a-f]{64}$")

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load(p):
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,Mapping):
        raise ValueError("SEMANTIC_DOCUMENT_NOT_OBJECT")
    return x

def _dir(url):
    p=urllib.parse.urlsplit(str(url or ""))
    if p.scheme!="https" or p.hostname!="www.sec.gov" or p.query or p.fragment or not p.path.startswith("/Archives/edgar/data/"):
        return None
    return p.path.rsplit("/",1)[0]

def _hashes(doc,keys):
    return all(isinstance(doc.get(k),str) and _SHA_RE.fullmatch(doc[k]) for k in keys)

def _contract(fact,md,instance,concept):
    fid="XBRL_INSTANCE_FACT:"+str(fact["ordinal"])
    cid="XBRL_CONCEPT:"+str(concept["concept_qname"])
    isrc={"path":instance["source_path"],"artifact":instance["source_sha256"],"uri":instance["source_url"],"observation_id":fid}
    csrc={"path":concept["xsd_path"],"artifact":concept["xsd_sha256"],"uri":concept["xsd_url"]}
    lsrc={"path":concept["label_path"],"artifact":concept["label_sha256"],"uri":concept["label_url"]}
    facts=[
        {"subject":fid,"predicate":"concept_qname","object":concept["concept_qname"],"source":isrc},
        {"subject":cid,"predicate":"documentation_label","object":concept["documentation_label"],"source":lsrc},
    ]
    if concept.get("standard_label") is not None:
        facts.append({"subject":cid,"predicate":"standard_label","object":concept["standard_label"],"source":lsrc})
    for k,v in md.items():
        facts.append({"subject":cid,"predicate":k,"object":v,"source":csrc})
    return {
        "entities":[
            {"id":fid,"type":"SOURCE_NATIVE_XBRL_INSTANCE_FACT","source":isrc},
            {"id":cid,"type":"ISSUER_EXTENSION_XBRL_CONCEPT","source":csrc},
        ],
        "facts":facts,
        "relations":[{"subject":fid,"predicate":"source_fact_uses_issuer_documented_concept","object":cid,"source":isrc}],
        "templates":[],"ambiguities":[],
    }

def verify(*,root:Any,instance_semantic_path:Any,concept_semantic_path:Any,binding_semantic_path:Any)->dict[str,Any]:
    errors=[]
    try:
        root=pathlib.Path(root).resolve()
        instance=_load(_safe(root,instance_semantic_path))
        concept=_load(_safe(root,concept_semantic_path))
        binding=_load(_safe(root,binding_semantic_path))
        if instance.get("schema")!=INSTANCE_SCHEMA: errors.append("INSTANCE_SCHEMA_INVALID")
        if concept.get("schema")!=CONCEPT_SCHEMA: errors.append("CONCEPT_SCHEMA_INVALID")
        if binding.get("schema")!=BIND_SCHEMA: errors.append("BINDING_SCHEMA_INVALID")
        if instance.get("source_native_instance_fact_semantics_proved") is not True: errors.append("INSTANCE_SOURCE_NATIVE_PROOF_REQUIRED")
        if concept.get("issuer_extension_documentation_semantics_proved") is not True: errors.append("ISSUER_EXTENSION_SEMANTICS_PROOF_REQUIRED")
        for name,doc in (("INSTANCE",instance),("CONCEPT",concept)):
            if doc.get("semantic_truth_authority") is not False or doc.get("terminal_authority") is not False or doc.get("terminal_credit_delta")!=0:
                errors.append(name+"_AUTHORITY_BOUNDARY_INVALID")
        if not _hashes(instance,("source_sha256",)): errors.append("INSTANCE_CONTENT_ADDRESS_INVALID")
        if not _hashes(concept,("xsd_sha256","label_sha256")): errors.append("CONCEPT_CONTENT_ADDRESS_INVALID")
        dirs=(_dir(instance.get("source_url")),_dir(concept.get("xsd_url")),_dir(concept.get("label_url")))
        if not dirs[0] or len(set(dirs))!=1: errors.append("SEC_ARCHIVE_DIRECTORY_MISMATCH")
        ordinal=binding.get("fact_ordinal")
        facts=instance.get("facts") if isinstance(instance.get("facts"),list) else []
        rows=[x for x in facts if isinstance(x,Mapping) and x.get("ordinal")==ordinal]
        if len(rows)!=1:
            errors.append("FACT_ORDINAL_NOT_UNIQUE")
            fact=None
        else:
            fact=dict(rows[0])
        q=str(concept.get("concept_qname") or "")
        ns=str(concept.get("concept_namespace") or "")
        local=str(concept.get("local_name") or "")
        if q!="{"+ns+"}"+local: errors.append("CONCEPT_QNAME_INTERNAL_MISMATCH")
        if fact is not None:
            if str(fact.get("concept_qname") or "")!=q: errors.append("FACT_CONCEPT_QNAME_MISMATCH")
            if str(fact.get("namespace_uri") or "")!=ns or str(fact.get("local_name") or "")!=local: errors.append("FACT_QNAME_COMPONENT_MISMATCH")
        md=concept.get("concept_metadata")
        if not isinstance(md,Mapping): errors.append("CONCEPT_METADATA_REQUIRED")
        if not str(concept.get("documentation_label") or "").strip(): errors.append("DOCUMENTATION_REQUIRED")
        if not errors and fact is not None:
            expected={
                "status":"PASS__FACT_BOUND_TO_ISSUER_DOCUMENTED_EXTENSION_CONCEPT",
                "pass":True,
                "fact_bound_to_issuer_documented_concept":True,
                "concept_qname":q,
                "fact":fact,
                "concept_metadata":dict(md),
                "standard_label":concept.get("standard_label"),
                "documentation_label":concept.get("documentation_label"),
                "instance_source":{"path":instance["source_path"],"sha256":instance["source_sha256"],"url":instance["source_url"]},
                "concept_sources":{
                    "xsd":{"path":concept["xsd_path"],"sha256":concept["xsd_sha256"],"url":concept["xsd_url"]},
                    "label":{"path":concept["label_path"],"sha256":concept["label_sha256"],"url":concept["label_url"]},
                },
            }
            for k,v in expected.items():
                if binding.get(k)!=v: errors.append("BINDING_FIELD_MISMATCH:"+k)
            if binding.get("semantic_contract")!=_contract(fact,dict(md),instance,concept):
                errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_REDERIVED")
        for key in ("cross_filing_semantic_stability_claimed","standard_taxonomy_equivalence_claimed","open_world_finance_semantics_complete","semantic_truth_authority","policy_adequacy_authority","acceptance_authority","terminal_authority"):
            if binding.get(key) is not False: errors.append("AUTHORITY_BOUNDARY_INVALID:"+key)
        if binding.get("terminal_credit_delta")!=0: errors.append("TERMINAL_CREDIT_FORBIDDEN")
        return {
            "schema":SCHEMA,"verified":not errors,
            "status":"PASS__ISSUER_EXTENSION_FACT_BINDING_REDERIVED" if not errors else "FAIL_CLOSED",
            "errors":sorted(set(errors)),"producer_independent":True,
            "semantic_truth_authority":False,"terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"verified":False,"status":"FAIL_CLOSED",
            "errors":[type(exc).__name__+":"+str(exc)],"producer_independent":True,
            "semantic_truth_authority":False,"terminal_authority":False,
        }

def run(args,root):
    return verify(
        root=root,
        instance_semantic_path=args.get("instance_semantic_path"),
        concept_semantic_path=args.get("concept_semantic_path"),
        binding_semantic_path=args.get("binding_semantic_path"),
    )

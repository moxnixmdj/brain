#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
XS="http://www.w3.org/2001/XMLSchema"
XBRLI="http://www.xbrl.org/2003/instance"
LINK="http://www.xbrl.org/2003/linkbase"
XLINK="http://www.w3.org/1999/xlink"
DOC_ROLE="http://www.xbrl.org/2003/role/documentation"
STD_ROLE="http://www.xbrl.org/2003/role/label"
MAX_BYTES=4_000_000
_EMAIL_RE=re.compile(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
_NAME_RE=re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

class ExtensionConceptError(RuntimeError):
    pass

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ExtensionConceptError("PATH_OUTSIDE_REPOSITORY")
    return p

def _ua(v):
    if not isinstance(v,str) or not v.strip() or len(v)>240:
        raise ExtensionConceptError("SEC_USER_AGENT_REQUIRED")
    t=" ".join(v.strip().split())
    if not any(_EMAIL_RE.fullmatch(x.strip("<>()[]{};,") or "") for x in t.split()):
        raise ExtensionConceptError("SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED")
    return t

def _url(v,suffix):
    t=str(v or "").strip()
    p=urllib.parse.urlsplit(t)
    if (
        p.scheme!="https" or p.hostname!="www.sec.gov" or p.username or p.password
        or p.port not in (None,443) or p.query or p.fragment
        or not p.path.startswith("/Archives/edgar/data/")
        or not p.path.lower().endswith(suffix)
    ):
        raise ExtensionConceptError("SEC_ARCHIVE_EXTENSION_URL_REQUIRED")
    return urllib.parse.urlunsplit(("https","www.sec.gov",p.path,"",""))

def _issuer_ns(v):
    t=str(v or "").strip()
    blocked=(
        "http://fasb.org/","https://fasb.org/",
        "http://xbrl.sec.gov/","https://xbrl.sec.gov/",
        "http://www.xbrl.org/","https://www.xbrl.org/",
    )
    if not t or t.startswith(blocked):
        raise ExtensionConceptError("ISSUER_EXTENSION_NAMESPACE_REQUIRED")
    return t

def _local(v):
    t=str(v or "").strip()
    if not _NAME_RE.fullmatch(t):
        raise ExtensionConceptError("LOCAL_NAME_INVALID")
    return t

def _fetch(url,ua,timeout,max_bytes):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":ua,
            "Accept":"application/xml,text/xml;q=0.9,*/*;q=0.1",
            "Accept-Encoding":"identity",
        },
    )
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return (
            r.read(max_bytes+1),
            str(r.geturl()),
            str(r.headers.get("Content-Type") or ""),
            int(getattr(r,"status",200)),
        )

def _reject(raw,kind):
    h=raw[:200000].lower()
    if b"<!doctype" in h or b"<!entity" in h:
        raise ExtensionConceptError(kind+"_DTD_OR_ENTITY_FORBIDDEN")

def _parse(raw,kind):
    _reject(raw,kind)
    try:
        return ET.fromstring(raw)
    except Exception as e:
        raise ExtensionConceptError(kind+"_XML_PARSE_FAILED") from e

def _metadata(xsd_raw,namespace,local):
    root=_parse(xsd_raw,"XSD")
    if root.tag!="{"+XS+"}schema":
        raise ExtensionConceptError("XSD_SCHEMA_ROOT_REQUIRED")
    if str(root.attrib.get("targetNamespace") or "").strip()!=namespace:
        raise ExtensionConceptError("XSD_TARGET_NAMESPACE_MISMATCH")
    els=[e for e in root.findall("{"+XS+"}element") if e.attrib.get("name")==local]
    if len(els)!=1:
        raise ExtensionConceptError("XSD_CONCEPT_NOT_UNIQUE")
    e=els[0]
    eid=str(e.attrib.get("id") or "").strip()
    if not eid:
        raise ExtensionConceptError("XSD_ELEMENT_ID_REQUIRED")
    out={"element_id":eid}
    mapping={
        "xsd_type":"type",
        "substitution_group":"substitutionGroup",
        "abstract":"abstract",
        "nillable":"nillable",
        "period_type":"{"+XBRLI+"}periodType",
        "balance":"{"+XBRLI+"}balance",
    }
    for k,a in mapping.items():
        value=e.attrib.get(a)
        if value is not None and str(value).strip():
            out[k]=str(value).strip()
    return out

def _labels(label_raw,element_id):
    root=_parse(label_raw,"LABEL")
    if root.tag!="{"+LINK+"}linkbase":
        raise ExtensionConceptError("LABEL_LINKBASE_ROOT_REQUIRED")
    docs=[]
    stds=[]
    for ll in root.findall(".//{"+LINK+"}labelLink"):
        loc_labels=set()
        for loc in ll.findall("{"+LINK+"}loc"):
            href=str(loc.attrib.get("{"+XLINK+"}href") or "")
            if urllib.parse.urlsplit(href).fragment==element_id:
                label=str(loc.attrib.get("{"+XLINK+"}label") or "").strip()
                if label:
                    loc_labels.add(label)
        if not loc_labels:
            continue
        resources={}
        for lab in ll.findall("{"+LINK+"}label"):
            lid=str(lab.attrib.get("{"+XLINK+"}label") or "").strip()
            role=str(lab.attrib.get("{"+XLINK+"}role") or "").strip()
            text="".join(lab.itertext()).strip()
            resources.setdefault(lid,[]).append((role,text))
        for arc in ll.findall("{"+LINK+"}labelArc"):
            if str(arc.attrib.get("{"+XLINK+"}from") or "").strip() in loc_labels:
                target=str(arc.attrib.get("{"+XLINK+"}to") or "").strip()
                for role,text in resources.get(target,[]):
                    if role==DOC_ROLE and text:
                        docs.append(text)
                    if role==STD_ROLE and text:
                        stds.append(text)
    docs=list(dict.fromkeys(docs))
    stds=list(dict.fromkeys(stds))
    if len(docs)!=1:
        raise ExtensionConceptError("DOCUMENTATION_LABEL_NOT_UNIQUE")
    if len(stds)>1:
        raise ExtensionConceptError("STANDARD_LABEL_NOT_UNIQUE")
    return (stds[0] if stds else None),docs[0]

def _contract(namespace,local,metadata,std,doc,xsd_rel,xsd_sha,xsd_url,lab_rel,lab_sha,lab_url):
    cid="XBRL_CONCEPT:{"+namespace+"}"+local
    xs={"path":xsd_rel,"artifact":xsd_sha,"uri":xsd_url}
    ls={"path":lab_rel,"artifact":lab_sha,"uri":lab_url}
    facts=[
        {"subject":cid,"predicate":"namespace_uri","object":namespace,"source":xs},
        {"subject":cid,"predicate":"local_name","object":local,"source":xs},
        {"subject":cid,"predicate":"element_id","object":metadata["element_id"],"source":xs},
        {"subject":cid,"predicate":"documentation_label","object":doc,"source":ls},
    ]
    if std is not None:
        facts.append({"subject":cid,"predicate":"standard_label","object":std,"source":ls})
    for key in ("xsd_type","substitution_group","period_type","balance","abstract","nillable"):
        if key in metadata:
            facts.append({"subject":cid,"predicate":key,"object":metadata[key],"source":xs})
    return {
        "entities":[{"id":cid,"type":"ISSUER_EXTENSION_XBRL_CONCEPT","source":xs}],
        "facts":facts,
        "relations":[],
        "templates":[],
        "ambiguities":[],
    }

def run(args:Mapping[str,Any],root:Any)->dict[str,Any]:
    root=pathlib.Path(root).resolve()
    cfgp=_safe(root,args.get("config_path"))
    xp=_safe(root,args.get("xsd_output_path"))
    lp=_safe(root,args.get("label_output_path"))
    sp=_safe(root,args.get("semantic_output_path"))
    cfg=json.loads(cfgp.read_text(encoding="utf-8"))
    xu=_url(cfg.get("xsd_url"),".xsd")
    lu=_url(cfg.get("label_url"),"_lab.xml")
    if urllib.parse.urlsplit(xu).path.rsplit("/",1)[0] != urllib.parse.urlsplit(lu).path.rsplit("/",1)[0]:
        raise ExtensionConceptError("SEC_EXTENSION_FILES_MUST_SHARE_ARCHIVE_DIRECTORY")
    ns=_issuer_ns(cfg.get("concept_namespace"))
    local=_local(cfg.get("local_name"))
    ua=_ua(cfg.get("sec_user_agent"))
    timeout=max(2,min(int(args.get("timeout_s",30)),60))
    maxb=max(4096,min(int(args.get("max_bytes",MAX_BYTES)),MAX_BYTES))
    xr,xf,xc,xstatus=_fetch(xu,ua,timeout,maxb)
    lr,lf,lc,lstatus=_fetch(lu,ua,timeout,maxb)
    if xstatus!=200:
        raise ExtensionConceptError("XSD_HTTP_STATUS:"+str(xstatus))
    if lstatus!=200:
        raise ExtensionConceptError("LABEL_HTTP_STATUS:"+str(lstatus))
    if xf!=xu:
        raise ExtensionConceptError("XSD_FINAL_URL_MISMATCH")
    if lf!=lu:
        raise ExtensionConceptError("LABEL_FINAL_URL_MISMATCH")
    if len(xr)>maxb or len(lr)>maxb:
        raise ExtensionConceptError("HTTP_BODY_TOO_LARGE")
    if "xml" not in xc.casefold():
        raise ExtensionConceptError("XSD_CONTENT_TYPE_NOT_XML")
    if "xml" not in lc.casefold():
        raise ExtensionConceptError("LABEL_CONTENT_TYPE_NOT_XML")
    metadata=_metadata(xr,ns,local)
    std,doc=_labels(lr,metadata["element_id"])
    xp.parent.mkdir(parents=True,exist_ok=True)
    lp.parent.mkdir(parents=True,exist_ok=True)
    sp.parent.mkdir(parents=True,exist_ok=True)
    xp.write_bytes(xr)
    lp.write_bytes(lr)
    xsha=hashlib.sha256(xr).hexdigest()
    lsha=hashlib.sha256(lr).hexdigest()
    xrel=str(xp.relative_to(root)).replace("\\","/")
    lrel=str(lp.relative_to(root)).replace("\\","/")
    out={
        "schema":SCHEMA,
        "status":"PASS__ISSUER_EXTENSION_DOCUMENTATION_SEMANTICS_BOUND",
        "xsd_url":xu,
        "label_url":lu,
        "xsd_path":xrel,
        "label_path":lrel,
        "xsd_sha256":xsha,
        "label_sha256":lsha,
        "concept_namespace":ns,
        "local_name":local,
        "concept_qname":"{"+ns+"}"+local,
        "concept_metadata":metadata,
        "standard_label":std,
        "documentation_label":doc,
        "semantic_contract":_contract(ns,local,metadata,std,doc,xrel,xsha,xu,lrel,lsha,lu),
        "issuer_extension_documentation_semantics_proved":True,
        "cross_filing_semantic_stability_claimed":False,
        "standard_taxonomy_equivalence_claimed":False,
        "ontology_classification_claimed":False,
        "raw_prose_wsd_claimed":False,
        "policy_adequacy_authority":False,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    sp.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return out

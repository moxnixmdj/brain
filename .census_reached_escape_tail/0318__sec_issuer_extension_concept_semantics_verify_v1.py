#!/usr/bin/env python3
from __future__ import annotations
from xml.dom import minidom, Node
import hashlib,json,pathlib,urllib.parse
from typing import Any

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_VERIFY_V1"
PRODUCER_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
XS="http://www.w3.org/2001/XMLSchema"
XBRLI="http://www.xbrl.org/2003/instance"
LINK="http://www.xbrl.org/2003/linkbase"
XLINK="http://www.w3.org/1999/xlink"
DOC_ROLE="http://www.xbrl.org/2003/role/documentation"
STD_ROLE="http://www.xbrl.org/2003/role/label"

class VerifyError(RuntimeError):
    pass

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise VerifyError("PATH_OUTSIDE_REPOSITORY")
    return p

def _doc(raw,kind):
    head=raw[:200000].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise VerifyError(kind+"_DTD_OR_ENTITY_FORBIDDEN")
    return minidom.parseString(raw)

def _attr(e,ns,local):
    return e.getAttributeNS(ns,local) if e.hasAttributeNS(ns,local) else None

def _metadata(raw,ns,local):
    d=_doc(raw,"XSD")
    r=d.documentElement
    if r.namespaceURI!=XS or r.localName!="schema":
        raise VerifyError("XSD_SCHEMA_ROOT_REQUIRED")
    if r.getAttribute("targetNamespace").strip()!=ns:
        raise VerifyError("XSD_TARGET_NAMESPACE_MISMATCH")
    els=[
        e for e in r.childNodes
        if e.nodeType==Node.ELEMENT_NODE and e.namespaceURI==XS
        and e.localName=="element" and e.getAttribute("name")==local
    ]
    if len(els)!=1:
        raise VerifyError("XSD_CONCEPT_NOT_UNIQUE")
    e=els[0]
    eid=e.getAttribute("id").strip()
    if not eid:
        raise VerifyError("XSD_ELEMENT_ID_REQUIRED")
    out={"element_id":eid}
    for k,a in {"xsd_type":"type","substitution_group":"substitutionGroup","abstract":"abstract","nillable":"nillable"}.items():
        if e.hasAttribute(a) and e.getAttribute(a).strip():
            out[k]=e.getAttribute(a).strip()
    for k,a in {"period_type":"periodType","balance":"balance"}.items():
        value=_attr(e,XBRLI,a)
        if value is not None and value.strip():
            out[k]=value.strip()
    return out

def _text(e):
    return "".join(
        c.data for c in e.childNodes
        if c.nodeType in (Node.TEXT_NODE,Node.CDATA_SECTION_NODE)
    ).strip()

def _labels(raw,eid):
    d=_doc(raw,"LABEL")
    docs=[]
    stds=[]
    for ll in d.getElementsByTagNameNS(LINK,"labelLink"):
        locs=set()
        for loc in ll.getElementsByTagNameNS(LINK,"loc"):
            if urllib.parse.urlsplit(_attr(loc,XLINK,"href") or "").fragment==eid:
                label=(_attr(loc,XLINK,"label") or "").strip()
                if label:
                    locs.add(label)
        resources={}
        for lab in ll.getElementsByTagNameNS(LINK,"label"):
            lid=(_attr(lab,XLINK,"label") or "").strip()
            resources.setdefault(lid,[]).append(
                (((_attr(lab,XLINK,"role") or "").strip()),_text(lab))
            )
        for arc in ll.getElementsByTagNameNS(LINK,"labelArc"):
            if ((_attr(arc,XLINK,"from") or "").strip()) in locs:
                target=(_attr(arc,XLINK,"to") or "").strip()
                for role,text in resources.get(target,[]):
                    if role==DOC_ROLE and text:
                        docs.append(text)
                    if role==STD_ROLE and text:
                        stds.append(text)
    docs=list(dict.fromkeys(docs))
    stds=list(dict.fromkeys(stds))
    if len(docs)!=1:
        raise VerifyError("DOCUMENTATION_LABEL_NOT_UNIQUE")
    if len(stds)>1:
        raise VerifyError("STANDARD_LABEL_NOT_UNIQUE")
    return (stds[0] if stds else None),docs[0]

def _contract(ns,local,md,std,doc,xrel,xsha,xurl,lrel,lsha,lurl):
    cid="XBRL_CONCEPT:{"+ns+"}"+local
    xs={"path":xrel,"artifact":xsha,"uri":xurl}
    ls={"path":lrel,"artifact":lsha,"uri":lurl}
    facts=[
        {"subject":cid,"predicate":"namespace_uri","object":ns,"source":xs},
        {"subject":cid,"predicate":"local_name","object":local,"source":xs},
        {"subject":cid,"predicate":"element_id","object":md["element_id"],"source":xs},
        {"subject":cid,"predicate":"documentation_label","object":doc,"source":ls},
    ]
    if std is not None:
        facts.append({"subject":cid,"predicate":"standard_label","object":std,"source":ls})
    for key in ("xsd_type","substitution_group","period_type","balance","abstract","nillable"):
        if key in md:
            facts.append({"subject":cid,"predicate":key,"object":md[key],"source":xs})
    return {
        "entities":[{"id":cid,"type":"ISSUER_EXTENSION_XBRL_CONCEPT","source":xs}],
        "facts":facts,
        "relations":[],
        "templates":[],
        "ambiguities":[],
    }

def verify(*,root:Any,xsd_path:Any,label_path:Any,semantic_path:Any)->dict[str,Any]:
    errors=[]
    try:
        root=pathlib.Path(root).resolve()
        xp=_safe(root,xsd_path)
        lp=_safe(root,label_path)
        sp=_safe(root,semantic_path)
        sem=json.loads(sp.read_text(encoding="utf-8"))
        xr=xp.read_bytes()
        lr=lp.read_bytes()
        if sem.get("schema")!=PRODUCER_SCHEMA:
            errors.append("PRODUCER_SCHEMA_INVALID")
        ns=str(sem.get("concept_namespace") or "")
        local=str(sem.get("local_name") or "")
        md=_metadata(xr,ns,local)
        std,doc=_labels(lr,md["element_id"])
        xsha=hashlib.sha256(xr).hexdigest()
        lsha=hashlib.sha256(lr).hexdigest()
        xrel=str(xp.relative_to(root)).replace("\\","/")
        lrel=str(lp.relative_to(root)).replace("\\","/")
        expected={
            "xsd_path":xrel,
            "label_path":lrel,
            "xsd_sha256":xsha,
            "label_sha256":lsha,
            "concept_qname":"{"+ns+"}"+local,
            "concept_metadata":md,
            "standard_label":std,
            "documentation_label":doc,
        }
        for key,value in expected.items():
            if sem.get(key)!=value:
                errors.append("SEMANTIC_FIELD_MISMATCH:"+key)
        if sem.get("semantic_contract") != _contract(
            ns,local,md,std,doc,xrel,xsha,str(sem.get("xsd_url") or ""),
            lrel,lsha,str(sem.get("label_url") or "")
        ):
            errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_REDERIVED")
        if sem.get("issuer_extension_documentation_semantics_proved") is not True:
            errors.append("PROOF_FLAG_MISSING")
        for key in (
            "cross_filing_semantic_stability_claimed",
            "standard_taxonomy_equivalence_claimed",
            "ontology_classification_claimed",
            "raw_prose_wsd_claimed",
            "policy_adequacy_authority",
            "semantic_truth_authority",
            "terminal_authority",
        ):
            if sem.get(key) is not False:
                errors.append("AUTHORITY_BOUNDARY_INVALID:"+key)
        if sem.get("terminal_credit_delta")!=0:
            errors.append("TERMINAL_CREDIT_FORBIDDEN")
        return {
            "schema":SCHEMA,
            "verified":not errors,
            "status":"PASS__ISSUER_EXTENSION_SEMANTICS_REDERIVED_FROM_RAW_BYTES" if not errors else "FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "producer_independent":True,
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "verified":False,
            "status":"FAIL_CLOSED",
            "errors":[type(exc).__name__+":"+str(exc)],
            "producer_independent":True,
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }

def run(args,root):
    return verify(
        root=root,
        xsd_path=args.get("xsd_path"),
        label_path=args.get("label_path"),
        semantic_path=args.get("semantic_path"),
    )

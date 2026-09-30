#!/usr/bin/env python3
"""Fail-closed PubMed/MeSH primary-source + objective-topic relevance verifier.

Scope:
- Requires an already bibliographically provenance-verified DOI candidate.
- Resolves the DOI to exactly one PubMed record through NCBI E-utilities.
- Treats only NLM publication types that explicitly denote direct empirical
  studies as primary-source evidence, while rejecting evidence-synthesis types.
- Verifies only deterministic objective-topic anchor coverage against PubMed
  title/abstract/MeSH/keyword metadata.

Nonclaims:
- Does not prove that a source supports or contradicts an objective claim.
- Does not prove factual correctness, causal relation, effect direction,
  evidence sufficiency, or general semantic relevance.
- Does not classify non-PubMed domains.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SCHEMA="PROJECT_BRAIN_SOURCE_PRIMARY_RELEVANCE_PUBMED_V1"
UA="ProjectBrain-PubMedPrimaryRelevance/1.0"
ESEARCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

DIRECT_EMPIRICAL_TYPES={
    "Clinical Study",
    "Clinical Trial",
    "Clinical Trial, Phase I",
    "Clinical Trial, Phase II",
    "Clinical Trial, Phase III",
    "Clinical Trial, Phase IV",
    "Controlled Clinical Trial",
    "Randomized Controlled Trial",
    "Adaptive Clinical Trial",
    "Pragmatic Clinical Trial",
    "Observational Study",
    "Comparative Study",
    "Evaluation Study",
    "Validation Study",
    "Multicenter Study",
    "Twin Study",
}
SYNTHESIS_OR_SECONDARY_TYPES={
    "Review",
    "Systematic Review",
    "Meta-Analysis",
    "Scoping Review",
    "Network Meta-Analysis",
    "Scientific Integrity Review",
    "Guideline",
    "Practice Guideline",
    "Consensus Statement",
    "Editorial",
    "Comment",
    "Letter",
}
STOPWORDS={
    "the","a","an","to","from","of","and","or","with","using","use","for",
    "which","is","are","be","this","that","into","on","in","by","as","at",
    "its","it","those","these","each","every","all","any","one","two","three",
    "whether","if","than","versus","vs","among","between","during","over",
    "assess","determine","evaluate","identify","find","show","test","analyze",
    "analyse","evidence","source","sources","primary","relevance","relevant",
    "published","publication","article","paper","research","study","studies",
    "experimental","using","based","report","reports",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _doi(value):
    x=_canon(value)
    low=x.lower()
    for prefix in ("https://doi.org/","http://doi.org/","doi:"):
        if low.startswith(prefix):
            x=x[len(prefix):]
            break
    return x.strip()

def _fetch(url,params,timeout,accept):
    endpoint=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(endpoint,headers={"User-Agent":UA,"Accept":accept})
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(4_000_000)
        final=r.geturl()
        host=(urllib.parse.urlsplit(final).hostname or "").lower()
        if host!="eutils.ncbi.nlm.nih.gov":
            raise RuntimeError("NCBI_REDIRECT_OUTSIDE_EUTILS")
        return raw,final,int(getattr(r,"status",200))

def _search_pmids(doi,timeout):
    raw,final,status=_fetch(
        ESEARCH,
        {"db":"pubmed","retmode":"json","retmax":"5","term":f'"{doi}"[AID]'},
        timeout,
        "application/json",
    )
    data=json.loads(raw.decode("utf-8","replace"))
    ids=[str(x) for x in ((data.get("esearchresult") or {}).get("idlist") or []) if str(x).isdigit()]
    return ids,final,status

def _text(node):
    if node is None:
        return ""
    return _canon(" ".join(node.itertext()))

def _parse_article(raw):
    root=ET.fromstring(raw)
    article=root.find(".//PubmedArticle")
    if article is None:
        raise ValueError("PUBMED_ARTICLE_MISSING")
    ids={}
    for node in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        kind=str(node.attrib.get("IdType") or "").lower()
        value=_canon(node.text)
        if kind and value:
            ids[kind]=value
    title=_text(article.find(".//Article/ArticleTitle"))
    abstract=" ".join(
        x for x in (_text(n) for n in article.findall(".//Article/Abstract/AbstractText")) if x
    )
    publication_types=sorted({
        _canon(n.text) for n in article.findall(".//Article/PublicationTypeList/PublicationType")
        if _canon(n.text)
    })
    mesh=sorted({
        _text(n) for n in article.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
        if _text(n)
    })
    keywords=sorted({
        _text(n) for n in article.findall(".//KeywordList/Keyword") if _text(n)
    })
    pmid=_canon(article.findtext(".//MedlineCitation/PMID"))
    return {
        "pmid":pmid,
        "doi":_doi(ids.get("doi")),
        "title":title,
        "abstract":abstract,
        "publication_types":publication_types,
        "mesh_terms":mesh,
        "keywords":keywords,
    }

def _fetch_record(pmid,timeout):
    raw,final,status=_fetch(
        EFETCH,
        {"db":"pubmed","id":pmid,"retmode":"xml"},
        timeout,
        "application/xml,text/xml",
    )
    record=_parse_article(raw)
    if record.get("pmid")!=str(pmid):
        raise ValueError("PUBMED_PMID_IDENTITY_MISMATCH")
    return record,final,status

def _tokens(value):
    return [
        t.lower() for t in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(t)>=3 and t.lower() not in STOPWORDS and not t.isdigit()
    ]

def _anchor_tokens(objective):
    out=[]
    for token in _tokens(objective):
        if token not in out:
            out.append(token)
    return out

def _prefix_match(a,b):
    if a==b:
        return True
    return len(a)>=5 and len(b)>=5 and (a.startswith(b) or b.startswith(a))

def _match_anchors(anchors,record):
    fields={
        "title":_tokens(record.get("title")),
        "abstract":_tokens(record.get("abstract")),
        "mesh":_tokens(record.get("mesh_terms") or []),
        "keywords":_tokens(record.get("keywords") or []),
    }
    matched=[]
    field_matches={}
    for name,tokens in fields.items():
        hits=[]
        for anchor in anchors:
            if any(_prefix_match(anchor,t) for t in tokens):
                hits.append(anchor)
                if anchor not in matched:
                    matched.append(anchor)
        if hits:
            field_matches[name]=sorted(set(hits))
    coverage=(len(matched)/len(anchors)) if anchors else 0.0
    verified=bool(
        len(anchors)>=2 and
        len(matched)>=2 and
        coverage>=0.50 and
        ("title" in field_matches or "mesh" in field_matches)
    )
    return {
        "objective_anchor_tokens":anchors,
        "matched_anchor_tokens":sorted(matched),
        "anchor_coverage":coverage,
        "field_matches":field_matches,
        "verified":verified,
    }

def verify(objective,candidate,provenance,timeout=20):
    objective=_canon(objective)
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    base={
        "schema":SCHEMA,
        "objective":objective,
        "primary_source_status":"UNVERIFIED",
        "relevance_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "claim_relation_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "primary_source_claim_scope":"NLM_DIRECT_EMPIRICAL_STUDY_PUBLICATION_TYPE_ONLY",
        "relevance_claim_scope":"PUBMED_TITLE_ABSTRACT_MESH_KEYWORD_OBJECTIVE_TOPIC_ANCHOR_COVERAGE_ONLY",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"status":"UNVERIFIED","reason":"OBJECTIVE_REQUIRED"}
    if provenance.get("status")!="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
        return {**base,"status":"UNVERIFIED","reason":"BIBLIOGRAPHIC_PROVENANCE_REQUIRED"}

    candidate_doi=_doi(candidate.get("doi"))
    provenance_doi=_doi(provenance.get("doi"))
    doi=provenance_doi or candidate_doi
    if not doi or (candidate_doi and provenance_doi and candidate_doi.lower()!=provenance_doi.lower()):
        return {**base,"status":"UNVERIFIED","reason":"PROVENANCE_DOI_IDENTITY_REQUIRED"}

    try:
        pmids,search_url,search_status=_search_pmids(doi,timeout)
        matches=[]
        traces=[]
        for pmid in pmids:
            record,fetch_url,fetch_status=_fetch_record(pmid,timeout)
            traces.append({"pmid":pmid,"fetch_url":fetch_url,"http_status":fetch_status,"observed_doi":record.get("doi")})
            if _doi(record.get("doi")).lower()==doi.lower():
                matches.append((record,fetch_url,fetch_status))
    except Exception as exc:
        return {
            **base,"status":"UNVERIFIED","reason":"PUBMED_LOOKUP_FAILED",
            "doi":doi,"error_class":type(exc).__name__,"error":str(exc)[:500],
        }

    if len(matches)!=1:
        return {
            **base,"status":"UNVERIFIED",
            "reason":"UNIQUE_PUBMED_DOI_RECORD_REQUIRED",
            "doi":doi,"matching_record_count":len(matches),
            "search_url":search_url,"search_http_status":search_status,
            "lookup_traces":traces,
        }

    record,fetch_url,fetch_status=matches[0]
    types=set(record.get("publication_types") or [])
    direct=sorted(types & DIRECT_EMPIRICAL_TYPES)
    secondary=sorted(types & SYNTHESIS_OR_SECONDARY_TYPES)
    primary_verified=bool(direct and not secondary)

    relevance=_match_anchors(_anchor_tokens(objective),record)
    relevance_verified=bool(relevance.get("verified"))

    if primary_verified and relevance_verified:
        status="PRIMARY_SOURCE_AND_OBJECTIVE_TOPIC_RELEVANCE_VERIFIED"
    elif not primary_verified and relevance_verified:
        status="OBJECTIVE_TOPIC_RELEVANCE_VERIFIED__PRIMARY_SOURCE_UNVERIFIED"
    elif primary_verified and not relevance_verified:
        status="PRIMARY_SOURCE_VERIFIED__OBJECTIVE_TOPIC_RELEVANCE_UNVERIFIED"
    else:
        status="UNVERIFIED"

    return {
        **base,
        "status":status,
        "doi":doi,
        "pmid":record.get("pmid"),
        "record_title":record.get("title"),
        "publication_types":record.get("publication_types"),
        "direct_empirical_publication_types":direct,
        "secondary_or_synthesis_publication_types":secondary,
        "primary_source_status":(
            "DIRECT_EMPIRICAL_STUDY_PUBLICATION_TYPE_VERIFIED"
            if primary_verified else "UNVERIFIED"
        ),
        "relevance_status":(
            "OBJECTIVE_TOPIC_ANCHOR_COVERAGE_VERIFIED"
            if relevance_verified else "UNVERIFIED"
        ),
        "objective_relevance_evidence":relevance,
        "mesh_term_count":len(record.get("mesh_terms") or []),
        "keyword_count":len(record.get("keywords") or []),
        "search_url":search_url,
        "search_http_status":search_status,
        "fetch_url":fetch_url,
        "fetch_http_status":fetch_status,
        "output_verified":bool(primary_verified and relevance_verified),
    }

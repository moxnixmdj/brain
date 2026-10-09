"""Producer-independent verifier for bounded contextual finance references.

This module does not import contextual_reference_operators.  It independently
reparses the same four deliberately narrow structural forms and compares the
complete normalized proposal.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_VERIFY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_RESULT_V1"
_MODAL=r"(?:shall|must)"
_SENTENCE=re.compile(r"[^.!?]+[.!?]?",re.S)


def _sha(text:str)->str:
    return sha256(text.encode("utf-8")).hexdigest()


def _sentences(source:str):
    rows=[]
    for m in _SENTENCE.finditer(source):
        raw=m.group(0)
        if not raw.strip(): continue
        left=len(raw)-len(raw.lstrip()); right=len(raw.rstrip())
        rows.append((m.start()+left,m.start()+right,raw[left:right]))
    return rows


def _abs(start:int,m:re.Match[str],group:str)->list[int]:
    return [start+m.start(group),start+m.end(group)]


def _expected(source:str)->tuple[dict[str,list[dict[str,Any]]],list[str]]:
    proposal={"bindings":[],"relations":[],"obligations":[]}
    unresolved=[]
    sents=_sentences(source)

    for i in range(1,len(sents)):
        pstart,_,prev=sents[i-1]; cstart,_,cur=sents[i]
        pm=re.match(r"(?P<subject>(?:The|A|An)\s+.+?)\s+(?:shall|must)\b",prev,re.I)
        cm=re.match(r"(?P<pron>It|They)\s+(?:shall|must)\b",cur,re.I)
        if pm and cm:
            subject=pm.group("subject"); pron=cm.group("pron").casefold()
            plural=bool(re.search(r"\band\b",subject,re.I))
            if (pron=="they" and plural) or (pron=="it" and not plural):
                proposal["bindings"].append({
                    "mention_span":_abs(cstart,cm,"pron"),
                    "target_span":_abs(pstart,pm,"subject"),
                    "kind":"subject_pronoun_continuation",
                })
            else:
                unresolved.append("PRONOUN_NUMBER_MISMATCH_OR_UNSUPPORTED")

    mode_targets=list(re.finditer(
        r"\bIf\s+(?P<target>(?:the\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,3}\s+mode)\s+is\s+enabled",
        source,re.I))
    for mention in re.finditer(r"(?P<mention>that\s+mode)\b",source,re.I):
        prior=[m for m in mode_targets if m.end("target")<=mention.start("mention")]
        if len(prior)==1:
            target=prior[0]
            proposal["bindings"].append({
                "mention_span":[mention.start("mention"),mention.end("mention")],
                "target_span":[target.start("target"),target.end("target")],
                "kind":"explicit_mode_anaphora",
            })
        elif len(prior)>1:
            unresolved.append("MULTIPLE_MODE_ANTECEDENTS")

    for i in range(1,len(sents)):
        pstart,_,prev=sents[i-1]; cstart,_,cur=sents[i]
        pm=re.match(r"(?P<subject>.+?)\s+(?P<modal>must|shall)\s+(?P<predicate>[^.!?]+?)[.!?]?$",prev,re.I)
        cm=re.match(r"(?P<subject>.+?)\s+(?P<modal>must|shall)\s*,?\s*too\s*[.!?]?$",cur,re.I)
        if pm and cm and pm.group("modal").casefold()==cm.group("modal").casefold():
            proposal["obligations"].append({
                "subject_span":_abs(cstart,cm,"subject"),
                "predicate_span":_abs(pstart,pm,"predicate"),
                "modality":cm.group("modal").casefold(),
            })

    resp=re.compile(
        r"(?P<s1>(?:The\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})"
        r"\s+and\s+"
        r"(?P<s2>(?:the\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})"
        r"\s+(?P<modal>shall|must)\s+"
        r"(?P<verb>[A-Za-z][A-Za-z0-9_-]*)\s+"
        r"(?P<o1>[A-Za-z0-9_.:/-]+)\s+and\s+(?P<o2>[A-Za-z0-9_.:/-]+)"
        r"\s*,\s*respectively\b",re.I)
    for m in resp.finditer(source):
        mod=m.group("modal").casefold(); verb=[m.start("verb"),m.end("verb")]
        proposal["obligations"].extend([
            {"subject_span":[m.start("s1"),m.end("s1")],"predicate_span":verb,"object_span":[m.start("o1"),m.end("o1")],"modality":mod},
            {"subject_span":[m.start("s2"),m.end("s2")],"predicate_span":verb,"object_span":[m.start("o2"),m.end("o2")],"modality":mod},
        ])
        proposal["relations"].extend([
            {"left_span":[m.start("s1"),m.end("s1")],"right_span":[m.start("o1"),m.end("o1")],"kind":"respectively_pair_1"},
            {"left_span":[m.start("s2"),m.end("s2")],"right_span":[m.start("o2"),m.end("o2")],"kind":"respectively_pair_2"},
        ])

    for _ in re.finditer(r"\b(?:former|latter)\b",source,re.I):
        unresolved.append("FORMER_LATTER_REQUIRES_UNIQUE_PAIR_GRAPH")
    for _ in re.finditer(r"\b(?:This|That)\s+(?:validation|operation|action|process|step|event)\b",source):
        unresolved.append("DEMONSTRATIVE_EVENT_REFERENCE_REQUIRES_EVENT_SEMANTICS")
    return proposal,unresolved


def verify(case:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if not isinstance(case,Mapping) or case.get("schema")!=INPUT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["CASE_SCHEMA_INVALID"],"producer_independent":True,"terminal_authority":False}
    if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["RESULT_SCHEMA_INVALID"],"producer_independent":True,"terminal_authority":False}
    if case.get("domain")!="FINANCE": errors.append("FINANCE_DOMAIN_MARKER_REQUIRED")
    source_id=case.get("source_id"); source=case.get("source_text")
    if not isinstance(source_id,str) or not source_id.strip(): errors.append("SOURCE_ID_INVALID"); source_id=""
    if not isinstance(source,str) or not source.strip(): errors.append("SOURCE_TEXT_INVALID"); source=""
    proposal,unresolved=_expected(source)
    if unresolved: errors.append("UNRESOLVED_CONTEXTUAL_REFERENCE_PRESENT")
    count=sum(len(proposal[k]) for k in proposal)
    if count<=0: errors.append("NO_RESOLVED_REFERENCE_STRUCTURE")
    expected={
        "domain":"FINANCE",
        "source_id":source_id.strip(),
        "source_text_sha256":_sha(source),
        "proposal":proposal,
        "resolved_item_count":count,
        "model_dependency_count":0,
        "general_coreference_claimed":False,
        "synonymy_claimed":False,
        "ontology_mapping_claimed":False,
        "external_world_truth_claimed":False,
    }
    for k,v in expected.items():
        if result.get(k)!=v: errors.append("MISMATCH:"+k)
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_BOUNDED_CONTEXTUAL_REFERENCE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "model_dependency_count":0,
        "terminal_authority":False,
        "boundary":"FOUR_STRUCTURAL_REFERENCE_FORMS_ONLY__NO_GENERAL_COREFERENCE_SYNONYMY_ONTOLOGY_WORD_SENSE_OR_EXTERNAL_TRUTH",
    }

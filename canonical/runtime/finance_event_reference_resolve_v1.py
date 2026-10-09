"""Bounded demonstrative event-reference resolver.

Owned forms are exact two-sentence modal event statements:
  The X shall validate Y. This validation must ...
  The X shall operate Y. This operation must ...
  The X shall process Y. This process must ...

The event noun must exactly match the finite lexical bridge. No general event
semantics, word sense, synonymy, ontology, or world knowledge is inferred.
"""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_RESOLVE_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_RESULT_V1"
_ENTITY=r"[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2}"
_FIRST=re.compile(
 rf"^The\s+(?P<subject>{_ENTITY})\s+(?P<modal>shall|must)\s+(?P<verb>validate|operate|process)\s+(?P<object>[^.!?]+)\.$",
 re.I,
)
_SECOND=re.compile(
 r"^(?P<dem>This|That)\s+(?P<noun>validation|operation|process)\s+(?P<modal>shall|must)\s+(?P<tail>[^.!?]+)\.$",
 re.I,
)
_SPLIT=re.compile(r"(?<=[.!?])\s+|\n+")
_NOUN={"validate":"validation","operate":"operation","process":"process"}

def _sha(text:str)->str:
 return sha256(text.encode("utf-8")).hexdigest()

def compute(case:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(case,Mapping) or case.get("schema")!=INPUT_SCHEMA:
  raise ValueError("CASE_SCHEMA_INVALID")
 if case.get("domain")!="FINANCE": raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
 source_id=case.get("source_id"); source=case.get("source_text")
 if not isinstance(source_id,str) or not source_id.strip(): raise ValueError("SOURCE_ID_REQUIRED")
 if not isinstance(source,str) or not source.strip(): raise ValueError("SOURCE_TEXT_REQUIRED")
 sentences=[x.strip() for x in _SPLIT.split(source) if x.strip()]
 if len(sentences)!=2: raise ValueError("EXACTLY_TWO_SENTENCES_REQUIRED")
 first,second=sentences
 fm=_FIRST.fullmatch(first); sm=_SECOND.fullmatch(second)
 if fm is None: raise ValueError("BOUNDED_EVENT_ANTECEDENT_REQUIRED")
 if sm is None: raise ValueError("BOUNDED_DEMONSTRATIVE_EVENT_REFERENCE_REQUIRED")
 verb=fm.group("verb").casefold(); noun=sm.group("noun").casefold()
 if _NOUN[verb]!=noun: raise ValueError("EVENT_TYPE_LEXICAL_BRIDGE_MISMATCH")
 fs=source.find(first); ss=source.find(second)
 if fs<0 or ss<0 or source.find(first,fs+1)>=0 or source.find(second,ss+1)>=0:
  raise ValueError("SENTENCE_LOCATION_NOT_UNIQUE")
 event_span=[fs+fm.start("verb"),fs+fm.end("object")]
 mention_span=[ss+sm.start("dem"),ss+sm.end("noun")]
 event_text=source[event_span[0]:event_span[1]]
 mention_text=source[mention_span[0]:mention_span[1]]
 return {
  "schema":RESULT_SCHEMA,"status":"PASS__BOUNDED_DEMONSTRATIVE_EVENT_REFERENCE_RESOLVED","pass":True,
  "domain":"FINANCE","source_id":source_id.strip(),"source_text_sha256":_sha(source),
  "event_type":noun,"event_verb":verb,"event_span":event_span,"event_text":event_text,
  "mention_span":mention_span,"mention_text":mention_text,
  "binding":{"mention_span":mention_span,"target_span":event_span,"event_type":noun},
  "reference_authority":"FINITE_LEXICAL_EVENT_BRIDGE_AND_ADJACENT_TWO_SENTENCE_STRUCTURE",
  "model_dependency_count":0,"general_event_semantics_claimed":False,
  "general_coreference_claimed":False,"synonymy_claimed":False,
  "ontology_mapping_claimed":False,"external_world_truth_claimed":False,
  "terminal_authority":False,
 }

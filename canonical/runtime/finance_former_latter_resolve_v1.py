"""Bounded former/latter resolver over an explicitly declared ordered pair.

Owned source shape:
  The X and the Y form the ordered pair. <sentence containing former/latter>

The first sentence is the authority for pair order. This module does not infer
salience, implicit pairing, ontology, synonymy, or general coreference.
"""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_RESOLVE_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_RESULT_V1"

_ENTITY=r"[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2}"
_PAIR=re.compile(
 rf"^The\s+(?P<first>{_ENTITY})\s+and\s+the\s+(?P<second>{_ENTITY})\s+form\s+the\s+ordered\s+pair\.$",
 re.I,
)
_SENT_SPLIT=re.compile(r"(?<=[.!?])\s+|\n+")
_REF=re.compile(r"\b(?P<ref>former|latter)\b",re.I)

def _sha(text:str)->str:
 return sha256(text.encode("utf-8")).hexdigest()

def compute(case:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(case,Mapping) or case.get("schema")!=INPUT_SCHEMA:
  raise ValueError("CASE_SCHEMA_INVALID")
 if case.get("domain")!="FINANCE":
  raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
 source_id=case.get("source_id"); source=case.get("source_text")
 if not isinstance(source_id,str) or not source_id.strip(): raise ValueError("SOURCE_ID_REQUIRED")
 if not isinstance(source,str) or not source.strip(): raise ValueError("SOURCE_TEXT_REQUIRED")
 sentences=[x.strip() for x in _SENT_SPLIT.split(source) if x.strip()]
 if len(sentences)!=2: raise ValueError("EXACTLY_TWO_SENTENCES_REQUIRED")
 first_sentence,reference_sentence=sentences
 m=_PAIR.fullmatch(first_sentence)
 if m is None: raise ValueError("EXPLICIT_ORDERED_PAIR_DECLARATION_REQUIRED")
 first=m.group("first").strip(); second=m.group("second").strip()
 if first.casefold()==second.casefold(): raise ValueError("PAIR_ENTITIES_MUST_DIFFER")
 pair_start=source.find(first_sentence)
 ref_start=source.find(reference_sentence)
 if pair_start<0 or ref_start<0 or source.find(first_sentence,pair_start+1)>=0 or source.find(reference_sentence,ref_start+1)>=0:
  raise ValueError("SENTENCE_LOCATION_NOT_UNIQUE")
 first_local=m.span("first"); second_local=m.span("second")
 first_span=[pair_start+first_local[0],pair_start+first_local[1]]
 second_span=[pair_start+second_local[0],pair_start+second_local[1]]
 refs=list(_REF.finditer(reference_sentence))
 if not refs: raise ValueError("FORMER_OR_LATTER_REFERENCE_REQUIRED")
 bindings=[]
 for rm in refs:
  token=rm.group("ref").casefold()
  target_span=first_span if token=="former" else second_span
  bindings.append({
   "mention":token.upper(),
   "mention_span":[ref_start+rm.start("ref"),ref_start+rm.end("ref")],
   "target":"FIRST" if token=="former" else "SECOND",
   "target_span":target_span,
   "target_text":first if token=="former" else second,
  })
 return {
  "schema":RESULT_SCHEMA,"status":"PASS__EXPLICIT_ORDERED_PAIR_FORMER_LATTER_RESOLVED","pass":True,
  "domain":"FINANCE","source_id":source_id.strip(),"source_text_sha256":_sha(source),
  "pair":{"first_text":first,"first_span":first_span,"second_text":second,"second_span":second_span},
  "bindings":bindings,"binding_count":len(bindings),
  "reference_authority":"EXPLICIT_ORDERED_PAIR_SOURCE_SENTENCE_ONLY",
  "model_dependency_count":0,"general_coreference_claimed":False,
  "implicit_pair_inference_claimed":False,"synonymy_claimed":False,
  "ontology_mapping_claimed":False,"external_world_truth_claimed":False,
  "terminal_authority":False,
 }

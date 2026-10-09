"""Independent verifier for bounded demonstrative event references."""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_VERIFY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_EVENT_REFERENCE_RESULT_V1"
_ENTITY=r"[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2}"
_A=re.compile(rf"^The\s+(?P<s>{_ENTITY})\s+(?:shall|must)\s+(?P<v>validate|operate|process)\s+(?P<o>[^.!?]+)\.$",re.I)
_B=re.compile(r"^(?P<d>This|That)\s+(?P<n>validation|operation|process)\s+(?:shall|must)\s+[^.!?]+\.$",re.I)
_SPLIT=re.compile(r"(?<=[.!?])\s+|\n+")
_MAP={"validate":"validation","operate":"operation","process":"process"}

def _sha(text:str)->str:
 return sha256(text.encode("utf-8")).hexdigest()

def verify(case:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
 errors=[]
 if not isinstance(case,Mapping) or case.get("schema")!=INPUT_SCHEMA:
  return {"schema":SCHEMA,"verified":False,"errors":["CASE_SCHEMA_INVALID"],"producer_independent":True,"terminal_authority":False}
 if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
  return {"schema":SCHEMA,"verified":False,"errors":["RESULT_SCHEMA_INVALID"],"producer_independent":True,"terminal_authority":False}
 source_id=case.get("source_id"); source=case.get("source_text")
 if case.get("domain")!="FINANCE": errors.append("FINANCE_DOMAIN_MARKER_REQUIRED")
 if not isinstance(source_id,str) or not source_id.strip(): errors.append("SOURCE_ID_INVALID"); source_id=""
 if not isinstance(source,str) or not source.strip(): errors.append("SOURCE_TEXT_INVALID"); source=""
 sentences=[x.strip() for x in _SPLIT.split(source) if x.strip()]
 expected=None
 if len(sentences)!=2: errors.append("EXACTLY_TWO_SENTENCES_REQUIRED")
 else:
  a,b=sentences; am=_A.fullmatch(a); bm=_B.fullmatch(b)
  if am is None: errors.append("BOUNDED_EVENT_ANTECEDENT_REQUIRED")
  if bm is None: errors.append("BOUNDED_DEMONSTRATIVE_EVENT_REFERENCE_REQUIRED")
  if am is not None and bm is not None:
   verb=am.group("v").casefold(); noun=bm.group("n").casefold()
   if _MAP[verb]!=noun: errors.append("EVENT_TYPE_LEXICAL_BRIDGE_MISMATCH")
   fs=source.find(a); ss=source.find(b)
   if fs<0 or ss<0 or source.find(a,fs+1)>=0 or source.find(b,ss+1)>=0:
    errors.append("SENTENCE_LOCATION_NOT_UNIQUE")
   else:
    event_span=[fs+am.start("v"),fs+am.end("o")]
    mention_span=[ss+bm.start("d"),ss+bm.end("n")]
    expected={
     "domain":"FINANCE","source_id":source_id.strip(),"source_text_sha256":_sha(source),
     "event_type":noun,"event_verb":verb,"event_span":event_span,"event_text":source[event_span[0]:event_span[1]],
     "mention_span":mention_span,"mention_text":source[mention_span[0]:mention_span[1]],
     "binding":{"mention_span":mention_span,"target_span":event_span,"event_type":noun},
     "reference_authority":"FINITE_LEXICAL_EVENT_BRIDGE_AND_ADJACENT_TWO_SENTENCE_STRUCTURE",
     "model_dependency_count":0,"general_event_semantics_claimed":False,
     "general_coreference_claimed":False,"synonymy_claimed":False,
     "ontology_mapping_claimed":False,"external_world_truth_claimed":False,
    }
 if expected is not None:
  for k,v in expected.items():
   if result.get(k)!=v: errors.append("MISMATCH:"+k)
 return {
  "schema":SCHEMA,"verified":not errors,
  "status":"PASS__INDEPENDENT_BOUNDED_EVENT_REFERENCE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
  "errors":sorted(set(errors)),"producer_independent":True,"model_dependency_count":0,
  "terminal_authority":False,
  "boundary":"FINITE_VALIDATE_VALIDATION_OPERATE_OPERATION_PROCESS_PROCESS_BRIDGE_ONLY__NO_GENERAL_EVENT_SEMANTICS_WORD_SENSE_ONTOLOGY_OR_EXTERNAL_TRUTH",
 }

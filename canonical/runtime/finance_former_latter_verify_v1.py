"""Independent verifier for explicit ordered-pair former/latter resolution."""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_VERIFY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_FORMER_LATTER_RESULT_V1"
_ENTITY=r"[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2}"
_PAIR=re.compile(rf"^The\s+(?P<a>{_ENTITY})\s+and\s+the\s+(?P<b>{_ENTITY})\s+form\s+the\s+ordered\s+pair\.$",re.I)
_SPLIT=re.compile(r"(?<=[.!?])\s+|\n+")
_REF=re.compile(r"\b(former|latter)\b",re.I)

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
 expected_bindings=[]; expected_pair=None
 if len(sentences)!=2:
  errors.append("EXACTLY_TWO_SENTENCES_REQUIRED")
 else:
  pair_sentence,ref_sentence=sentences
  pm=_PAIR.fullmatch(pair_sentence)
  if pm is None:
   errors.append("EXPLICIT_ORDERED_PAIR_DECLARATION_REQUIRED")
  else:
   a=pm.group("a").strip(); b=pm.group("b").strip()
   if a.casefold()==b.casefold(): errors.append("PAIR_ENTITIES_MUST_DIFFER")
   ps=source.find(pair_sentence); rs=source.find(ref_sentence)
   if ps<0 or rs<0 or source.find(pair_sentence,ps+1)>=0 or source.find(ref_sentence,rs+1)>=0:
    errors.append("SENTENCE_LOCATION_NOT_UNIQUE")
   else:
    sa=[ps+pm.start("a"),ps+pm.end("a")]; sb=[ps+pm.start("b"),ps+pm.end("b")]
    expected_pair={"first_text":a,"first_span":sa,"second_text":b,"second_span":sb}
    refs=list(_REF.finditer(ref_sentence))
    if not refs: errors.append("FORMER_OR_LATTER_REFERENCE_REQUIRED")
    for rm in refs:
     token=rm.group(1).casefold()
     expected_bindings.append({
      "mention":token.upper(),
      "mention_span":[rs+rm.start(1),rs+rm.end(1)],
      "target":"FIRST" if token=="former" else "SECOND",
      "target_span":sa if token=="former" else sb,
      "target_text":a if token=="former" else b,
     })
 expected={
  "domain":"FINANCE","source_id":source_id.strip(),"source_text_sha256":_sha(source),
  "pair":expected_pair,"bindings":expected_bindings,"binding_count":len(expected_bindings),
  "reference_authority":"EXPLICIT_ORDERED_PAIR_SOURCE_SENTENCE_ONLY",
  "model_dependency_count":0,"general_coreference_claimed":False,
  "implicit_pair_inference_claimed":False,"synonymy_claimed":False,
  "ontology_mapping_claimed":False,"external_world_truth_claimed":False,
 }
 for k,v in expected.items():
  if result.get(k)!=v: errors.append("MISMATCH:"+k)
 return {
  "schema":SCHEMA,"verified":not errors,
  "status":"PASS__INDEPENDENT_EXPLICIT_ORDERED_PAIR_FORMER_LATTER_RECOMPUTATION" if not errors else "FAIL_CLOSED",
  "errors":sorted(set(errors)),"producer_independent":True,"model_dependency_count":0,
  "terminal_authority":False,
  "boundary":"EXPLICIT_ORDERED_PAIR_ONLY__FORMER_TO_FIRST_LATTER_TO_SECOND__NO_IMPLICIT_PAIRING_GENERAL_COREFERENCE_SYNONYMY_ONTOLOGY_OR_EXTERNAL_TRUTH",
 }

from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R4_MEASUREMENT_SEMANTIC_CERTIFICATE_V1"
SOURCE_BLOB="4da88dc71e85874b6445988b792951fb3c36d62f"

OPS={
 "FILE_BASENAME":("ARTIFACT_PATH_BASENAME_EXACT_STRING","enum",()),
 "FILE_SUFFIX":("LOWERCASED_FINAL_PATH_SUFFIX_INCLUDING_LEADING_DOT","enum",()),
 "FILE_SIZE_BYTES":("INTEGER_ARTIFACT_FILE_BYTE_LENGTH","integer",()),
 "OOXML_MEMBER_EXISTS":("BOOLEAN_EXACT_ZIP_MEMBER_NAME_MEMBERSHIP","boolean",("member",)),
 "XLSX_SHEET_EXISTS":("BOOLEAN_XLSX_WORKBOOK_SHEET_NAME_MEMBERSHIP","boolean",("sheet_name","case_sensitive")),
 "XLSX_SHEET_COUNT":("INTEGER_COUNT_OF_XLSX_WORKBOOK_SHEET_ELEMENTS","integer",()),
 "DOCX_TEXT_CONTAINS":("BOOLEAN_SUBSTRING_OVER_DOCX_BODY_TEXT_NODES","boolean",("text","case_sensitive")),
 "DOCX_PARAGRAPH_COUNT":("INTEGER_COUNT_OF_DIRECT_DOCX_BODY_PARAGRAPHS","integer",()),
 "DOCX_TABLE_COUNT":("INTEGER_COUNT_OF_DIRECT_DOCX_BODY_TABLES","integer",()),
 "PPTX_SLIDE_COUNT":("INTEGER_COUNT_OF_NUMERIC_PPTX_SLIDE_XML_MEMBERS","integer",()),
 "PPTX_TEXT_CONTAINS":("BOOLEAN_SUBSTRING_OVER_SORTED_PPTX_SLIDE_TEXT_NODES","boolean",("text","case_sensitive")),
}

def _canon(v: Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":reason,
         "bounded_semantic_evidence":False,"global_r4_semantic_leaf_closed":False,
         "task_contract_alignment_authority":False,"quality_authority":False,
         "terminal_authority":False,"terminal_credit_delta":0,**extra}

def certify(req: Mapping[str,Any])->dict[str,Any]:
 if not isinstance(req,Mapping): return _fail("REQUEST_NOT_OBJECT")
 mid=req.get("id"); kind=req.get("kind")
 if not isinstance(mid,str) or not mid: return _fail("MEASUREMENT_ID_INVALID")
 if kind not in OPS: return _fail("MEASUREMENT_KIND_UNSUPPORTED")
 op,out_type,params=OPS[kind]
 allowed={"id","kind",*params}
 extra=sorted(set(req)-allowed)
 if extra: return _fail("UNMODELED_FIELDS",unknown_fields=extra)
 bound={}
 for p in params:
  if p=="case_sensitive":
   value=req.get(p,True)
   if not isinstance(value,bool): return _fail("CASE_SENSITIVE_NOT_BOOLEAN")
   bound[p]=value
  else:
   value=req.get(p)
   if not isinstance(value,str) or not value: return _fail("LITERAL_REQUIRED:"+p)
   bound[p+"_sha256"]=hashlib.sha256(value.encode()).hexdigest()
   bound[p+"_length"]=len(value)
 core={"kind":kind,"operator":op,"output_type":out_type,"parameters":bound,
       "source_measurement_runtime_git_blob_sha":SOURCE_BLOB}
 return {"schema":SCHEMA,"status":"PASS__BOUNDED_R4_MEASUREMENT_SEMANTICS",
         "pass":True,"measurement_id":mid,**core,
         "semantic_signature_sha256":hashlib.sha256(_canon(core)).hexdigest(),
         "bounded_semantic_evidence":True,"global_r4_semantic_leaf_closed":False,
         "task_contract_alignment_authority":False,"quality_authority":False,
         "terminal_authority":False,"terminal_credit_delta":0,
         "rule":"PROVES_MEASUREMENT_OPERATOR_MEANING_ONLY__NOT_TASK_OR_RUBRIC_ALIGNMENT"}

def supported_kinds()->tuple[str,...]:
 return tuple(sorted(OPS))

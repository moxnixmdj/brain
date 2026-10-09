"""Independent verifier for bounded cross-document glossary Finance UNLESS V1."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_VERIFY_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_CASE_V1"
RULE_SCHEMA="PROJECT_BRAIN_FINANCE_RULE_DOCUMENT_V1"
GLOSSARY_SCHEMA="PROJECT_BRAIN_FINANCE_GLOSSARY_DOCUMENT_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_RESULT_V1"

_UNLESS=re.compile(r"\bunless\b",re.I)
_FIELD=r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM=r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_BOOL=re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*\.?\s*$",re.I)
_NUM_EQ=re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*){_NUM}\s*\.?\s*$",re.I)
_MIN=re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+least\s+{_NUM}\s*\.?\s*$",re.I)
_MAX=re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+most\s+{_NUM}\s*\.?\s*$",re.I)
_EXACT=re.compile(rf"^\s*{_FIELD}\s+is\s+exactly\s+{_NUM}\s*\.?\s*$",re.I)
_DECIMAL=re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha_text(v:str)->str:
    return sha256(v.encode("utf-8")).hexdigest()

def _sha_obj(v:Any)->str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()

def _norm(v:Any,label:str)->str:
    if not isinstance(v,str):
        raise ValueError(label+"_INVALID")
    out=" ".join(v.strip().split())
    if not out:
        raise ValueError(label+"_EMPTY")
    return out

def _trim(text:str,start:int,end:int)->tuple[int,int]:
    while start<end and text[start].isspace():
        start+=1
    while end>start and (text[end-1].isspace() or text[end-1] in ".,;:"):
        end-=1
    return start,end

def _scope_id(source_id:str,text:str,match:re.Match[str])->tuple[str,tuple[int,int],tuple[int,int]]:
    left=_trim(text,0,match.start())
    right=_trim(text,match.end(),len(text))
    material=f"{source_id}\0{match.start()}\0{match.end()}\0CONDITIONAL_UNLESS\0{text[match.start():match.end()].lower()}"
    operator_id="OP-"+sha256(material.encode("utf-8")).hexdigest()[:20]
    scope_raw=f"{source_id}\0UNLESS\0{operator_id}\0{(left,right)!r}".encode("utf-8")
    return "SCOPE-"+sha256(scope_raw).hexdigest()[:20],left,right

def _ctx_sha(ctx:Mapping[str,Any])->str:
    return sha256(_canon(ctx).encode("utf-8")).hexdigest()

def _atom(source_id:str,scope_id:str,field:str,operator:str,literal:str,digest:str)->str:
    payload={
        "source_id":source_id,
        "scope_id":scope_id,
        "field_name":field,
        "operator":operator,
        "literal":literal,
        "typed_context_sha256":digest,
    }
    return "CERTIFIED_CONDITION::"+sha256(_canon(payload).encode("utf-8")).hexdigest()

def _decimal(v:Any)->Decimal:
    if not isinstance(v,str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        d=Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not d.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return d

def verify(
    case:Mapping[str,Any],
    rule_document:Mapping[str,Any],
    glossary_document:Mapping[str,Any],
    result:Mapping[str,Any],
)->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        return _fail(["CASE_SCHEMA_INVALID"])
    if not isinstance(rule_document,Mapping) or rule_document.get("schema")!=RULE_SCHEMA:
        return _fail(["RULE_DOCUMENT_SCHEMA_INVALID"])
    if not isinstance(glossary_document,Mapping) or glossary_document.get("schema")!=GLOSSARY_SCHEMA:
        return _fail(["GLOSSARY_DOCUMENT_SCHEMA_INVALID"])
    if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
        return _fail(["RESULT_SCHEMA_INVALID"])

    try:
        source_id=_norm(case.get("source_id"),"SOURCE_ID")
        rule_id=_norm(rule_document.get("document_id"),"RULE_DOCUMENT_ID")
        glossary_id=_norm(glossary_document.get("document_id"),"GLOSSARY_DOCUMENT_ID")
        if rule_id!=_norm(case.get("rule_document_id"),"CASE_RULE_DOCUMENT_ID"):
            errors.append("RULE_DOCUMENT_ID_MISMATCH")
        if glossary_id!=_norm(case.get("glossary_document_id"),"CASE_GLOSSARY_DOCUMENT_ID"):
            errors.append("GLOSSARY_DOCUMENT_ID_MISMATCH")
        if rule_id==glossary_id:
            errors.append("DOCUMENT_ID_COLLISION")

        rule_text=_norm(rule_document.get("rule_text"),"RULE_TEXT")
        entries=glossary_document.get("entries")
        if not isinstance(entries,list) or len(entries)!=1 or not isinstance(entries[0],Mapping):
            raise ValueError("EXACTLY_ONE_GLOSSARY_ENTRY_REQUIRED")
        term=_norm(entries[0].get("term"),"GLOSSARY_TERM")
        definition=_norm(entries[0].get("definition"),"GLOSSARY_DEFINITION")

        ctx=case.get("typed_context")
        expected_digest=case.get("typed_context_sha256")
        if not isinstance(ctx,Mapping):
            raise ValueError("TYPED_CONTEXT_REQUIRED")
        digest=_ctx_sha(ctx)
        if not isinstance(expected_digest,str) or digest!=expected_digest:
            errors.append("TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH")

        ums=list(_UNLESS.finditer(rule_text))
        if len(ums)!=1:
            raise ValueError("EXACT_SINGLE_UNLESS_RULE_REQUIRED")
        rule_source=source_id+"#rule"
        rule_scope,left,right=_scope_id(rule_source,rule_text,ums[0])
        ordinary=rule_text[left[0]:left[1]]
        reference=rule_text[right[0]:right[1]]
        if reference.casefold()!=term.casefold():
            errors.append("GLOSSARY_TERM_REFERENCE_MISMATCH")

        expanded=ordinary+" unless "+definition+"."
        ems=list(_UNLESS.finditer(expanded))
        if len(ems)!=1:
            raise ValueError("EXPANDED_UNLESS_INVALID")
        expanded_source=source_id+"#glossary-expanded"
        expanded_scope,_,eright=_scope_id(expanded_source,expanded,ems[0])
        condition_text=expanded[eright[0]:eright[1]]

        match=_BOOL.fullmatch(condition_text)
        field=operator=literal=required=""
        if match:
            field=match.group("field"); literal=match.group("bool").lower()
            operator="BOOL_EQ"; required="BOOL"
        else:
            for rx,opname in (
                (_MIN,"DECIMAL_GE"),(_MAX,"DECIMAL_LE"),
                (_EXACT,"DECIMAL_EQ"),(_NUM_EQ,"DECIMAL_EQ"),
            ):
                match=rx.fullmatch(condition_text)
                if match:
                    field=match.group("field"); literal=match.group("num")
                    operator=opname; required="DECIMAL_STRING"; break
        if not field:
            raise ValueError("GLOSSARY_DEFINITION_OUTSIDE_TYPED_GRAMMAR")

        fields=ctx.get("fields")
        row=fields.get(field) if isinstance(fields,Mapping) else None
        if not isinstance(row,Mapping):
            raise ValueError("GLOSSARY_FIELD_NOT_PRESENT")
        if row.get("type")!=required:
            raise ValueError("GLOSSARY_FIELD_TYPE_MISMATCH")
        value=row.get("value")
        if operator=="BOOL_EQ":
            if not isinstance(value,bool):
                raise ValueError("BOOL_VALUE_INVALID")
            holds=value is (literal=="true")
        else:
            av,lv=_decimal(value),_decimal(literal)
            if operator=="DECIMAL_GE": holds=av>=lv
            elif operator=="DECIMAL_LE": holds=av<=lv
            else: holds=av==lv

        atom=_atom(expanded_source,expanded_scope,field,operator,literal,digest)
        constraint={"op":"ATOM","id":atom} if holds else {
            "op":"NOT","arg":{"op":"ATOM","id":atom}
        }
        selected=right if holds else left
        selected_text=rule_text[selected[0]:selected[1]]
        expected={
            "source_id":source_id,
            "rule_document_id":rule_id,
            "glossary_document_id":glossary_id,
            "rule_document_semantic_sha256":_sha_obj(rule_document),
            "glossary_document_semantic_sha256":_sha_obj(glossary_document),
            "typed_context_sha256":digest,
            "rule_text_sha256":_sha_text(rule_text),
            "glossary_term":term,
            "glossary_term_sha256":_sha_text(term),
            "glossary_definition_sha256":_sha_text(definition),
            "expanded_rule_sha256":_sha_text(expanded),
            "rule_scope_id":rule_scope,
            "condition_holds":holds,
            "condition_atom_id":atom,
            "proved_constraint":constraint,
            "field_name":field,
            "field_type":required,
            "operator":operator,
            "literal":literal,
            "selected_branch":"EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
            "selected_span":list(selected),
            "selected_text":selected_text,
            "selected_text_sha256":_sha_text(selected_text),
        }
        for key,value in expected.items():
            if result.get(key)!=value:
                errors.append("MISMATCH:"+key)
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))

    if result.get("model_dependency_count")!=0:
        errors.append("MODEL_DEPENDENCY_NONZERO")
    if result.get("external_world_truth_claimed") is not False:
        errors.append("EXTERNAL_WORLD_TRUTH_BOUNDARY_VIOLATION")
    if result.get("inferred_synonymy_claimed") is not False:
        errors.append("INFERRED_SYNONYMY_BOUNDARY_VIOLATION")
    if result.get("general_ontology_mapping_claimed") is not False:
        errors.append("GENERAL_ONTOLOGY_BOUNDARY_VIOLATION")
    if result.get("general_cross_document_semantics_claimed") is not False:
        errors.append("GENERAL_CROSS_DOCUMENT_BOUNDARY_VIOLATION")
    if result.get("reference_resolution_authority")!=(
        "EXACT_CONTENT_ADDRESSED_CROSS_DOCUMENT_GLOSSARY_TERM_TO_TYPED_CONDITION_ONLY"
    ):
        errors.append("REFERENCE_AUTHORITY_BOUNDARY_MISMATCH")

    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_CROSS_DOCUMENT_GLOSSARY_TYPED_UNLESS_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "model_dependency_count":0,
        "terminal_authority":False,
        "boundary":"EXACT_SEPARATE_RULE_AND_GLOSSARY_DOCUMENTS__ONE_EXPLICIT_GLOSSARY_TERM_TO_LITERAL_TYPED_BOOLEAN_OR_DECIMAL_CONDITION__NO_INFERRED_SYNONYMY_ONTOLOGY_EXTERNAL_WORLD_TRUTH_OR_GENERAL_CROSS_DOCUMENT_SEMANTICS",
    }

def _fail(errors:list[str])->dict[str,Any]:
    return {
        "schema":SCHEMA,"verified":False,"status":"FAIL_CLOSED",
        "errors":errors,"producer_independent":True,
        "model_dependency_count":0,"terminal_authority":False,
    }

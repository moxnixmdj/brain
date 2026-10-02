"""Executable annotation-to-feature-constraint pipeline for M1A.

Input contract:
- normalized/registered drawing image,
- OCR text observations with bounding boxes (from the pinned OCR route or another
  independently verified extractor),
- optional JIT formal notation grammar/catalog knowledge,
- optional JIT visual symbol templates + semantics.

The pipeline owns parsing, ambiguity-safe geometry association, and conjunctive
feature composition. It never treats OCR text or a symbol match as terminal truth.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import numpy as np

from canonical.runtime.raw_drawing_primitives import extract_primitives
from canonical.runtime.engineering_feature_notation import parse_feature_notation
from canonical.runtime.engineering_callout_parser import parse_callout
from canonical.runtime.declarative_notation_grammar import parse_with_grammar
from canonical.runtime.declarative_engineering_notation import compile_catalog, resolve_tokens
from canonical.runtime.visual_symbol_template_matcher import match_symbol
from canonical.runtime.callout_geometry_association import associate_callout
from canonical.runtime.feature_constraint_composer import compose_feature_constraints

SCHEMA="BRAIN_DRAWING_ANNOTATION_CONSTRAINT_PIPELINE_V1"


def _target_for_box(
    box:Mapping[str,Any],
    primitives:Mapping[str,Any],
    explicit_target:Any,
)->tuple[str|None,dict[str,Any]|None]:
    if isinstance(explicit_target,str) and explicit_target:
        return explicit_target,{"route":"EXPLICIT_TARGET"}
    assoc=associate_callout(dict(box),dict(primitives))
    if assoc.get("status")!="ASSOCIATED":
        return None,assoc
    return f"{assoc['primitive_kind']}:{assoc['primitive_index']}",assoc


def _parse_text(
    text:str,
    *,
    jit_rules:Sequence[Mapping[str,Any]]|None,
    compiled_catalog:Mapping[str,Any]|None,
)->tuple[dict[str,Any]|None,dict[str,Any]]:
    fast=parse_feature_notation(text)
    if fast.get("status")=="PARSED":
        return fast,{"route":"ENGINEERING_FEATURE_FAST_PATH"}

    scalar=parse_callout(text)
    if scalar.get("status")=="PARSED":
        return scalar,{"route":"SCALAR_CALLOUT_FAST_PATH"}

    if jit_rules:
        generic=parse_with_grammar(text,jit_rules)
        if generic.get("status")=="PARSED":
            ann={
                "status":"PARSED",
                "kind":"declarative_claim",
                "property":generic["kind"],
                "value":generic["captures"],
            }
            return ann,{"route":"JIT_STRUCTURAL_GRAMMAR","rule_id":generic["rule_id"]}

    if compiled_catalog is not None:
        resolved=resolve_tokens(text,compiled_catalog)
        toks=resolved.get("tokens",[]) if resolved.get("status")=="RESOLVED" else []
        usable=[]
        for tok in toks:
            sem=tok.get("semantics")
            if isinstance(sem,Mapping) and isinstance(sem.get("property"),str):
                usable.append(sem)
        if len(usable)==1:
            ann={
                "status":"PARSED",
                "kind":"declarative_claim",
                "property":usable[0]["property"],
                "value":usable[0].get("value"),
            }
            return ann,{"route":"JIT_ALIAS_CATALOG","symbol_count":1}
        if len(usable)>1:
            return None,{"route":"JIT_ALIAS_CATALOG","error":"MULTIPLE_SEMANTIC_TOKENS_REQUIRE_STRUCTURAL_GRAMMAR"}

    return None,{
        "route":"NONE",
        "error":"UNSUPPORTED_OR_AMBIGUOUS_TEXT_NOTATION",
        "fast_error":fast.get("error"),
        "scalar_error":scalar.get("error"),
    }


def compile_annotation_constraints(
    image:np.ndarray[Any,Any],
    *,
    text_items:Sequence[Mapping[str,Any]]=(),
    symbol_items:Sequence[Mapping[str,Any]]=(),
    jit_rules:Sequence[Mapping[str,Any]]|None=None,
    jit_catalog_rows:Sequence[Mapping[str,Any]]|None=None,
    symbol_templates:Mapping[str,np.ndarray]|None=None,
    symbol_semantics:Mapping[str,Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    primitives=extract_primitives(image)
    rows=[]
    parse_receipts=[]
    errors=[]

    compiled_catalog=None
    if jit_catalog_rows is not None:
        compiled_catalog=compile_catalog(jit_catalog_rows)
        if compiled_catalog.get("status")!="COMPILED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"JIT_CATALOG_INVALID","detail":compiled_catalog}

    for i,item in enumerate(text_items):
        if not isinstance(item,Mapping):
            errors.append(f"TEXT_ITEM_NOT_OBJECT:{i}"); continue
        text=item.get("text")
        box=item.get("box")
        if not isinstance(text,str) or not text.strip():
            errors.append(f"TEXT_EMPTY:{i}"); continue
        if not isinstance(box,Mapping):
            errors.append(f"TEXT_BOX_INVALID:{i}"); continue
        ann,receipt=_parse_text(text,jit_rules=jit_rules,compiled_catalog=compiled_catalog)
        parse_receipts.append({"item":f"text:{i}","text":text,"receipt":receipt})
        if ann is None:
            errors.append(f"TEXT_PARSE_FAILED:{i}:{receipt.get('error')}"); continue
        target,assoc=_target_for_box(box,primitives,item.get("target_id"))
        if target is None:
            errors.append(f"TEXT_ASSOCIATION_FAILED:{i}:{assoc.get('error')}"); continue
        rows.append({
            "target_id":target,
            "source_id":str(item.get("source_id",f"text:{i}")),
            "annotation":ann,
        })

    if symbol_items:
        if not symbol_templates or not symbol_semantics:
            errors.append("SYMBOL_ROUTE_CONFIGURATION_MISSING")
        else:
            for i,item in enumerate(symbol_items):
                if not isinstance(item,Mapping):
                    errors.append(f"SYMBOL_ITEM_NOT_OBJECT:{i}"); continue
                crop=item.get("image"); box=item.get("box")
                if not isinstance(crop,np.ndarray) or crop.ndim!=2:
                    errors.append(f"SYMBOL_IMAGE_INVALID:{i}"); continue
                if not isinstance(box,Mapping):
                    errors.append(f"SYMBOL_BOX_INVALID:{i}"); continue
                match=match_symbol(crop,symbol_templates)
                parse_receipts.append({"item":f"symbol:{i}","receipt":match})
                if match.get("status")!="MATCHED":
                    errors.append(f"SYMBOL_MATCH_FAILED:{i}:{match.get('error')}"); continue
                sem=symbol_semantics.get(match["symbol_id"])
                if not isinstance(sem,Mapping) or not isinstance(sem.get("property"),str):
                    errors.append(f"SYMBOL_SEMANTICS_MISSING:{i}:{match['symbol_id']}"); continue
                ann={
                    "status":"PARSED","kind":"declarative_claim",
                    "property":sem["property"],"value":sem.get("value"),
                }
                target,assoc=_target_for_box(box,primitives,item.get("target_id"))
                if target is None:
                    errors.append(f"SYMBOL_ASSOCIATION_FAILED:{i}:{assoc.get('error')}"); continue
                rows.append({
                    "target_id":target,
                    "source_id":str(item.get("source_id",f"symbol:{i}")),
                    "annotation":ann,
                })

    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "parse_receipts":parse_receipts,
            "primitives":primitives,
            "terminal_authority":False,
        }

    composed=compose_feature_constraints(rows)
    if composed.get("status")!="COMPOSED":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","error":"FEATURE_COMPOSITION_FAILED",
            "detail":composed,"parse_receipts":parse_receipts,"primitives":primitives,
            "terminal_authority":False,
        }
    return {
        "schema":SCHEMA,"status":"COMPILED",
        "primitives":primitives,
        "features":composed["features"],
        "provenance":composed["provenance"],
        "parse_receipts":parse_receipts,
        "terminal_authority":False,
        "scope":"VERIFIED_PARSE_ASSOCIATE_COMPOSE_PATHS_WITH_JIT_NOTATION_KNOWLEDGE_AND_FAIL_CLOSED_AMBIGUITY",
    }
